from pathlib import Path
from playwright.sync_api import sync_playwright
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
root=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',18989),partial(SimpleHTTPRequestHandler,directory=str(root/'website')))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
    browser=p.chromium.launch(channel="chrome")
    page=browser.new_page(accept_downloads=True)
    page.goto('http://127.0.0.1:18989/')
    page.wait_for_selector('.gayboy-support-note')
    page.locator('.download-button').click()
    assert page.locator('.gayboy-tip-dialog').is_visible()
    with page.expect_download() as event:
        page.locator('[data-tip=free]').click()
    assert event.value.suggested_filename=='GAYBOY.gb'
    assert not page.locator('.gayboy-tip-dialog').is_visible()
    for choice in ('five','custom'):
        page.locator('.download-button').click()
        page.evaluate('window.open = url => {window.checkoutURL=url; return {opener:null}}')
        with page.expect_download():
            page.locator('[data-tip='+choice+']').click()
        assert page.evaluate('window.checkoutURL').startswith('https://buy.stripe.com/')
        page.locator('.tip-close').click()
    page.set_viewport_size({'width':320,'height':640})
    page.locator('.download-button').click()
    bounds=page.locator('.gayboy-tip-dialog').bounding_box()
    assert bounds['x']>=0 and bounds['x']+bounds['width']<=320
    page.keyboard.press('Escape')
    assert not page.locator('.gayboy-tip-dialog').is_visible()
    page.route('**/gayboy-tips.json',lambda route:route.abort())
    page.reload()
    page.locator('.download-button').click()
    page.locator('[data-tip=five]').click()
    assert 'unavailable' in page.locator('.tip-status').inner_text()
    with page.expect_download():page.locator('[data-tip=free]').click()
    print('PASS: free download, both Stripe destinations, 320px layout, Escape, and payment failure fallback')
    browser.close()
server.shutdown()

