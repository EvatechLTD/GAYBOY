"""Exercise the complete network against isolated local storage, never production."""
from pathlib import Path
import base64
import io
import json
import secrets
import sqlite3
import sys
from PIL import Image
from playwright.sync_api import sync_playwright, expect

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:18981/'
DATA=ROOT/'build/network-v2-qa'
OUT=DATA/'screenshots';OUT.mkdir(parents=True,exist_ok=True)
with sqlite3.connect(DATA/'network.sqlite') as db:db.execute('DELETE FROM limits')
def png(c):
    f=io.BytesIO();Image.new('RGBA',(128,128),c).save(f,format='PNG');return 'data:image/png;base64,'+base64.b64encode(f.getvalue()).decode()
tag1,tag2=png('#ff81d9'),png('#baff37')
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome')
    contexts=[browser.new_context(viewport={'width':1440,'height':1100}) for _ in range(3)]
    clients=[]
    for context in contexts:
        token=context.request.get(BASE+'api.php').json()['csrf']
        def post(action,data,context=context,token=token):return context.request.post(BASE+'api.php?action='+action,data=data,headers={'X-CSRF-Token':token})
        def get(action,context=context,**args):return context.request.get(BASE+'api.php',params={'action':action,**args})
        handle='v2_'+secrets.token_hex(4);password=secrets.token_urlsafe(20)
        r=post('register',{'handle':handle,'password':password});assert r.status==200,r.text()
        clients.append({'ctx':context,'post':post,'get':get,'u':r.json()['user'],'password':password})
    A,B,C=clients;a,b,c=[x['u']['id'] for x in clients];ap,bp,cp=[x['post'] for x in clients];ag,bg,cg=[x['get'] for x in clients]
    def ok(r):assert r.status==200,r.text();return r.json()
    def denied(r):assert r.status in [401,403,404,422],r.text()
    assert contexts[0].request.post(BASE+'api.php?action=profile',data={}).status==403
    asset=ok(ap('upload',{'data':tag1}))['url'];assert contexts[2].request.get(BASE+asset).headers['content-type']=='image/png'
    denied(ap('upload',{'data':'data:image/svg+xml;base64,PHN2Zz4='}))
    blocks=[{'id':'intro','type':'text','title':'My blurb','value':'<script>window.BAD=true</script>','column':'main','items':[]},{'id':'song','type':'media','title':'My song','value':'https://soundcloud.com/forss/flickermood','items':[]},{'id':'pics','type':'gallery','title':'My pictures','value':'','items':[{'label':'tiny art','image':asset,'url':'','text':''}]}]
    settings={'title':'A REAL HOMEPAGE','displayName':'Pixel Person','avatar':asset,'quote':'A processor is an animal breathing','pattern':'stars','glitter':True,'tickerMotion':True,'visitorCounter':True,'badges':['HELLO\nWORLD'],'links':[{'label':'A link worth visiting','url':'https://example.com'}],'decorations':[],'featuredFriends':[b],'soundtrack':'https://youtu.be/M7lc1UVf-VE','showBathroom':True,'showGuestbook':True}
    profile={'bio':'A long personal story. '*7,'color':'#d5ff39','status':'available','away':'making something','bathroom':True,'settings':settings,'blocks':blocks}
    ok(ap('tag',{'art':tag1}));ok(ap('save-page',profile));page=ok(ag('page',id=a));assert json.loads(page['user']['settings'])['avatar']==asset
    denied(ap('save-page',{**profile,'blocks':blocks*5}));denied(ap('save-page',{**profile,'settings':{**settings,'avatar':'javascript:alert(1)'}}))
    ok(ap('save-page',{**profile,'slug':'my-mixtapes','title':'My mixtapes'}));assert ok(ag('page',id=a,slug='my-mixtapes'))['user']['pageTitle']=='My mixtapes'
    denied(bp('restore-page',{'id':ok(ag('revisions'))[0]['id']}))
    ok(ap('friend',{'target':b}));denied(ap('friend',{'target':b,'op':'accept'}));ok(bp('friend',{'target':a,'op':'accept'}));assert ok(ag('friends'))[0]['state']=='accepted'
    ok(bp('save-page',{'bio':'Buddy only','settings':{'dmPolicy':'friends','bathroomMode':'approve','guestbookMode':'approve'},'blocks':[],'bathroom':True}))
    denied(cp('send',{'recipient':b,'body':'stranger','room':''}));ok(ap('send',{'recipient':b,'body':'private uWu <script>NO</script>','room':''}));assert not ok(cg('messages',recipient=a))
    ok(ap('guestbook',{'owner':b,'body':'Your page feels like home.','art':tag1}));assert not ok(cg('page',id=b))['guestbook']
    notes=ok(bg('page',id=b))['guestbook'];ok(bp('moderate-note',{'id':notes[-1]['id'],'op':'approve'}));assert len(ok(cg('page',id=b))['guestbook'])==1
    ok(ap('mark',{'owner':b,'x':30,'y':40,'rotation':15}));marks=ok(bg('page',id=b))['marks'];mid=marks[-1]['id'];assert not ok(cg('page',id=b))['marks'];ok(bp('moderate-mark',{'id':mid,'op':'approve'}))
    ok(ap('tag',{'art':tag2}));assert ok(cg('page',id=b))['marks'][-1]['art']==tag1
    ok(bp('moderate-mark',{'id':mid,'op':'archive'}));assert not ok(cg('page',id=b))['marks'];ok(bp('moderate-mark',{'id':mid,'op':'restore'}))
    ok(ap('postcard',{'recipient':b,'body':'I made this for you.','bg':'#ff81d9'}));cards=ok(bg('desk'))['postcards'];assert not ok(cg('page',id=b))['postcards'];ok(bp('display-postcard',{'id':cards[-1]['id'],'displayed':True}));assert len(ok(cg('page',id=b))['postcards'])==1
    inv=ok(ag('inventory'));assert all(inv['available'].values()),inv['available']
    for award in ['made-my-place','personal-style','curator','storyteller']:ok(ap('mint',{'award':award,'name':'FRIENDSHIP','art':tag1,'edition':2 if award=='personal-style' else 1}))
    denied(ap('mint',{'award':'personal-style','name':'DUPLICATE','art':tag1,'edition':3}))
    own=ok(ag('inventory'))['pins'];other=ok(bg('inventory'))['pins'];assert len(own)==8
    denied(bp('give',{'pin':own[0]['id'],'recipient':c}));ok(ap('trade',{'pin':own[0]['id'],'recipient':b,'wanted':other[0]['id']}));offer=ok(bg('inventory'))['trades'][-1];denied(cp('trade-answer',{'id':offer['id'],'accept':True}));ok(bp('trade-answer',{'id':offer['id'],'accept':True}));denied(bp('trade-answer',{'id':offer['id'],'accept':True}))
    ok(ap('give',{'pin':own[1]['id'],'recipient':b}));denied(ap('give',{'pin':own[1]['id'],'recipient':c}))
    ok(ap('ring-save',{'slug':'ring-'+secrets.token_hex(3),'title':'Tiny music machines','description':'People who make small noises.'}));ring=ok(ag('rings'))[-1]['slug'];ok(bp('ring-join',{'ring':ring}));assert len(next(r for r in ok(ag('rings')) if r['slug']==ring)['members'])==2
    ok(ap('bulletin',{'body':'What are you making?'}));bid=ok(ag('board'))[0]['id'];ok(bp('bulletin',{'body':'A mixtape.','reply':bid}));assert ok(ag('board'))[0]['reply']==bid
    slug='room-'+secrets.token_hex(4);ok(ap('room-save',{'slug':slug,'title':'Bedroom listening room','capacity':2,'privacy':'friends','history':True,'media':'https://soundcloud.com/forss/flickermood','wallpaper':asset}));denied(bp('room-save',{'slug':slug,'title':'Stolen'}));denied(cp('room-join',{'room':slug}));ok(ap('room-join',{'room':slug}));ok(bp('room-join',{'room':slug}));ok(ap('send',{'room':slug,'body':'hi uWu :) <3'}));assert ok(bg('messages',room=slug))[-1]['body']=='hi uWu :) <3'
    denied(bp('room-moderate',{'room':slug,'target':c,'op':'ban'}));ok(ap('room-moderate',{'room':slug,'target':b,'op':'moderator'}));msgid=ok(bg('messages',room=slug))[-1]['id'];ok(bp('room-moderate',{'room':slug,'id':msgid,'op':'delete-message'}));assert not ok(ag('messages',room=slug))
    public='room-'+secrets.token_hex(4);ok(ap('room-save',{'slug':public,'title':'Two seats','capacity':2,'privacy':'public','history':False}));ok(ap('room-join',{'room':public}));ok(ap('send',{'room':public,'body':'Before you arrived'}));ok(bp('room-join',{'room':public}));assert not ok(bg('messages',room=public));denied(cp('room-join',{'room':public}));ok(bp('send',{'room':public,'body':'After I arrived'}));assert len(ok(bg('messages',room=public)))==1
    ok(ap('room-moderate',{'room':public,'target':b,'op':'ban'}));denied(bp('send',{'room':public,'body':'banned'}));ok(ap('room-moderate',{'room':public,'target':b,'op':'unban'}))
    ok(bp('block',{'target':a}));denied(ap('send',{'recipient':b,'body':'blocked'}));denied(ap('mark',{'owner':b,'body':'blocked'}));ok(bp('unblock',{'target':a}))
    print('PASS API: uploads; settings; safe URLs; page limits; subpages/revisions; buddies; DM privacy; guestbook approval; tag history; bathroom archive; private/displayed postcards; four finite achievements; fixed pin editions; ownership/trades; webrings; board replies; hosted rooms; capacity/privacy; no-history cutoff; moderator authority; bans; blocks')

    page=contexts[0].new_page();errors=[];console=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
    page.goto(BASE+'#edit');page.wait_for_selector('#builder-form')
    page.locator('[data-editor-tab=profile]').click();page.locator('[name="s.title"]').fill('MY VERY OWN INTERNET');page.locator('[name="s.pronouns"]').fill('they/them');page.get_by_role('button',name='SAVE PAGE').click();expect(page.locator('#draft-status')).to_have_text('Your page is live.')
    page.locator('[data-editor-tab=blocks]').click();page.locator('[data-select-block="1"]').click();page.locator('[name="b.value"]').fill('https://youtu.be/M7lc1UVf-VE?t=12');expect(page.locator('.media-detected')).to_contain_text('YouTube player detected');page.get_by_role('button',name='SAVE PAGE').click();expect(page.locator('#draft-status')).to_have_text('Your page is live.')
    page.locator('[data-editor-tab=jacket]').click();page.locator('#add-pin').click();expect(page.locator('#builder-preview .jacket-decor.pin')).to_have_count(1)
    page.get_by_role('button',name='SAVE PAGE').click();expect(page.locator('#draft-status')).to_have_text('Your page is live.')
    page.goto(BASE+'~'+A['u']['handle']);page.wait_for_selector('.homepage');expect(page.locator('.hp-header h1')).to_have_text('MY VERY OWN INTERNET');expect(page.locator('.hp-text')).to_have_text('<script>window.BAD=true</script>');assert not page.evaluate('window.BAD || false')
    assert page.locator('iframe[src*="youtube-nocookie.com"]').count()>=1
    page.goto(BASE+'#chat/room/'+slug);page.wait_for_selector('#transcript');page.locator('[name=body]').fill('hello uWu :) <3');page.get_by_role('button',name='SEND',exact=False).click();expect(page.locator('#transcript .chat-emoji')).to_have_count(1);expect(page.locator('#transcript .text-emoji')).to_have_count(2)
    assert page.locator('.chat-emoji').first.evaluate('(i)=>i.complete && i.naturalWidth>0')
    page.locator('.emoji-picker summary').click();page.locator('[data-insert-emoji="uWu"]').click();assert 'uWu' in page.locator('[name=body]').input_value()
    page.goto(BASE+'#chat/dm/'+str(b));page.wait_for_selector('#im-send');page.locator('#im-text').fill('uWu lives here');page.locator('#im-send button').click();expect(page.locator('#im-messages .chat-emoji')).to_have_count(2)
    page.goto(BASE+'#board');page.wait_for_selector('#bulletin-form');expect(page.locator('#im-dock')).to_be_visible();page.locator('#close-im').click()
    page.goto(BASE+'#paint');page.wait_for_selector('#paint');page.get_by_role('button',name='TEXT',exact=True).click();page.locator('[name=words]').fill('BUG');page.locator('#paint').click(position={'x':20,'y':20});page.locator('[name=words]').fill('MY BUG');expect(page.locator('#paint-layers')).to_contain_text('MY BUG');page.get_by_role('button',name='UNDO',exact=True).click();page.get_by_role('button',name='REDO',exact=True).click();page.once('dialog',lambda d:d.accept());page.locator('#save-tag').click()
    # Snapshot all major routes at desktop and narrow phone widths.
    for route,selector in [('home','.hero'),('directory','#neighbors'),('page/GAYBOY','.homepage'),('edit','#builder-form'),('paint','#paint'),('pins','.pin-catalog'),('chat','.directory'),('board','.bulletin-list'),('desk','.section-grid'),('rings','.directory'),('apps','.app-card')]:
        page.goto(BASE+'#'+route);page.wait_for_selector(selector);page.wait_for_timeout(150)
        for width in [1440,390,320]:
            page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(100)
            overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
            assert not overflow,f'Overflow {route} at {width}'
            if width in [1440,390]:page.screenshot(path=str(OUT/(route.replace('/','-')+'-'+str(width)+'.png')),full_page=True)
    assert not errors,errors
    # Boot the real packaged app within the real homepage iframe.
    page.set_viewport_size({'width':1440,'height':1100});page.goto(BASE+'~GAYBOY');page.wait_for_selector('.hp-app');page.locator('.hp-app').scroll_into_view_if_needed();frame=page.frame_locator('.hp-app');frame.locator('#demo-play').wait_for();frame.locator('#demo-play').click();expect(frame.locator('.demo-status')).to_contain_text('Playing!',timeout=15000)
    print('PASS BROWSER: builder settings save; live media preview; jacket placement; public permalinks; escaping; room and DM emoji conversion; emoticon picker; persistent floating messenger; editable paint text; undo/redo; eleven routes at desktop/390/320; actual GAYBOY boot in shared homepage')
    assert not errors,errors
    # Recovery is one-time and does not require disclosure of email addresses.
    code=ok(ap('recovery-code',{}))['code'];token=contexts[2].request.get(BASE+'api.php').json()['csrf'];r=contexts[2].request.post(BASE+'api.php?action=recover',data={'handle':A['u']['handle'],'code':code,'password':'a-new-password-for-local-qa'},headers={'X-CSRF-Token':token});ok(r)
    r=contexts[2].request.post(BASE+'api.php?action=recover',data={'handle':A['u']['handle'],'code':code,'password':'another-new-password'},headers={'X-CSRF-Token':token});denied(r)
    assert ok(ag('session'))['user'] is None
    print('PASS: single-use account recovery code and old-session invalidation')
    browser.close()
