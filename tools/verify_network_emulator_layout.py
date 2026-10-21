"""Read-only layout and real ROM check, local by default or --live."""
import sys
from playwright.sync_api import sync_playwright

BASE='https://y2kcrisis.com/' if '--live' in sys.argv else 'http://127.0.0.1:18981/'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome')
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'gayboy');frame=page.frame_locator('.hp-app')
    frame.locator('#demo-play').click();frame.locator('.demo-status').filter(has_text='Playing!').wait_for(timeout=30000)
    for width in [1440,1280,1024,390,320]:
        page.set_viewport_size({'width':width,'height':900});page.wait_for_timeout(400)
        d=frame.locator('body').evaluate('e=>({height:e.scrollHeight,viewport:innerHeight,width:e.scrollWidth,viewWidth:innerWidth})')
        assert d['height']<=d['viewport']+2,d
        assert d['width']<=d['viewWidth']+2,d
    page.set_viewport_size({'width':1440,'height':1000})
    frame.locator('#demo-fullscreen').click();page.wait_for_timeout(300)
    rect=page.locator('.hp-app').bounding_box()
    assert rect['x']==0 and rect['y']==0 and rect['width']==1440 and rect['height']==1000,rect
    frame.locator('#demo-fullscreen').click();page.wait_for_timeout(300)
    assert frame.locator('body').evaluate('e=>e.scrollHeight<=innerHeight+2')
    assert not errors,errors
    print('PASS: ROM boots; complete app height at desktop and phone widths; big-screen fills browser and returns without inner scrollbars:',BASE)
    browser.close()
