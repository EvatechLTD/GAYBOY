"""Exercise demonstrations and open-ended lesson goals in the actual WASM ROM.

Run with the VIBECHOPPER virtualenv (Playwright + Chrome). No ROM state is
written to complete tasks: learner actions are keyboard/pointer joypad events.
"""
from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright, expect

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:18980/'
ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8')
INSTRUMENT = """
const factory=window.SameBoyCore;
window.SameBoyCore=async(...args)=>{
 const m=await factory(...args);window.qaCore=m;window.qaMachines=[];
 const create=m._emulator_new_simple;
 m._emulator_new_simple=(...args)=>{const e=create(...args);qaMachines.push(e);window.qaInstance=e;return e;};
 return m;
};
"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width':390,'height':844}, has_touch=True)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.route('**/emulator/sameboy.js*', lambda route: route.fulfill(
        response=(response := route.fetch()), body=response.text()+INSTRUMENT))
    page.goto(URL, wait_until='networkidle')
    page.locator('#demo-tutorial').click()
    panel = page.locator('.demo-tutorial')
    next_button = page.locator('[data-tour=next]')
    expect(panel).to_have_attribute('data-stage','demo',timeout=30000)
    expect(next_button).to_be_disabled()
    expect(page.locator('.tutorial-score')).to_have_text('0 / 1200 pts')
    expect(panel).to_have_attribute('data-stage','practice',timeout=30000)
    metadata = page.evaluate("async()=>await(await fetch('emulator/tutorial-rom.json')).json()")
    page.evaluate('(m)=>window.qaMap=m',metadata)
    page.evaluate("""()=>{
      window.qaRead=n=>qaCore._emulator_observe_mem(qaInstance,qaMap.symbols[n]);
      window.qaWord=a=>qaCore._emulator_observe_mem(qaInstance,a)|(qaCore._emulator_observe_mem(qaInstance,a+1)<<8);
      window.qaTotal=()=>Array.from({length:7},(_,i)=>qaWord(qaMap.symbols.seqeventcounts+i*2)).reduce((a,b)=>a+b,0);
      window.qaNote=(track,i)=>{
        const n=qaWord(qaMap.symbols.seqeventoffsets+track*2)+i;
        const a=n<256?qaMap.symbols.seqevents_lo+n*4:qaMap.symbols.seqevents_hi+(n-256)*4;
        return Array.from({length:4},(_,j)=>qaCore._emulator_observe_mem(qaInstance,a+j));
      };
      window.qaNormalTicks=qaCore._emulator_get_ticks_f64(qaMachines[0]);
      window.qaRam=e=>{const f=qaCore._ext_ram_file_data_new(e);qaCore._emulator_write_ext_ram(e,f);
        const bytes=Array.from(qaCore.HEAPU8.slice(qaCore._get_file_data_ptr(f),qaCore._get_file_data_ptr(f)+qaCore._get_file_data_size(f)));
        qaCore._file_data_delete(f);return bytes;};
      window.qaNormalRam=qaRam(qaMachines[0]);
    }""")

    masks={'ArrowRight':1,'ArrowLeft':2,'ArrowUp':4,'ArrowDown':8,'x':16,'KeyX':16,'z':32,'KeyZ':32,'Space':64,'Shift':128}
    def edge(code,down):
        page.keyboard.down(code) if down else page.keyboard.up(code)
        try:
            page.wait_for_function('a=>!!(qaRead("lastpad")&a.bit)===a.down',arg={'bit':masks[code],'down':down},timeout=6000)
        except Exception:
            print(page.evaluate('()=>({focus:document.activeElement.outerHTML,stage:document.querySelector(".demo-tutorial").dataset.stage,pad:qaRead("lastpad"),track:qaRead("seqtrack"),status:document.querySelector(".demo-status").textContent})'),flush=True)
            print(errors,flush=True)
            raise

    def key(code, times=1):
        for _ in range(times):
            edge(code,True);edge(code,False)
            page.wait_for_timeout(80)

    def chord(hold,code,times=1):
        edge(hold,True);key(code,times);edge(hold,False)
        page.wait_for_timeout(180)

    def passed(n):
        expect(panel).to_have_attribute('data-stage','passed',timeout=8000)
        expect(panel).to_have_attribute('data-lesson',str(n))
        expect(next_button).to_be_enabled()
        print(f'Lesson {n}: actual ROM goal passed',flush=True)

    def advance(n):
        next_button.click()
        expect(panel).to_have_attribute('data-lesson',str(n))
        expect(next_button).to_be_disabled()
        try:
            expect(panel).to_have_attribute('data-stage','practice',timeout=60000)
        except Exception:
            print('Tutorial errors:',errors,flush=True)
            print(page.evaluate('()=>({track:qaRead("seqtrack"),head:qaRead("seqhead"),pitch:qaRead("seqpitch"),total:qaTotal()})'),flush=True)
            raise
        expect(panel).to_be_focused()

    def cell(track,step,pitch):
        for _ in range(256):
            current=page.evaluate('(c)=>qaCore._emulator_observe_mem(qaInstance,qaMap.symbols.seqcursor+c)',track)
            if current==step: break
            key('ArrowRight')
        for _ in range(128):
            current=page.evaluate('(c)=>qaCore._emulator_observe_mem(qaInstance,qaMap.symbols.seqpitch+c)',track)
            if current==pitch: break
            key('ArrowUp' if current<pitch else 'ArrowDown')
        head=page.evaluate('qaRead("seqhead")')
        if head: key('ArrowRight' if head==6 else 'ArrowUp' if head==5 else 'ArrowDown')

    # A real C2 note is ready; the first lesson only teaches starting playback.
    assert page.evaluate('qaTotal()') == 1
    assert page.evaluate('qaNote(0,0).slice(0,2)') == [0,37]
    assert page.evaluate('qaRead("seqplaying")') == 0
    expect(next_button).to_be_disabled()
    expect(page.locator('[data-pad=select]')).to_have_class(__import__('re').compile('tutorial-target'))
    expect(page.locator('[data-pad=A]')).to_have_class(__import__('re').compile('tutorial-target'))
    chord('Space','x');passed(1)
    # Passing unlocks Next without locking the instrument or awarding points twice.
    cell(0,3,41);key('z')
    assert page.evaluate('qaTotal()') == 2
    expect(page.locator('.tutorial-score')).to_have_text('100 / 1200 pts')
    key('z')
    assert page.evaluate('qaTotal()') == 1
    page.evaluate('()=>{window.qaPlaybackStops=[];window.qaPlaybackWatch=setInterval(()=>{if(!qaRead("seqplaying"))qaPlaybackStops.push(document.querySelector(".demo-tutorial").dataset.lesson)},20)}')
    advance(2)
    assert page.evaluate('qaTotal()') == 1
    assert page.evaluate('qaRead("seqplaying")') == 1, 'Next lesson stopped the groove'
    cell(0,2,39)
    expect(next_button).to_be_disabled()
    key('z');passed(2)
    custom_note=page.evaluate('qaNote(0,1).slice(0,2)')
    assert custom_note == [2,40], ('Custom pitch/time was not accepted',custom_note)
    advance(3)
    assert page.evaluate('qaTotal()') == 2, 'Demonstration overwrote the learner melody'
    # Three new notes cannot pass the four-note lesson. A reset reduces score.
    for step in [5,8,11]: cell(0,step,40);key('z')
    expect(next_button).to_be_disabled()
    page.locator('[data-tour=retry]').click()
    assert page.evaluate('qaTotal()') == 2
    for step,pitch in [(4,41),(7,42),(10,43),(13,44)]: cell(0,step,pitch);key('z')
    passed(3)
    advance(4)
    assert page.evaluate('qaTotal()') == 6
    page.locator('[data-tour=replay]').click()
    expect(panel).to_have_attribute('data-stage','practice',timeout=60000)
    assert page.evaluate('qaTotal()') == 6
    expect(panel).to_be_focused()
    # Switch TWO instruments rather than copying the demonstrated P2 part.
    chord('Space','ArrowLeft',2)
    track=page.evaluate('qaRead("seqtrack")')
    for _ in range(7):
        if track==2: break
        chord('Space','ArrowLeft')
        track=page.evaluate('qaRead("seqtrack")')
    assert track==2, ('Could not select a different instrument',track)
    cell(track,3,62);key('z')
    expect(next_button).to_be_disabled()
    cell(track,6,64);key('z')
    expect(next_button).to_be_disabled()
    cell(track,9,65);key('z')
    expect(next_button).to_be_disabled()
    cell(track,12,67);key('z');passed(4)
    advance(5)
    assert page.evaluate('qaTotal()') == 10
    cell(track,6,64);chord('KeyZ','ArrowRight');passed(5)
    advance(6)
    cell(track,6,64);chord('KeyX','ArrowDown');passed(6)
    advance(7)
    cell(track,3,62);key('z');passed(7)
    advance(8)
    page.keyboard.down('Shift');page.wait_for_timeout(150)
    for _ in range(24):
        if page.evaluate('qaRead("navchoice")')==18: break
        key('ArrowDown')
    page.keyboard.up('Shift');passed(8)
    advance(9)
    key('ArrowDown');key('ArrowRight');key('x');passed(9)
    advance(10)
    key('ArrowDown',2);key('ArrowRight',2);key('x');passed(10)
    advance(11)
    key('ArrowDown',3);key('ArrowRight');key('x');key('ArrowDown',2)
    expect(next_button).to_be_disabled()  # Must finish edit mode.
    key('x');passed(11)
    advance(12)
    key('ArrowDown',4);key('ArrowRight',2);key('x');key('ArrowDown',2);key('x');passed(12)
    expect(page.locator('.tutorial-score')).to_have_text('1175 / 1200 pts')
    assert page.evaluate('qaPlaybackStops') == [], 'A lesson transition stopped playback'
    page.evaluate('()=>clearInterval(qaPlaybackWatch)')
    next_button.click()
    expect(panel).to_have_attribute('data-stage','finished')
    expect(page.locator('.tutorial-description')).to_contain_text('1175/1200')
    assert page.evaluate('qaCore._emulator_get_ticks_f64(qaMachines[0])===qaNormalTicks')
    assert page.evaluate('JSON.stringify(qaRam(qaMachines[0]))===JSON.stringify(qaNormalRam)')
    page.screenshot(path=str(ROOT/'build/tutorial-complete-mobile.png'))
    next_button.click()
    expect(panel).to_be_hidden()
    assert page.evaluate('JSON.stringify(qaRam(qaMachines[0]))===JSON.stringify(qaNormalRam)')
    page.wait_for_function('qaCore._emulator_get_ticks_f64(qaMachines[0])>qaNormalTicks',timeout=6000)
    assert not errors,errors
    print(json.dumps({'lessons':12,'score':1175,'pattern_freedom':'different notes, instrument, lengths, mixer channels and values accepted',
      'gating':'wrong/partial actions and unfinished edits rejected','reset':'teacher changes cleared, user pattern preserved',
      'session_isolation':'original emulator and SRAM preserved','browser_errors':errors}),flush=True)
    browser.close()
