"""Share and audition an actual ROM sequence on the isolated Y2KCRISIS server."""
from pathlib import Path
import secrets
import sys
from playwright.sync_api import sync_playwright,expect
sys.stdout.reconfigure(encoding='utf-8')
BASE='http://127.0.0.1:18981/'
INSTRUMENT='''
const factory=window.SameBoyCore;
window.SameBoyCore=async(...args)=>{
 const m=await factory(...args);window.qaCore=m;
 const create=m._emulator_new_simple;
 m._emulator_new_simple=(...args)=>{const e=create(...args);window.qaInstance=e;return e;};return m;
};
'''
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome')
    context=browser.new_context(viewport={'width':390,'height':844})
    token=context.request.get(BASE+'api.php').json()['csrf']
    r=context.request.post(BASE+'api.php?action=register',data={'handle':'beats_'+secrets.token_hex(3),'password':secrets.token_urlsafe(20)},headers={'X-CSRF-Token':token});assert r.status==200,r.text()
    beatTitle='Local QA '+secrets.token_hex(4)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/emulator/sameboy.js*',lambda r:r.fulfill(response=(response:=r.fetch()),body=response.text()+INSTRUMENT))
    page.goto(BASE+'apps/gayboy/player.html',wait_until='networkidle');page.locator('#demo-play').click();page.wait_for_timeout(3200)
    page.keyboard.down('Shift');page.wait_for_timeout(1600);page.keyboard.up('Shift');page.wait_for_timeout(500)
    metadata=page.evaluate("async()=>await(await fetch('emulator/tutorial-rom.json')).json()")
    page.evaluate('(m)=>{window.qaMap=m;window.qaRead=n=>qaCore._emulator_observe_mem(qaInstance,m.symbols[n]);}',metadata)
    assert page.evaluate('qaRead("page")')==8
    page.keyboard.press('z',delay=200);page.wait_for_timeout(400);page.keyboard.down('Space');page.wait_for_timeout(200);page.keyboard.press('x',delay=200);page.keyboard.up('Space');page.wait_for_function('qaRead("seqplaying")===1')
    page.evaluate('window.qaOriginal=qaInstance')
    page.locator('#demo-share').click();expect(page.locator('.network-beat-dialog')).to_be_visible();page.locator('.network-beat-dialog [name=title]').fill(beatTitle)
    with page.expect_response(lambda r:'action=share-beat' in r.url) as response:page.locator('.network-beat-dialog [type=submit]').click()
    r=response.value;assert r.status==200,r.text();identifier=r.json()['id']
    expect(page.locator('#beat-tracks')).to_contain_text(beatTitle)
    page.locator('#beat-tracks button').filter(has_text=beatTitle).click();expect(page.locator('#return-my-beat')).to_be_visible(timeout=20000)
    assert page.evaluate('qaInstance!==qaOriginal');assert page.evaluate('qaRead("seqplaying")')==1
    frozen=page.evaluate('qaCore._emulator_get_ticks_f64(qaOriginal)');page.locator('#return-my-beat').click();page.wait_for_function('(frozen)=>qaCore._emulator_get_ticks_f64(qaOriginal)>frozen',arg=frozen);assert page.evaluate('qaCore._emulator_observe_mem(qaOriginal,qaMap.symbols.seqplaying)')==1
    other=browser.new_context(viewport={'width':390,'height':844});listener=other.new_page();listener.goto(BASE+'apps/gayboy/player.html?beat='+identifier,wait_until='networkidle');expect(listener.locator('#demo-play')).to_have_text('PLAY THIS SHARED BEAT');listener.locator('#demo-play').click();expect(listener.locator('#return-my-beat')).to_be_visible(timeout=20000)
    assert not errors,errors
    print('PASS: real sequencer input; authenticated beat capture/share; shared-beat audition in a separate emulator instance; original music restored; anonymous share-link playback')
    browser.close()
