"""Verify the shipped ROM hash and isolated practice/normal browser machines."""
import hashlib
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright, expect

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:18986/'
ROOT = Path(__file__).resolve().parents[1]
expected_hash = hashlib.sha256((ROOT/'build/GAYBOY.gb').read_bytes()).hexdigest()
instrument = '''
const factory=window.SameBoyCore;
window.SameBoyCore=async(...args)=>{
 const m=await factory(...args);window.qaCore=m;window.qaMachines=[];
 const create=m._emulator_new_simple;
 m._emulator_new_simple=(...args)=>{const e=create(...args);qaMachines.push(e);return e;};
 return m;
};
'''
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page()
    if '--local-rom-only' in sys.argv:
        assert URL.startswith('http://127.0.0.1:'), 'Offline shelf stub is local-only'
        page.route('**/network-beats.js*', lambda r:r.fulfill(
            content_type='application/javascript',body='/* PHP shelf is verified on the live site. */'))
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
    page.route('**/emulator/sameboy.js*',lambda r:r.fulfill(
        response=(response:=r.fetch()),body=response.text()+instrument))
    page.goto(URL,wait_until='networkidle')
    hashes=page.evaluate('''async()=>{
      const current=await(await fetch('emulator/tutorial-rom.json')).json();
      const practice=await(await fetch('emulator/practice-rom.json')).json();
      const hash=async path=>Array.from(new Uint8Array(await crypto.subtle.digest(
        'SHA-256',await(await fetch(path)).arrayBuffer())),n=>n.toString(16).padStart(2,'0')).join('');
      return {current:current.sha256,normal:await hash(current.rom),
        download:await hash('downloads/GAYBOY.gb'),practice:practice.sha256,
        practiceFile:await hash(practice.rom),practiceHasEvents:!!practice.symbols.seqevents_lo};
    }''')
    assert hashes['current']==hashes['normal']==hashes['download']==expected_hash,hashes
    assert hashes['practice']==hashes['practiceFile'] and hashes['practiceHasEvents'],hashes
    page.locator('#demo-play').click()
    # wait_for_function uses page eval, which the live site's CSP disallows.
    # Poll through the browser protocol without relaxing production policy.
    for _ in range(100):
        if page.evaluate('window.qaMachines?.length===1'):
            break
        page.wait_for_timeout(200)
    assert page.evaluate('window.qaMachines?.length===1'),errors
    page.wait_for_timeout(3000)
    page.locator('#demo-pause').click()
    expect(page.locator('#demo-pause')).to_have_attribute('aria-pressed','true')
    page.evaluate('''()=>{
      window.qaRam=()=>{const m=qaCore,f=m._ext_ram_file_data_new(qaMachines[0]);
        m._emulator_write_ext_ram(qaMachines[0],f);
        const data=Array.from(m.HEAPU8.slice(m._get_file_data_ptr(f),m._get_file_data_ptr(f)+m._get_file_data_size(f)));
        m._file_data_delete(f);return JSON.stringify(data);};
      window.qaBeforeRam=qaRam();window.qaBeforeTicks=qaCore._emulator_get_ticks_f64(qaMachines[0]);
    }''')
    page.locator('#demo-tutorial-reopen').click()
    panel=page.locator('.demo-tutorial')
    expect(panel).to_have_attribute('data-stage','practice',timeout=45000)
    page.locator('[data-tour=close]').click()
    expect(panel).to_be_hidden(timeout=10000)
    assert page.evaluate('qaRam()===qaBeforeRam')
    assert page.evaluate('qaCore._emulator_get_ticks_f64(qaMachines[0])===qaBeforeTicks')
    assert not errors,errors
    browser.close()
    print(json.dumps({'url':URL,**hashes,'practice_first_lesson':'passed',
                      'normal_machine_and_sram_preserved':True,'browser_errors':errors}))
