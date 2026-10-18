"""Read-only production check. Never configures credentials or posts content."""
import json
import sys
from playwright.sync_api import sync_playwright, expect
BASE=sys.argv[1] if len(sys.argv)>1 else 'https://buttholechopper.com/gayboy/'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE,wait_until='networkidle')
    expect(page.locator('.admin-login')).to_have_count(0)
    expect(page.locator('a[href="admin/"]')).to_have_count(0)
    expect(page.locator('.handheld-brand #demo-share')).to_have_text('share beat')
    expect(page.locator('#beats')).to_be_visible()
    listing=context.request.get(BASE+'beats/api.php?action=list')
    assert listing.status==200 and isinstance(listing.json()['beats'],list)
    assert context.request.get(BASE+'admin/api.php?action=list').status==401
    page.goto(BASE+'admin/',wait_until='networkidle')
    expect(page.locator('#login')).to_be_visible()
    expect(page.locator('#moderation')).to_be_hidden()
    assert page.locator('#password').get_attribute('type')=='password'
    session=context.request.get(BASE+'admin/api.php?action=session').json()
    assert not session['authenticated'] and 'password_hash' not in session and 'setup_token' not in session
    cookie=next(c for c in context.cookies() if c['name']=='GAYBOYADMIN')
    assert cookie['secure'] and cookie['httpOnly'] and cookie['sameSite']=='Strict'
    assert not errors,errors
    print(json.dumps({'beat_wall':'live; listing verified','admin':'login page and access control verified','admin_cookie':'Secure, HttpOnly, SameSite Strict','public_writes':0,'credentials_changed':False,'browser_errors':errors}))
    browser.close()
