"""Browser QA for the actual WASM ROM, keyboard, touch, pause and downloads.

Run with the sibling VIBECHOPPER virtualenv (Playwright + Chrome available).
Pass the served website URL, optionally https://buttholechopper.com/gayboy/.
"""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright, expect

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:18974/'
OUT = Path(__file__).resolve().parents[1] / 'build'
INSTRUMENT = r"""
const originalSameBoy = window.SameBoyCore;
window.SameBoyCore = async (...args) => {
  const module = await originalSameBoy(...args);
  window.qaInputs = [];
  for (const button of ['up','down','left','right','A','B','start','select']) {
    const original = module['_set_joyp_' + button];
    module['_set_joyp_' + button] = (instance, down) => {
      window.qaInputs.push({button, down:!!down});
      return original(instance, down);
    };
  }
  return module;
};
"""


def start(page, mobile=False):
    page.add_init_script("""(() => {
      const original = AudioContext.prototype.createBufferSource;
      window.qaAudioPeak = 0;
      AudioContext.prototype.createBufferSource = function(...args) {
        const source = original.apply(this,args), start = source.start;
        source.start = function(...args) {
          if (source.buffer) {
            const data = source.buffer.getChannelData(0);
            window.qaAudioPeak = Math.max(qaAudioPeak, Math.max(...data)-Math.min(...data));
          }
          return start.apply(this,args);
        }; return source;
      };
    })();""")
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    requests = []
    page.on('request', lambda request: requests.append(request.url))
    page.route('**/emulator/sameboy.js*', lambda route: route.fulfill(
        response=(response := route.fetch()), body=response.text() + INSTRUMENT))
    page.goto(URL, wait_until='networkidle')
    assert not any(url.endswith('sameboy.wasm') for url in requests), 'Core loaded before Play'
    page.locator('#demo-play').tap() if mobile else page.locator('#demo-play').click()
    expect(page.locator('#live-demo')).to_have_class(
        'panel demo-panel demo-started demo-expanded' if mobile else 'panel demo-panel demo-started',
        timeout=20000)
    page.wait_for_timeout(3200)
    colors = page.locator('#live-demo canvas').evaluate(
        "c=>new Set(c.getContext('2d').getImageData(0,0,160,144).data).size")
    assert colors > 2, 'ROM did not render a visible screen'
    assert page.evaluate('qaAudioPeak > 0.01'), 'ROM audio stayed silent'
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'Horizontal overflow'
    return errors


with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    desktop = browser.new_context(viewport={'width':1440, 'height':1000})
    page = desktop.new_page()
    errors = start(page)
    for key, button in [('z','B'),('x','A'),('Shift','start'),('Space','select'),
                        ('ArrowUp','up'),('ArrowDown','down'),('ArrowLeft','left'),('ArrowRight','right')]:
        page.locator('#live-demo canvas').focus()
        page.keyboard.down(key)
        expect(page.locator(f'[data-pad="{button}"]')).to_have_class('held')
        page.wait_for_timeout(80)
        page.keyboard.up(key)
        expect(page.locator(f'[data-pad="{button}"]')).not_to_have_class('held')
        assert page.evaluate('(button)=>qaInputs.some(e=>e.button===button && e.down)', button)
    page.wait_for_timeout(1500)
    page.locator('#demo-pause').click()
    expect(page.locator('#demo-pause')).to_have_attribute('aria-pressed','true')
    before = page.locator('#live-demo canvas').evaluate("c=>c.toDataURL()")
    page.wait_for_timeout(200)
    assert page.locator('#live-demo canvas').evaluate("c=>c.toDataURL()") == before
    page.locator('#live-demo').screenshot(path=str(OUT / 'demo-desktop.png'))
    with page.expect_download() as download:
        page.locator('#demo-save').click()
    assert Path(download.value.path()).stat().st_size == 32768
    page.locator('#demo-pause').click()
    page.locator('#demo-mute').click()
    expect(page.locator('#demo-mute')).to_have_attribute('aria-pressed','true')
    page.locator('#demo-restart').click()
    page.wait_for_timeout(1500)
    assert not errors, errors
    desktop.close()

    mobile = browser.new_context(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True,
        device_scale_factor=1)
    page = mobile.new_page()
    errors = start(page, True)
    cdp = mobile.new_cdp_session(page)
    b = page.locator('[data-pad="B"]').bounding_box()
    left = page.locator('[data-pad="left"]').bounding_box()
    points = [{'x':box['x']+box['width']/2,'y':box['y']+box['height']/2,'id':i+1}
              for i,box in enumerate([b,left])]
    cdp.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':points})
    expect(page.locator('[data-pad="B"]')).to_have_class('held')
    expect(page.locator('[data-pad="left"]')).to_have_class('held')
    cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
    expect(page.locator('[data-pad="B"]')).not_to_have_class('held')
    expect(page.locator('[data-pad="left"]')).not_to_have_class('held')
    page.locator('[data-pad="start"]').tap()
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / 'demo-mobile.png'), full_page=False)
    for width,height in [(320,740),(768,1024),(844,390)]:
        page.set_viewport_size({'width':width,'height':height})
        assert not page.locator('#live-demo').evaluate('e=>e.scrollWidth>e.clientWidth'), f'Demo overflow: {width}'
    page.locator('#demo-fullscreen').tap()
    expect(page.locator('#live-demo')).not_to_have_class('demo-expanded')
    assert not errors, errors
    mobile.close()
    browser.close()
    print(json.dumps({'url':URL,'ROM_rendering':'passed','keyboard':'all 8 controls passed',
        'pause_restart_mute':'passed','save_download':'32 KiB',
        'mobile_multitouch':'B + left held together and released',
        'responsive':'320px, 390px, tablet and landscape passed','browser_errors':[]}))
