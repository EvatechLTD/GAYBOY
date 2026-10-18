from pathlib import Path
import json
from playwright.sync_api import sync_playwright
out=Path('build/808-shell');out.mkdir(exist_ok=True)
url='https://buttholechopper.com/gayboy/'
with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome',headless=True)
 context=b.new_context(viewport={'width':390,'height':694},device_scale_factor=2,is_mobile=True,has_touch=True)
 page=context.new_page();r=page.goto(url,wait_until='domcontentloaded',timeout=45000)
 assert r and r.status==200,(r.status if r else None)
 page.locator('#live-demo').wait_for();page.evaluate('document.fonts.ready')
 # Pause decorative website motion for a clear, faithful mobile capture.
 if page.locator('#motion').count():page.locator('#motion').click()
 for target,name in [('#live-demo','mobile-play.png'),('#download','mobile-download.png')]:
  page.locator(target).scroll_into_view_if_needed()
  page.evaluate('(selector)=>{const y=document.querySelector(selector).getBoundingClientRect().top+window.scrollY-12;window.scrollTo({top:y,behavior:"instant"});}',target)
  page.screenshot(path=str(out/name))
 report={'url':page.url,'status':r.status,'title':page.title(),'viewport':[390,694],
         'download_href':page.locator('.download-button').get_attribute('href'),'emulator_button':page.locator('#demo-play').inner_text()}
 print(json.dumps(report,indent=2));(out/'mobile-site.json').write_text(json.dumps(report,indent=2));b.close()
