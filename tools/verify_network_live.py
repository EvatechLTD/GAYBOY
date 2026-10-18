"""Read-only HTTPS deployment verification. Never creates production accounts."""
import hashlib
import json
from pathlib import Path
import urllib.request
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='https://y2kcrisis.com/'
for name in ['index.html','app.js','core.js','editor.js','homepage.js','social.js','studio.js','media.js','emoji.js','themes.js','style.css','community.css','homepage.css','gayboy.json','emoji/uwu.png','fonts/PressStart2P-Regular.ttf','fonts/PermanentMarker-Regular.ttf']:
    with urllib.request.urlopen(BASE+name,timeout=20) as response:
        assert hashlib.sha256(response.read()).digest()==hashlib.sha256((ROOT/'network'/name).read_bytes()).digest(),name
        assert 'frame-ancestors' in response.headers.get('Content-Security-Policy','')
    print('HTTPS hash verified:',name)
with urllib.request.urlopen(BASE+'api.php',timeout=20) as response:
    session=json.load(response)
    assert session['user'] is None and session['csrf']
    assert 'HttpOnly' in response.headers['Set-Cookie'] and 'secure' in response.headers['Set-Cookie'].lower()
    print('HTTPS API verified: private session, Secure/HttpOnly cookie')
with urllib.request.urlopen(BASE+'api.php?action=members',timeout=20) as response:
    assert isinstance(json.load(response),list)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome')
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE,wait_until='networkidle')
    assert 'your computer' in page.locator('.hero h1').inner_text()
    assert 'SERVER SETUP NEEDED' not in page.locator('#view').inner_text()
    for width in [1440,390,320]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(ROOT/f'build/network-qa/live-{width}.png'),full_page=True)
    assert not errors,errors
    page.goto(BASE+'~GAYBOY',wait_until='domcontentloaded')
    page.wait_for_selector('.homepage')
    assert page.locator('.hp-header h1').inner_text()=='GAYBOY'
    assert page.locator('.hp-gallery img').count()==4
    assert page.locator('.hp-download').count()==1
    page.set_viewport_size({'width':1440,'height':1100})
    page.locator('.hp-app').scroll_into_view_if_needed()
    frame=page.frame_locator('.hp-app')
    frame.locator('#demo-play').wait_for()
    frame.locator('#demo-play').click()
    frame.locator('.demo-status').filter(has_text='Playing!').wait_for(timeout=20000)
    assert not errors,errors
    page.screenshot(path=str(ROOT/'build/network-qa/live-gayboy.png'),full_page=True)
    browser.close()
print('PASS: live TLS, module/asset hashes, security headers, API, desktop/mobile rendering, clean GAYBOY permalink, gallery/download blocks, embedded real app boot, no JavaScript errors')
