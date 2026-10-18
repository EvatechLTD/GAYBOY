"""Exercise the GAYBOY template, design portability, drafts and provider parsing."""
from pathlib import Path
import json
import secrets
import sys
from playwright.sync_api import sync_playwright,expect
sys.stdout.reconfigure(encoding='utf-8')
BASE='http://127.0.0.1:18981/'
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome');context=browser.new_context(viewport={'width':1440,'height':1000});csrf=context.request.get(BASE+'api.php').json()['csrf']
    handle='build_'+secrets.token_hex(3);r=context.request.post(BASE+'api.php?action=register',data={'handle':handle,'password':secrets.token_urlsafe(20)},headers={'X-CSRF-Token':csrf});assert r.status==200,r.text()
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(BASE+'#edit');page.wait_for_selector('#gayboy-template');page.once('dialog',lambda d:d.accept());page.locator('#gayboy-template').click();expect(page.locator('#builder-preview .hp-app')).to_have_count(1);expect(page.locator('#builder-preview .hp-gallery img')).to_have_count(4);expect(page.locator('#builder-preview .hp-download')).to_have_count(1)
    page.locator('[data-editor-tab=blocks]').click();page.locator('[data-select-block="0"]').click();page.locator('[name="b.type"]').select_option('image');expect(page.locator('#builder-preview .hp-photo')).to_have_count(1);page.locator('[name="b.type"]').select_option('app');expect(page.locator('#builder-preview .hp-app')).to_have_count(1)
    page.locator('[data-editor-tab=profile]').click();page.locator('[name="s.title"]').fill('MY GAYBOY-LEVEL HOMEPAGE');page.locator('[name="s.welcome"]').fill('HELLO FROM MY OWN CORNER');page.locator('[name="s.ticker"]').fill('I CAN CHANGE ALL OF THIS');page.locator('#save-page').click();expect(page.locator('#draft-status')).to_have_text('Your page is live.')
    page.locator('[data-editor-tab=pages]').click()
    with page.expect_download() as d:page.locator('#export-page').click()
    exported=Path(d.value.path()).read_bytes();design=json.loads(exported);assert len(design['blocks'])==6 and design['settings']['title']=='MY GAYBOY-LEVEL HOMEPAGE'
    page.locator('#import-page').set_input_files({'name':'design.json','mimeType':'application/json','buffer':exported});page.locator('#save-page').click();expect(page.locator('#draft-status')).to_have_text('Your page is live.')
    page.locator('[data-editor-tab=profile]').click();page.locator('[name="s.quote"]').fill('An unfinished thought');page.wait_for_timeout(200);page.reload();page.wait_for_selector('#builder-form');page.locator('[data-editor-tab=profile]').click();expect(page.locator('[name="s.quote"]')).to_have_value('An unfinished thought')
    page.locator('[data-editor-tab=history]').click();page.wait_for_selector('[data-restore]');page.once('dialog',lambda d:d.accept());page.locator('[data-restore]').first.click();page.wait_for_timeout(500);assert not page.locator('#view').inner_text().startswith('CONNECTION INTERRUPTED')
    page.goto(BASE+'~'+handle);page.wait_for_selector('.homepage');assert page.locator('.hp-app').count()==1;assert page.locator('.hp-gallery img').count()==4
    media=page.evaluate("""async()=>{const {mediaInfo}=await import('/media.js');const urls=['https://youtu.be/M7lc1UVf-VE?t=1m2s','https://www.youtube.com/playlist?list=PL1234567890123456','https://youtube.com/shorts/M7lc1UVf-VE','https://soundcloud.com/forss/flickermood','https://open.spotify.com/track/0Lr4kGOYn9l83EjuK6cZFQ','https://vimeo.com/76979871','https://www.mixcloud.com/user/show/','https://bandcamp.com/EmbeddedPlayer/album=123456/size=large/','https://twitch.tv/twitchdev','https://example.com/song.mp3','https://example.com/video.mp4'];return urls.map(v=>mediaInfo(v));}""")
    assert all(m.get('src') and not m.get('error') for m in media),media
    assert 'start=62' in media[0]['src'];assert 'videoseries' in media[1]['src'];assert 'parent=127.0.0.1' in media[8]['src']
    malicious=page.evaluate("""async()=>{const {messageHTML}=await import('/emoji.js');return messageHTML('<img src=x onerror=alert(1)> uWu :D <3 uwux');}""")
    assert '&lt;img' in malicious and 'chat-emoji' in malicious and 'uwux' in malicious
    r=context.request.post(BASE+'api.php?action=save-page',data={'bio':'Privacy check','settings':{'guestbookMode':'off','showGuestbook':False,'showBathroom':False},'blocks':[{'type':'guestbook'},{'type':'bathroom'}],'bathroom':False},headers={'X-CSRF-Token':csrf});assert r.status==200,r.text()
    page.goto(BASE+'~'+handle);page.wait_for_selector('.homepage');assert page.locator('.hp-guestbook').count()==0 and page.locator('.hp-bathroom').count()==0
    assert not errors,errors
    print('PASS: full GAYBOY template is editable and saveable; gallery/download/app parity; JSON export/import; unsaved draft recovery; version restore; eleven provider URL formats; YouTube time offsets; Twitch domain binding; emoji HTML escaping')
    browser.close()
