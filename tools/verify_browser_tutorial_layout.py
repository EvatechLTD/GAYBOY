"""Check tutorial placement, 44px molded D-pad tilt, replay and demo interruption.

Run with the VIBECHOPPER virtualenv; optionally pass the served website URL.
"""
import sys,json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright,expect
URL=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:18980/'
OUT=__import__('pathlib').Path(__file__).resolve().parents[1]/'build'
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 for w,h in [(1440,1000),(768,1024),(390,844),(320,667),(844,390)]:
  page=b.new_page(viewport={'width':w,'height':h},has_touch=w<600)
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  page.goto(URL)
  page.locator('#demo-tutorial').click()
  panel=page.locator('.demo-tutorial')
  expect(panel).to_have_attribute('data-stage','demo',timeout=30000)
  if w==390:
   page.locator('#demo-pause').click()
   expect(panel).to_have_attribute('data-stage','paused')
   page.locator('.demo-resume-overlay').click()
  expect(panel).to_have_attribute('data-stage','practice',timeout=30000)
  page.wait_for_timeout(200)
  assert panel.bounding_box()['y']>=0
  assert panel.bounding_box()['y']+panel.bounding_box()['height']<=page.locator('.handheld').bounding_box()['y']
  assert not page.locator('#live-demo').evaluate('e=>e.scrollWidth>e.clientWidth'),(w,'overflow')
  if h>=667:
   assert page.locator('.system-buttons').bounding_box()['y']+page.locator('.system-buttons').bounding_box()['height']<=h,(w,'controls out of view',page.locator('.system-buttons').bounding_box())
  right=page.locator('[data-pad=right]')
  assert right.bounding_box()['width']>=44
  before=page.locator('.dpad').evaluate('e=>getComputedStyle(e).transform')
  right.hover();page.mouse.down();page.wait_for_timeout(120)
  assert page.locator('.dpad').evaluate('e=>getComputedStyle(e).transform')!=before
  assert right.evaluate('e=>getComputedStyle(e).outlineStyle')=='none'
  page.screenshot(path=str(OUT/f'tutorial-layout-{w}.png'))
  page.mouse.up()
  page.locator('[data-tour=close]').click()
  expect(panel).to_be_hidden()
  page.locator('#demo-tutorial-reopen').click()
  expect(panel).to_have_attribute('data-stage','practice',timeout=30000)
  page.locator('[data-tour=close]').click()
  assert not errors,errors
  print('layout, tilt, exit/replay passed',w,h,flush=True)
  page.close()
 b.close()
