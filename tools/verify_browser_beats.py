"""Share real emulator music against isolated local PHP; never posts publicly."""
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import time
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'build/comments-private'
BASE='http://127.0.0.1:18978/'
INSTRUMENT='''
const factory=window.SameBoyCore;
window.SameBoyCore=async(...args)=>{
 const m=await factory(...args);window.qaCore=m;window.qaMachines=[];
 const create=m._emulator_new_simple;
 m._emulator_new_simple=(...args)=>{const e=create(...args);qaMachines.push(e);window.qaInstance=e;return e;};
 return m;
};
'''
AUDIO='''
window.qaBeatPeak=0;
const create=AudioContext.prototype.createBufferSource;
AudioContext.prototype.createBufferSource=function(...args){
 const source=create.apply(this,args),start=source.start;
 source.start=function(...args){if(source.buffer){for(const v of source.buffer.getChannelData(0))window.qaBeatPeak=Math.max(qaBeatPeak,Math.abs(v));}return start.apply(this,args);};return source;
};
'''
def code_for(context,nonce):
    sid=next(c['value'] for c in context.cookies() if c['name']=='GAYBOYWALL')
    text=(PRIVATE/'sessions'/('sess_'+sid)).read_text()
    return re.search(re.escape(nonce)+r'";a:\d+:\{s:4:"code";s:6:"(\d{6})";',text).group(1)

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
    page=context.new_page();errors=[]
    page.add_init_script(AUDIO)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/emulator/sameboy.js*',lambda r:r.fulfill(response=(response:=r.fetch()),body=response.text()+INSTRUMENT))
    page.goto(BASE,wait_until='networkidle')
    assert context.request.post(BASE+'beats/api.php?action=post',multipart={'name':'bot'}).status==403
    page.locator('#demo-play').tap();page.wait_for_timeout(3200)
    page.keyboard.down('Shift');page.wait_for_timeout(1600);page.keyboard.up('Shift');page.wait_for_timeout(500)
    metadata=page.evaluate("async()=>await(await fetch('emulator/tutorial-rom.json')).json()")
    page.evaluate('(m)=>{window.qaMap=m;window.qaRead=n=>qaCore._emulator_observe_mem(qaInstance,m.symbols[n]);}',metadata)
    assert page.evaluate('qaRead("page")')==8
    # Plot a note in the real sequencer, then start playback.
    page.keyboard.press('z',delay=200);page.wait_for_timeout(400)
    page.keyboard.down('Space');page.wait_for_timeout(200);page.keyboard.press('x',delay=200);page.keyboard.up('Space')
    page.wait_for_function('()=>qaRead("seqplaying")===1')
    page.evaluate('()=>{window.qaOriginal=qaInstance;window.qaOriginalTicks=qaCore._emulator_get_ticks_f64(qaInstance)}')
    page.locator('#demo-share').click()
    expect(page.locator('.beat-dialog')).to_be_visible()
    expect(page.locator('.beat-dialog [type=submit]')).to_be_enabled()
    page.locator('#beat-name').fill('Beat QA visitor')
    page.locator('#beat-title').fill('<script>window.beatXSS=true</script>')
    nonce=page.locator('.beat-dialog img').get_attribute('src').split('nonce=')[1]
    page.locator('#beat-code').fill(code_for(context,nonce));page.wait_for_timeout(2100)
    with page.expect_response(lambda r:'beats/api.php?action=post' in r.url) as response:
        page.locator('.beat-dialog [type=submit]').click()
    result=response.value
    assert result.status==201,result.text()
    beat=result.json();identifier=beat['id']
    assert 'delete_token' not in beat
    try:
        expect(page.locator('.beat-row').filter(has_text='<script>')).to_be_visible()
        assert page.evaluate('window.beatXSS') is None
        data=context.request.get(BASE+'beats/api.php?action=beat&id='+identifier).json()
        import base64
        snapshot=base64.b64decode(data['snapshot']);assert hashlib.sha256(snapshot).hexdigest()==data['sha']
        assert snapshot[:8]==b'GBBT0001' and snapshot[-4:]==b'BESS'
        assert context.request.get(BASE+'beats/api.php?action=beat&id=../secret').status==404
        challenge=context.request.get(BASE+'beats/api.php?action=challenge').json()
        payload={**challenge,'name':'Invalid QA','title':'Not a beat','website':'','human_code':code_for(context,challenge['nonce']),
            'snapshot':{'name':'beat.gbb','mimeType':'application/octet-stream','buffer':b'bad snapshot'}}
        assert context.request.post(BASE+'beats/api.php?action=post',headers={'Origin':'https://evil.invalid'},multipart=payload).status==403
        assert context.request.post(BASE+'beats/api.php?action=post',headers={'Origin':BASE.rstrip('/')},multipart={**payload,'csrf':'wrong'}).status==403
        page.wait_for_timeout(2100)
        assert context.request.post(BASE+'beats/api.php?action=post',headers={'Origin':BASE.rstrip('/')},multipart=payload).status==422
        assert context.request.post(BASE+'beats/api.php?action=post',headers={'Origin':BASE.rstrip('/')},multipart=payload).status==400
        # Sharing captures the live note, without requiring an in-game SRAM save.
        page.locator('.beat-play').filter(has_text='<script>').click()
        expect(page.locator('button').filter(has_text='back to my beat')).to_be_visible()
        page.wait_for_function('()=>qaRead("seqplaying")===1')
        page.evaluate('()=>window.qaBeatPeak=0');page.wait_for_function('()=>qaBeatPeak>0.02',timeout=10000)
        assert page.evaluate('qaInstance!==qaOriginal')
        assert page.evaluate('qaRead("seqtrack")')==6
        assert page.evaluate('()=>qaCore._emulator_observe_mem(qaInstance,qaMap.symbols.seqeventcounts+12)')==1
        # Audition cannot replace the visitor's local save or parked session.
        frozen=page.evaluate('qaCore._emulator_get_ticks_f64(qaOriginal)')
        page.wait_for_timeout(300)
        assert page.evaluate('qaCore._emulator_get_ticks_f64(qaOriginal)')==frozen
        page.get_by_role('button',name='back to my beat',exact=False).click()
        page.wait_for_function('(frozen)=>qaCore._emulator_get_ticks_f64(qaOriginal)>frozen',arg=frozen)
        # Open the shared URL in a fresh phone context. One tap starts the sequence.
        other=browser.new_context(viewport={'width':375,'height':667},has_touch=True)
        listener=other.new_page()
        listener.add_init_script(AUDIO)
        listener.route('**/emulator/sameboy.js*',lambda r:r.fulfill(response=(response:=r.fetch()),body=response.text()+INSTRUMENT))
        listener.goto(BASE+'?beat='+identifier+'#live-demo',wait_until='networkidle')
        expect(listener.locator('#demo-play')).to_have_text('▶ PLAY THIS BEAT')
        listener.locator('#demo-play').tap()
        expect(listener.get_by_role('button',name='back to my beat',exact=False)).to_be_visible(timeout=30000)
        listener.wait_for_function('(m)=>qaCore._emulator_observe_mem(qaInstance,m.symbols.seqplaying)===1',arg=metadata)
        listener.evaluate('()=>window.qaBeatPeak=0');listener.wait_for_function('()=>qaBeatPeak>0.02',timeout=10000)
        listener.screenshot(path=str(ROOT/'build/shared-beat-mobile.png'))
        other_csrf=other.request.get(BASE+'beats/api.php?action=challenge').json()['csrf']
        assert other.request.post(BASE+'beats/api.php?action=delete',headers={'Origin':BASE.rstrip('/')},multipart={'csrf':other_csrf,'id':identifier,'delete_token':'a'*64}).status==403
        other.close()
        expect(page.get_by_role('button',name='delete my beat')).to_have_count(0)
        legacy_token='b'*64
        with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
            db.execute('UPDATE beats SET delete_hash=? WHERE id=?',(hashlib.sha256(legacy_token.encode()).hexdigest(),identifier))
        author_csrf=context.request.get(BASE+'beats/api.php?action=challenge').json()['csrf']
        assert context.request.post(BASE+'beats/api.php?action=delete',headers={'Origin':BASE.rstrip('/')},multipart={'csrf':author_csrf,'id':identifier,'delete_token':legacy_token}).status==403
        assert context.request.get(BASE+'beats/api.php?action=beat&id='+identifier).status==200
        assert not errors,errors
        print(json.dumps({'snapshot_bytes':len(snapshot),'live_note':'restored without saving a pattern','links':'same-page playback and fresh phone one-tap playback','original_music':'preserved','public_text':'escaped','public_deletion':'denied, including valid legacy author token','browser_errors':errors}))
    finally:
        with sqlite3.connect(PRIVATE/'comments.sqlite') as db:
            db.execute('DELETE FROM beats WHERE id=?',(identifier,));db.execute('DELETE FROM limits')
    browser.close()
