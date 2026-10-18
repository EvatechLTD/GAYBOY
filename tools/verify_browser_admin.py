"""Exercise admin setup, authentication, notifications and moderation locally."""
from pathlib import Path
import hashlib
import json
import re
import secrets
import sqlite3
import time
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1];PRIVATE=ROOT/'build/comments-private'
BASE='http://127.0.0.1:18978/'
auth=PRIVATE/'admin-auth.json';previous=auth.read_bytes() if auth.exists() else None
token=secrets.token_hex(32);password='Local-only-test-password-785!'
auth.write_text(json.dumps({'setup_hash':hashlib.sha256(token.encode()).hexdigest(),'setup_expires':int(time.time())+3600}))
identifiers=[];beat_identifier=None
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(viewport={'width':390,'height':844});page=context.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        request=context.request;origin={'Origin':BASE.rstrip('/')}
        api=BASE+'admin/api.php?action='
        assert request.get(api+'status').json()=={'authenticated':False}
        assert request.get(api+'list').status==401
        assert request.post(api+'delete-comment',headers=origin,multipart={'id':'1'}).status==401
        page.goto(BASE+'admin/#setup='+token,wait_until='networkidle')
        expect(page.locator('#login-title')).to_have_text('Set your admin password')
        assert token not in page.url,'Setup key remained in URL'
        page.locator('#password').fill(password);page.get_by_role('button',name='set password',exact=True).click()
        expect(page.locator('#moderation')).to_be_visible()
        credentials=json.loads(auth.read_text());assert 'setup_hash' not in credentials and 'password_hash' in credentials
        session=request.get(api+'session').json();csrf=session['csrf'];baseline=session['new_comments']
        request.get(BASE+'beats/api.php?action=list')
        beat_identifier=secrets.token_hex(12)
        with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
            db.execute('INSERT INTO beats VALUES(?,?,?,?,?,?,?,?)',(beat_identifier,'Local QA','Admin deletion check',int(time.time()),b'local fixture','fixture','unused','local'))
        page.locator('#refresh').click()
        beat_row=page.locator(f'.admin-item[data-id="{beat_identifier}"]')
        expect(beat_row).to_be_visible()
        accept=lambda d:d.accept();page.on('dialog',accept)
        beat_row.get_by_role('button',name='delete beat').click()
        expect(beat_row).to_have_count(0);page.remove_listener('dialog',accept)
        assert request.get(BASE+'beats/api.php?action=beat&id='+beat_identifier).status==404
        assert request.post(api+'approve',headers=origin,multipart={'id':'1','csrf':'bad'}).status==403
        assert request.post(api+'approve',headers={'Origin':'https://evil.invalid'},multipart={'id':'1','csrf':csrf}).status==403
        # Submit a real comment through the public human check.
        challenge=request.get(BASE+'comments/api.php?action=challenge').json()
        sid=next(c['value'] for c in context.cookies() if c['name']=='GAYBOYWALL')
        session_text=(PRIVATE/'sessions'/('sess_'+sid)).read_text()
        code=re.search(re.escape(challenge['nonce'])+r'";a:\d+:\{s:4:"code";s:6:"(\d{6})";',session_text).group(1)
        time.sleep(2.1)
        result=request.post(BASE+'comments/api.php?action=post',headers=origin,multipart={**challenge,'name':'Admin local QA','body':'<script>window.adminXSS=true</script>','human_code':code,'website':'','avatar':{'name':'profile.png','mimeType':'image/png','buffer':(ROOT/'website/images/mixer.png').read_bytes()}})
        assert result.status==201,result.text();identifier=result.json()['id'];identifiers.append(identifier)
        assert not any(c['id']==identifier for c in request.get(BASE+'comments/api.php?action=list').json()['comments'])
        assert request.get(BASE+f'comments/api.php?action=avatar&id={identifier}').status==404
        private_avatar=request.get(api+f'avatar&id={identifier}')
        assert private_avatar.status==200 and private_avatar.body().startswith(b'\x89PNG')
        page.goto(BASE,wait_until='networkidle')
        expect(page.locator('.admin-login')).to_have_count(0)
        assert request.get(api+'status').json()['new_comments']==baseline+1
        page.goto(BASE+'admin/',wait_until='networkidle')
        expect(page.locator('#moderation')).to_be_visible()
        row=page.locator(f'.admin-item[data-id="{identifier}"]')
        expect(row).to_contain_text('<script>window.adminXSS=true</script>')
        assert page.evaluate('window.adminXSS') is None
        row.get_by_role('button',name='approve comment').click()
        expect(row).not_to_have_class(re.compile('unreviewed'))
        assert request.get(api+'status').json()['new_comments']==baseline
        assert any(c['id']==identifier for c in request.get(BASE+'comments/api.php?action=list').json()['comments'])
        assert request.get(BASE+f'comments/api.php?action=avatar&id={identifier}').status==200
        page.on('dialog',lambda d:d.accept())
        row.get_by_role('button',name='delete comment').click();expect(row).to_have_count(0)
        assert not any(c['id']==identifier for c in request.get(BASE+'comments/api.php?action=list').json()['comments'])
        page.goto(BASE,wait_until='networkidle')
        expect(page.locator('.admin-login')).to_have_count(0)
        assert request.get(api+'status').json()['new_comments']==baseline
        page.goto(BASE+'admin/',wait_until='networkidle');page.locator('#logout').click()
        expect(page.locator('#login')).to_be_visible()
        assert request.get(api+'list').status==401
        # Login failures and consumed setup links do not grant a new session.
        session=request.get(api+'session').json()
        assert request.post(api+'login',headers=origin,multipart={'csrf':session['csrf'],'password':'wrong'}).status==403
        assert request.post(api+'setup',headers=origin,multipart={'csrf':session['csrf'],'setup_token':token,'password':password}).status==403
        page.locator('#password').fill(password);page.get_by_role('button',name='log in',exact=True).click()
        expect(page.locator('#moderation')).to_be_visible()
        assert not errors,errors
        print(json.dumps({'setup':'one-use fragment key; password hashed privately','login':'password and logout verified','security':'unauthenticated, invalid CSRF and foreign origin rejected','badge':'pending comment changes count and style; approval clears it','moderation':'comment and thumbnail hidden before approval; approval publishes; deletion removes','browser_errors':errors}))
        browser.close()
finally:
    with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
        for identifier in identifiers:db.execute('DELETE FROM comments WHERE id=?',(identifier,))
        if beat_identifier:db.execute('DELETE FROM beats WHERE id=?',(beat_identifier,))
        db.execute('DELETE FROM limits')
    if previous is None:auth.unlink(missing_ok=True)
    else:auth.write_bytes(previous)
