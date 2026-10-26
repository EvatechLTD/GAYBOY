"""Live public QA and one clearly labelled, cleaned-up owner-address test signup."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shlex,sys,uuid
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/fentwave-live-verification';OUT.mkdir(parents=True,exist_ok=True)
url='https://y2kcrisis.com'
tag=uuid.uuid4().hex[:12]
email='evatechusa+fentwave-check-'+tag+'@gmail.com'
name='Deployment check '+tag+' (not a real subscriber)'
checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    assert page.goto(url+'/#apps').status==200
    card=page.locator('.app-card').filter(has=page.get_by_role('heading',name='FENTWAVE',exact=True))
    link=card.get_by_role('link',name='VISIT ITS HOMEPAGE')
    link.wait_for();assert link.get_attribute('href')=='/fentwave/'
    assert page.get_by_role('heading',name='GAYBOY',exact=True).is_visible()
    page.screenshot(path=str(OUT/'apps.png'),full_page=True)
    link.click();page.wait_for_url('**/fentwave/')
    page.get_by_role('heading',name='FENTWAVE64').wait_for()
    assert page.locator('html').evaluate('(el)=>el.scrollWidth<=innerWidth')
    page.screenshot(path=str(OUT/'homepage.png'),full_page=True)
    checks+=['Live Apps card preserves GAYBOY and links to FENTWAVE','Published homepage loads over verified HTTPS']
    page.get_by_role('button',name='PUT ME ON THE WAITLIST').click()
    page.locator('#signup-name').fill(name);page.locator('#signup-email').fill(email);page.locator('[name=consent]').check()
    page.locator('#signup-submit').click();page.locator('#signup-success').wait_for(state='visible',timeout=30000)
    checks.append('Live labelled test signup succeeds without an account')
    page.get_by_role('link',name='CREATE & DECORATE MY PAGE').click()
    page.wait_for_url('**/#edit')
    page.get_by_role('button',name='ESTABLISH CONNECTION').wait_for()
    checks.append('Optional account/page-builder invitation reaches existing community signup flow')
    browser.close()
sys.path.insert(0,'G:/DEVELOPMENT/VIBECHOPPER/scripts')
from namehero_access import connect_sftp
c=connect_sftp()
try:
    # Inspect/remove only our unguessable fixture, never enumerate real contacts.
    code='''require "/home/centered/y2kcrisis.com/fentwave/waitlist-core.php";
    $email=EMAIL;$name=NAME;
    $h=hash_hmac('sha256',$email,substr(fw_keys(),32));
    $r=fw_query('SELECT id,payload,notification FROM contacts WHERE email_hmac=?',[$h])->fetchArray(SQLITE3_ASSOC);
    if(!$r || fw_decrypt($r['payload'])['name']!==$name)throw new RuntimeException('Fixture mismatch');
    $state=$r['notification'];fw_query('DELETE FROM contacts WHERE id=?',[$r['id']]);
    echo json_encode(['notification'=>$state,'test_contact_removed'=>fw_db()->changes()===1]);
    '''.replace('EMAIL',json.dumps(email)).replace('NAME',json.dumps(name))
    _,out,err=c.exec_command('Y2KCRISIS_DATA=/home/centered/y2kcrisis-private /opt/cpanel/ea-php83/root/usr/bin/php -r '+shlex.quote(code),timeout=25)
    raw=out.read().decode();assert out.channel.recv_exit_status()==0,'Fixture verification/cleanup failed'
    state=json.loads(raw);assert state['test_contact_removed'] and state['notification']=='accepted',state
    checks.append('Encrypted test record verified, owner notification accepted, fixture removed')
finally:c.close()
assert not errors,errors
report={'status':'PASS','checked_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'mail_limit':'Accepted by host MTA; inbox placement is not proven by this check.'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
