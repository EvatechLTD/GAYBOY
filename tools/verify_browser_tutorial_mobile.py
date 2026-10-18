"""Check the phone lesson layout and device-specific instructions in Chrome."""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:18980/'
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width':390,'height':844}, has_touch=True)
    page.goto(URL, wait_until='networkidle')
    page.locator('#demo-tutorial').tap()
    panel = page.locator('.demo-tutorial')
    expect(panel).to_have_attribute('data-stage','practice',timeout=45000)
    expect(page.locator('.tutorial-description')).not_to_contain_text('Keyboard:')
    sizes = []
    for width, height in [(390,844),(375,667),(360,640)]:
        page.set_viewport_size({'width':width,'height':height})
        page.wait_for_timeout(300)
        bounds = page.evaluate('''()=>{
          const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom}};
          return {screen:rect('.demo-screen canvas'),lesson:rect('.demo-tutorial'),toolbar:rect('.demo-toolbar'),scroll:document.querySelector('#live-demo').scrollWidth};
        }''')
        assert bounds['screen']['height'] >= 200, bounds
        assert bounds['toolbar']['bottom'] <= height, bounds
        assert bounds['scroll'] <= width, bounds
        page.screenshot(path=str(ROOT/f'build/tutorial-mobile-{width}.png'))
        sizes.append({'viewport':[width,height],**bounds})
    panel.focus()
    page.keyboard.down('Space');page.wait_for_timeout(300)
    page.keyboard.down('x');page.wait_for_timeout(300)
    page.keyboard.up('x');page.keyboard.up('Space')
    expect(panel).to_have_attribute('data-stage','passed',timeout=8000)
    expect(page.locator('.tutorial-feedback')).to_contain_text('Lesson complete!')
    expect(panel).to_have_attribute('data-lesson','2',timeout=10000)
    expect(panel).to_have_attribute('data-stage','practice',timeout=30000)
    expect(page.locator('.tutorial-description')).to_contain_text('B to place')
    expect(page.locator('.tutorial-description')).not_to_contain_text('(Z)')
    page.context.new_cdp_session(page).send('Emulation.setTouchEmulationEnabled', {'enabled':False})
    page.set_viewport_size({'width':1200,'height':900})
    expect(page.locator('.tutorial-description')).to_contain_text('B (Z)')
    print(json.dumps({'mobile_layouts':sizes,'instructions':'phone buttons only; desktop shortcuts retained','cold_start':'one tap'}))
    browser.close()
