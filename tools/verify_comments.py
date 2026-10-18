"""Exercise the real PHP wall against isolated local storage, never public posts."""
from pathlib import Path
from io import BytesIO
import json
import re
import sqlite3
import time
import sys
import site
sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
sys.path.append(site.getusersitepackages())
from PIL import Image, PngImagePlugin
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'build/comments-private'
BASE='http://127.0.0.1:18978/'
API=BASE+'comments/api.php'
origin={'Origin':BASE.rstrip('/')}
def code_for(request,nonce):
    sid=next(cookie['value'] for cookie in request.storage_state()['cookies'] if cookie['name']=='GAYBOYWALL')
    text=(PRIVATE/'sessions'/('sess_'+sid)).read_text()
    result=re.search(re.escape(nonce)+r'";a:\d+:\{s:4:"code";s:6:"(\d{6})";',text)
    assert result,'Own test challenge missing from private session'
    return result.group(1)
def challenge(request,wait=True):
    response=request.get(API+'?action=challenge');assert response.status==200,response.text()
    data=response.json();data['human_code']=code_for(request,data['nonce'])
    if wait:time.sleep(2.05)
    return data
def post(request,data,**fields):
    payload={'name':'Local QA visitor','body':'Local verification only','website':'',**data,**fields}
    return request.post(API+'?action=post',headers=origin,multipart=payload)
def clear_limits():
    with sqlite3.connect(PRIVATE/'comments.sqlite') as db:db.execute('DELETE FROM limits')

