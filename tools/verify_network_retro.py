"""Local-only playback QA. Test songs stay in build/, outside deployment."""
import base64
from pathlib import Path
import secrets
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:18981/'
FIXTURES=ROOT/'build/retro-research'

# Observe real output samples, rather than treating a Play label as playback.
AUDIO_PROBE="""(() => {
 window.__audioPeak=0;window.__audioAnalysers=[];
 const connect=AudioNode.prototype.connect;
 AudioNode.prototype.connect=function(destination,...args){
  if(destination===this.context.destination){
   const a=this.context.createAnalyser();a.fftSize=2048;
   window.__audioAnalysers.push(a);connect.call(a,destination);
   return connect.call(this,a,...args);
  }return connect.call(this,destination,...args);
 };
 setInterval(()=>{for(const a of window.__audioAnalysers){const b=new Float32Array(a.fftSize);a.getFloatTimeDomainData(b);for(const v of b)window.__audioPeak=Math.max(window.__audioPeak,Math.abs(v));}},40);
})();"""

with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome')
    context=browser.new_context(viewport={'width':1200,'height':900})
    context.add_init_script(AUDIO_PROBE)
    csrf=context.request.get(BASE+'api.php').json()['csrf']
    handle='retro_'+secrets.token_hex(3)
    r=context.request.post(BASE+'api.php?action=register',data={'handle':handle,'password':secrets.token_urlsafe(20)},headers={'X-CSRF-Token':csrf})
    assert r.status==200,r.text()
    headers={'X-CSRF-Token':csrf}
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    files={}
    for name in ['test.mid','cybernoid.sid','ambpower.mod','inside_out.s3m','radix_xyce_-_rainbow_dash_.xm']:
        raw=(FIXTURES/name).read_bytes()
        r=context.request.post(BASE+'api.php?action=upload-music',data={'name':name,'data':base64.b64encode(raw).decode()},headers=headers)
        assert r.status==200,r.text();files[name]=r.json()['url']
        saved=context.request.get(BASE+files[name]);assert saved.body()==raw
        assert 'attachment' in saved.headers['content-disposition']
        page.goto(BASE+'retro/player.html?'+urlencode({'src':BASE+files[name],'format':Path(name).suffix[1:]}))
        assert page.evaluate('window.__audioAnalysers.length')==0
        page.locator('#play').click()
        expect(page.locator('#status')).to_have_text('Playing.',timeout=25000)
        page.wait_for_function('window.__audioPeak>0.0001',timeout=12000)
        page.wait_for_function("document.querySelector('#time').textContent.split(' / ')[0]!=='0:00'",timeout=5000)
        assert page.locator('#time').inner_text().split(' / ')[0]!='0:00',page.locator('#time').inner_text()
        page.locator('#play').click();expect(page.locator('#status')).to_have_text('Paused.')
        page.wait_for_timeout(300);before=page.locator('#time').inner_text();page.wait_for_timeout(600);assert page.locator('#time').inner_text()==before
        page.locator('#volume').fill('0');page.locator('#volume').dispatch_event('input')
        page.locator('#play').click();expect(page.locator('#status')).to_have_text('Playing.')
        page.wait_for_timeout(700)
        peak=page.evaluate('''()=>{let peak=0;for(const a of window.__audioAnalysers){const b=new Float32Array(a.fftSize);a.getFloatTimeDomainData(b);for(const v of b)peak=Math.max(peak,Math.abs(v));}return peak;}''')
        assert peak<0.00001,('mute output',name,peak)
        page.locator('#stop').click();expect(page.locator('#status')).to_have_text('Stopped.')
        if name=='test.mid':
            page.locator('#loop').check();page.locator('#play').click();page.wait_for_timeout(8500)
            expect(page.locator('#status')).to_have_text('Playing.');page.locator('#stop').click()
        if name=='cybernoid.sid':
            page.locator('#volume').fill('60');page.locator('#volume').dispatch_event('input')
            page.evaluate('window.__audioPeak=0');page.locator('#subsong').select_option('2')
            expect(page.locator('#status')).to_have_text('Playing.');page.wait_for_function('window.__audioPeak>0.0001',timeout=10000)
            page.locator('#stop').click()
        print('PASS: audible decoding, advancing clock, pause/resume, volume, stop:',name)
    # Reject renamed HTML, oversize files, missing IDs, unauthenticated uploads.
    r=context.request.post(BASE+'api.php?action=upload-music',data={'name':'bad.sid','data':base64.b64encode(b'<html>'+b'a'*150).decode()},headers=headers);assert r.status==422
    assert context.request.get(BASE+'api.php?action=music&id=bad&format=mid').status==404
    anonymous=browser.new_context();anoncsrf=anonymous.request.get(BASE+'api.php').json()['csrf']
    assert anonymous.request.post(BASE+'api.php?action=upload-music',data={'name':'test.mid','data':base64.b64encode((FIXTURES/'test.mid').read_bytes()).decode()},headers={'X-CSRF-Token':anoncsrf}).status in [401,403]
    # Only the uploader may remove a shelf entry; shared bytes survive other removals.
    other=browser.new_context();othercsrf=other.request.get(BASE+'api.php').json()['csrf'];otherheaders={'X-CSRF-Token':othercsrf}
    r=other.request.post(BASE+'api.php?action=register',data={'handle':'retro_'+secrets.token_hex(3),'password':secrets.token_urlsafe(20)},headers=otherheaders);assert r.status==200
    shared=base64.b64encode((FIXTURES/'ambpower.mod').read_bytes()+secrets.token_bytes(16)).decode()
    shared_upload=context.request.post(BASE+'api.php?action=upload-music',data={'name':'unique.mod','data':shared},headers=headers);assert shared_upload.status==200
    shared_url=shared_upload.json()['url']
    library=context.request.get(BASE+'api.php?action=music-library').json();module=next(x for x in library if x['name']=='unique.mod')
    assert other.request.post(BASE+'api.php?action=delete-music',data={'id':module['id'],'format':'mod'},headers=otherheaders).status==404
    assert other.request.post(BASE+'api.php?action=upload-music',data={'name':'shared.mod','data':shared},headers=otherheaders).status==200
    assert context.request.post(BASE+'api.php?action=delete-music',data={'id':module['id'],'format':'mod'},headers=headers).status==200
    assert context.request.get(BASE+shared_url).status==200
    assert other.request.post(BASE+'api.php?action=delete-music',data={'id':module['id'],'format':'mod'},headers=otherheaders).status==200
    assert context.request.get(BASE+shared_url).status==404
    # Exercise the actual editor upload, save and visitor player, not just the API.
    page.goto(BASE+'#edit');page.locator('[data-editor-tab=music]').click()
    page.locator('#music-upload').set_input_files(str(FIXTURES/'test.mid'))
    expect(page.locator('[name="s.soundtrack"]')).to_have_value(files['test.mid'],timeout=10000)
    page.locator('#save-page').click();expect(page.locator('#draft-status')).to_have_text('Your page is live.')
    page.goto(BASE+'~'+handle);player=page.frame_locator('iframe[title="MIDI player"]')
    player.locator('#play').click();expect(player.locator('#status')).to_have_text('Playing.',timeout=20000)
    assert not errors,errors
    print('PASS: MIDI looping; SID tune switching; actual silent output at zero volume; signature rejection; shelf ownership and shared-file deletion; editor upload/save and homepage playback')
    browser.close()
