"""Real-browser and API checks against an isolated, locally served network."""
import base64
import io
import json
import secrets
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:18981/'
ROOT=Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome')
    contexts=[browser.new_context() for _ in range(3)]
    clients=[]
    for i,c in enumerate(contexts):
        session=c.request.get(BASE+'api.php').json()
        token=session['csrf']
        def post(action,data,c=c,token=token):
            return c.request.post(BASE+'api.php?action='+action,data=data,headers={'X-CSRF-Token':token})
        handle='qa_'+secrets.token_hex(4)
        response=post('register',{'handle':handle,'password':secrets.token_urlsafe(20)})
        assert response.status==200,response.text()
        clients.append((c,post,response.json()['user']))
    a,apost,alice=clients[0];b,bpost,bob=clients[1];c,cpost,carol=clients[2]
    assert a.request.post(BASE+'api.php?action=profile',data={}).status==403
    raw=io.BytesIO();Image.new('RGBA',(128,128),'#ff69b4').save(raw,format='PNG');tag='data:image/png;base64,'+base64.b64encode(raw.getvalue()).decode()
    assert apost('tag',{'art':tag}).status==200
    assert apost('mark',{'owner':bob['id'],'x':20,'y':30}).status==200
    marks=b.request.get(BASE+f'api.php?action=page&id={bob["id"]}').json()['marks'];assert marks[-1]['art']==tag
    raw=io.BytesIO();Image.new('RGBA',(128,128),'#baff37').save(raw,format='PNG');newtag='data:image/png;base64,'+base64.b64encode(raw.getvalue()).decode()
    assert apost('tag',{'art':newtag}).status==200
    assert b.request.get(BASE+f'api.php?action=page&id={bob["id"]}').json()['marks'][-1]['art']==tag
    profile={'bio':'A person, not a metric.','color':'#baff37','wallpaper':'grid','status':'available','bathroom':True,'blocks':[{'type':'text','value':'<script>alert(1)</script>'}]}
    assert apost('profile',profile).status==200
    assert apost('mint',{'name':'ONE OF ONE','art':tag}).status==200
    assert apost('mint',{'name':'DUPLICATE','art':tag}).status==422
    own=a.request.get(BASE+'api.php?action=inventory').json()['pins'];other=b.request.get(BASE+'api.php?action=inventory').json()['pins']
    assert bpost('give',{'pin':own[0]['id'],'recipient':carol['id']}).status==422
    assert apost('trade',{'pin':own[0]['id'],'recipient':bob['id'],'wanted':other[0]['id']}).status==200
    trade=b.request.get(BASE+'api.php?action=inventory').json()['trades'][-1]
    assert cpost('trade-answer',{'id':trade['id'],'accept':True}).status==422
    assert bpost('trade-answer',{'id':trade['id'],'accept':True}).status==200
    assert bpost('trade-answer',{'id':trade['id'],'accept':True}).status==422
    assert any(pin['id']==other[0]['id'] for pin in a.request.get(BASE+'api.php?action=inventory').json()['pins'])
    assert apost('give',{'pin':own[1]['id'],'recipient':bob['id']}).status==200
    assert apost('give',{'pin':own[1]['id'],'recipient':carol['id']}).status==422
    assert apost('send',{'recipient':bob['id'],'body':'PRIVATE QA MESSAGE','room':''}).status==200
    assert b.request.get(BASE+f'api.php?action=messages&recipient={alice["id"]}').json()[-1]['body']=='PRIVATE QA MESSAGE'
    assert not c.request.get(BASE+f'api.php?action=messages&recipient={alice["id"]}').json()
    assert apost('send',{'room':'lobby','body':'ROOM QA MESSAGE'}).status==200
    assert b.request.get(BASE+'api.php?action=messages&room=lobby').json()[-1]['body']=='ROOM QA MESSAGE'
    assert bpost('block',{'target':alice['id']}).status==200
    assert apost('send',{'recipient':bob['id'],'body':'blocked','room':''}).status==403
    assert apost('mark',{'owner':bob['id'],'body':'blocked'}).status==403
    assert bpost('unblock',{'target':alice['id']}).status==200
    assert bpost('profile',{**profile,'bathroom':False}).status==200
    assert apost('mark',{'owner':bob['id'],'body':'closed'}).status==403
    assert apost('report',{'kind':'member','target':bob['id'],'reason':'Local QA only'}).status==200
    print('PASS: CSRF, accounts, tag history, one-time mint, ownership, atomic trades, private DMs, rooms, blocks, bathroom privacy, reports')
    page=a.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    for route in ['home','directory','page','edit','paint','pins','chat','apps']:
        page.goto(BASE+'#'+route);page.wait_for_timeout(400)
        assert page.locator('#view').inner_text().strip(),route
        assert 'CONNECTION INTERRUPTED' not in page.locator('#view').inner_text(),route
    page.goto(BASE+'#page');page.wait_for_timeout(300)
    assert page.locator('.block').inner_text()=='<script>alert(1)</script>'
    page.goto(BASE+'#paint');page.wait_for_timeout(300)
    canvas=page.locator('#paint');box=canvas.bounding_box();page.mouse.move(box['x']+40,box['y']+40);page.mouse.down();page.mouse.move(box['x']+80,box['y']+80,steps=8);page.mouse.up()
    assert page.evaluate("document.querySelector('#paint').getContext('2d').getImageData(0,0,128,128).data.some(v=>v!==0)")
    page.get_by_role('button',name='UNDO',exact=True).click();page.get_by_role('button',name='REDO',exact=True).click()
    page.goto(BASE+'#home');page.wait_for_timeout(300)
    (ROOT/'build/network-qa').mkdir(exist_ok=True,parents=True)
    for width in [1440,768,390,320]:
        page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(100)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'Overflow at {width}'
        page.screenshot(path=str(ROOT/f'build/network-qa/home-{width}.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000});page.goto(BASE+'#page');page.wait_for_timeout(300);page.screenshot(path=str(ROOT/'build/network-qa/profile.png'),full_page=True)
    assert not errors,errors
    print('PASS: eight browser routes, HTML escaping, paint interaction, undo/redo, desktop/mobile overflow, no JavaScript errors')
    browser.close()