with sync_playwright() as p:
    with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
        db.execute("DELETE FROM comments WHERE name IN ('Profile QA','Local QA visitor','Tiny pixel visitor')")
        db.execute('DELETE FROM limits')
    request=p.request.new_context()
    assert request.get(API+'?action=list').json()['total']==0,'Local test DB must start empty'
    assert request.post(API+'?action=post',multipart={'name':'bot','body':'no token'}).status==403
    data=challenge(request,False)
    assert post(request,data).status==422,'Instant form submission was accepted'
    data=challenge(request)
    wrong={**data,'human_code':'999999' if data['human_code']!='999999' else '111111'}
    assert post(request,wrong).status==422
    assert post(request,data).status==400,'CAPTCHA replay was accepted'
    data=challenge(request)
    assert post(request,data,website='https://spam.invalid/').status==422
    data=challenge(request)
    assert post(request,data,avatar={'name':'picture.png','mimeType':'image/png',
        'buffer':b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'}).status==422
    data=challenge(request)
    huge=BytesIO();Image.new('RGB',(2049,2)).save(huge,format='PNG')
    assert post(request,data,avatar={'name':'large.png','mimeType':'image/png','buffer':huge.getvalue()}).status==422
    # Real PNG with metadata: the server must output only a fresh square PNG.
    image=BytesIO();info=PngImagePlugin.PngInfo();info.add_text('Comment','must-not-survive-thumbnail')
    Image.new('RGB',(240,120),(140,80,190)).save(image,format='PNG',pnginfo=info)
    data=challenge(request)
    response=post(request,data,name='Profile QA',body='<script>window.wallXSS=true</script>\nA real local test.',
        avatar={'name':'original-profile-name.png','mimeType':'image/png','buffer':image.getvalue()})
    assert response.status==201,response.text()
    posted=response.json();identifier=posted['id']
    assert request.get(API+'?action=list').json()['total']==0, 'Pending comment was public'
    assert request.get(API+f'?action=avatar&id={identifier}').status==404, 'Pending thumbnail was public'
    with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
        db.execute('UPDATE comments SET reviewed=1 WHERE id=?',(identifier,))
    avatar=request.get(API+f'?action=avatar&id={identifier}')
    assert avatar.headers['content-type']=='image/png'
    assert Image.open(BytesIO(avatar.body())).size==(128,128)
    assert b'must-not-survive-thumbnail' not in avatar.body()
    public=request.get(API+'?action=list').json()
    assert public['total']==1 and public['comments'][0]['has_avatar'] is True
    assert set(public['comments'][0])=={'id','name','body','created_at','has_avatar'}
    assert request.post(API+'?action=delete',headers=origin,multipart={
        'csrf':data['csrf'],'id':identifier,'delete_token':'a'*64}).status==403
    deletion=request.post(API+'?action=delete',headers=origin,multipart={
        'csrf':data['csrf'],'id':str(identifier),'delete_token':posted['delete_token']})
    assert deletion.status==200,deletion.text()
    assert request.get(API+'?action=list').json()['total']==0
    # Force a consumed limit bucket without sending dozens of requests.
    request.get(API+'?action=challenge')
    with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
        db.execute("UPDATE limits SET count=60 WHERE bucket='challenge'")
    assert request.get(API+'?action=challenge').status==429
    clear_limits();request.dispose()

    browser=p.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1100})
    page=context.new_page();errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(BASE,wait_until='networkidle')
    page.locator('#comments').scroll_into_view_if_needed()
    expect(page.locator('#comments .wall-submit')).to_be_enabled()
    page.locator('#wall-name').fill('Tiny pixel visitor')
    page.locator('#wall-body').fill('<script>window.wallXSS=true</script>\nLove the tiny music machine ♥')
    page.locator('#wall-avatar').set_input_files({'name':'profile.png','mimeType':'image/png','buffer':image.getvalue()})
    expect(page.locator('#wall-preview')).to_be_visible()
    nonce=page.locator('#wall-code-image').get_attribute('src').split('nonce=')[1]
    page.locator('#wall-human-code').fill(code_for(context.request,nonce));time.sleep(2.05)
    with page.expect_response(lambda r:'comments/api.php?action=post' in r.url) as posted_response:
        page.locator('#comments .wall-submit').click()
    pending_id=posted_response.value.json()['id']
    expect(page.locator('#wall-status')).to_contain_text('after the site owner approves')
    expect(page.locator('.wall-comment')).to_have_count(0)
    with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
        db.execute('UPDATE comments SET reviewed=1 WHERE id=?',(pending_id,))
    page.reload(wait_until='networkidle')
    expect(page.locator('.wall-comment')).to_have_count(1)
    expect(page.locator('.wall-message p')).to_contain_text('<script>window.wallXSS=true</script>')
    assert page.evaluate('window.wallXSS===undefined')
    assert page.locator('.wall-message script').count()==0
    expect(page.locator('.wall-profile img')).to_have_attribute('src',re.compile('action=avatar'))
    page.locator('#comments').screenshot(path=str(ROOT/'build/comments-desktop.png'))
    for width in [768,390,320]:
        page.set_viewport_size({'width':width,'height':900})
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),f'Overflow at {width}'
    page.set_viewport_size({'width':390,'height':900})
    page.locator('#comments').screenshot(path=str(ROOT/'build/comments-mobile.png'))
    # Browser restart/reload keeps the author's deletion capability.
    page.reload(wait_until='networkidle');expect(page.locator('.wall-delete')).to_be_visible()
    page.locator('.wall-delete').click();expect(page.locator('.wall-comment')).to_have_count(0)
    assert not errors,errors
    # Both human-check alternatives are generated, with no code in JSON.
    result=context.request.get(API+'?action=challenge').json()
    assert set(result)=={'csrf','nonce'}
    assert context.request.get(API+'?action=image&nonce='+result['nonce']).body().startswith(b'\x89PNG')
    assert context.request.get(API+'?action=audio&nonce='+result['nonce']).body().startswith(b'RIFF')
    browser.close()
    print(json.dumps({'backend':'CSRF, human-check timing/answer/replay, honeypot, rate limits passed',
        'uploads':'SVG rejected; excessive dimensions rejected; PNG cropped and stripped of metadata',
        'browser':'posting, escaped text, thumbnail preview, deletion after reload passed',
        'layouts':'desktop, tablet, 390px and 320px passed','human_check':'image and audio passed',
        'public_test_posts':0,'browser_errors':[]}))
