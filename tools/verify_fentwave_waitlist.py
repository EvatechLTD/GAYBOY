"""Isolated API/security/browser checks; never submits contacts to production."""
from pathlib import Path
import contextlib,http.cookiejar,json,os,socket,sqlite3,subprocess,tempfile,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1]
PHP=Path('G:/DEVELOPMENT/GAYBOY/DATA/TEST_RESULTS/legacy-build/php/php.exe')
PHP_ARGS=[str(PHP),'-n','-d','extension_dir='+str(PHP.parent/'ext'),'-d','extension=sqlite3','-d','extension=mbstring','-d','extension=openssl']
OUT=ROOT/'build/fentwave-verification';OUT.mkdir(parents=True,exist_ok=True)
def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
@contextlib.contextmanager
def server(home,**extra):
    env=os.environ.copy();env.update(Y2KCRISIS_DATA=str(home),FENTWAVE_TEST_MODE='1',FENTWAVE_MAIL_SPOOL=str(home/'mail.jsonl'));env.update(extra)
    url='http://127.0.0.1:'+str(port())
    with (OUT/'php.log').open('ab') as log:
        p=subprocess.Popen(PHP_ARGS+['-S',url.removeprefix('http://'),'-t',str(ROOT/'network'),str(ROOT/'network/router.php')],cwd=ROOT,env=env,stdout=log,stderr=log)
        try:
            for _ in range(60):
                try:urllib.request.urlopen(url+'/fentwave/',timeout=.5);break
                except Exception:
                    if p.poll() is not None:raise RuntimeError('PHP server failed; inspect local PHP log')
                    time.sleep(.1)
            else:raise RuntimeError('PHP server did not start')
            yield url,env
        finally:p.terminate();p.wait(timeout=10)
def client(url):
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(payload=None,origin=None,path='/fentwave/waitlist.php',method=None):
        headers={'Origin':origin or url,'Content-Type':'application/json'}
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(url+path,data=data,headers=headers,method=method)
        try:
            with opener.open(req,timeout=10) as r:return r.status,r.read(),dict(r.headers)
        except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
    return request
@contextlib.contextmanager
def database(home):
    db=sqlite3.connect(home/'fentwave-waitlist/contacts.sqlite')
    try:
        with db:yield db
    finally:db.close()
def count(home):
    with database(home) as db:return db.execute('SELECT count(*) FROM contacts').fetchone()[0]
def messages(home):return [json.loads(line) for line in (home/'mail.jsonl').read_text().splitlines()] if (home/'mail.jsonl').exists() else []
checks=[]
with tempfile.TemporaryDirectory(prefix='fentwave-api-') as tmp:
    home=Path(tmp)
    with server(home) as (url,env):
        call=client(url);status,raw,headers=call();assert status==200
        csrf=json.loads(raw)['csrf'];assert set(json.loads(raw))=={'csrf'}
        assert 'HttpOnly' in headers.get('Set-Cookie','') and 'SameSite=Strict' in headers.get('Set-Cookie','')
        good={'csrf':csrf,'email':'Waitlist.Test@example.com','name':'Fixture <not HTML>','consent':True,'website':''}
        for data,expected in [({**good,'csrf':'wrong'},403),({**good,'email':'invalid'},422),({**good,'consent':False},422),({**good,'name':'bad\r\nBcc: victim@example.com'},422),({**good,'email':'test@example.com\r\nBcc: x@example.com'},422),({**good,'name':'x'*5000},413)]:
            assert call(data)[0]==expected,(data,expected)
        assert call(good,origin='https://attacker.example')[0]==403
        assert call(method='PUT')[0]==405
        for path in ['/fentwave/notify.php','/fentwave/waitlist-core.php','/fentwave/.htaccess']:assert call(path=path)[0]==404,path
        assert call({**good,'website':'bot.example'})[0]==200 and count(home)==0 and not messages(home)
        assert call(good)[0]==200 and count(home)==1 and len(messages(home))==1
        assert call({**good,'email':'waitlist.test@example.com'})[0]==200 and count(home)==1 and len(messages(home))==1
        msg=messages(home)[0];assert msg['to']=='evatechusa@gmail.com' and 'waitlist.test@example.com' in msg['body'] and 'Fixture <not HTML>' in msg['body']
        with database(home) as db:
            record=db.execute('SELECT payload,email_hmac,notification,consent_version FROM contacts').fetchone()
        assert record[2:] == ('accepted','fentwave-updates-v1')
        assert 'waitlist.test' not in ''.join(record) and 'Fixture' not in ''.join(record)
        for _ in range(6):assert call(good)[0]==200
        assert call(good)[0]==429
        checks+=['CSRF/origin/method checks','Validation and header injection rejection','No public contact listing or CLI access','Honeypot does not store or mail','Encrypted authenticated storage and HMAC-only dedupe','Case-insensitive duplicate generates no extra owner email','Owner notification decrypts correct contact','Consent and private session cookies','IP rate limit']
    with server(home,FENTWAVE_TEST_MAIL_FAIL='1') as (url,env):
        call=client(url);csrf=json.loads(call()[1])['csrf']
        # Separate rate-limit bucket to exercise the deferred notification path.
        with database(home) as db:db.execute('DELETE FROM limits')
        assert call({'csrf':csrf,'email':'queue@example.com','name':'Queue test','consent':True})[0]==200
        assert count(home)==2 and len(messages(home))==1
        with database(home) as db:assert db.execute("SELECT count(*) FROM contacts WHERE notification='pending'").fetchone()[0]==1
    env.pop('FENTWAVE_TEST_MAIL_FAIL',None)
    p=subprocess.run(PHP_ARGS+[str(ROOT/'network/fentwave/notify.php'),'--process'],env=env,capture_output=True,text=True,check=True)
    assert len(messages(home))==2
    subprocess.run(PHP_ARGS+[str(ROOT/'network/fentwave/notify.php'),'--process'],env=env,capture_output=True,text=True,check=True)
    assert len(messages(home))==2
    checks.append('Transient mail failure retains encrypted signup and retry sends once')
    with server(home,FENTWAVE_TEST_MODE='0') as (url,env):assert client(url)()[0]==426
    checks.append('Production rejects plain HTTP')
with tempfile.TemporaryDirectory(prefix='fentwave-browser-') as tmp:
    with server(Path(tmp)) as (url,env):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='chrome',headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            response=page.goto(url+'/fentwave/');assert response.status==200
            page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
            page.get_by_role('button',name='MOD',exact=True).click();assert page.locator('#screen').get_attribute('src')=='images/mod.png'
            page.get_by_role('button',name='Pink homepage').click();assert page.locator('.mini-homepage').get_attribute('data-color')=='pink'
            page.get_by_role('button',name='PUT ME ON THE WAITLIST').click();assert page.locator('#waitlist').is_visible()
            page.keyboard.press('Escape');assert not page.locator('#waitlist').is_visible()
            for width in [390,320]:
                page.set_viewport_size({'width':width,'height':844});page.goto(url+'/fentwave/')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
                page.screenshot(path=str(OUT/f'mobile-{width}.png'),full_page=True)
                page.get_by_role('button',name='GET ON THE LIST').click();page.locator('#signup-email').fill('browser.fixture@example.com');page.locator('#signup-name').fill('Browser fixture');page.locator('[name=consent]').check()
                page.screenshot(path=str(OUT/f'modal-{width}.png'))
                if width==320:
                    page.locator('#signup-submit').click();page.locator('#signup-success').wait_for(state='visible')
                    assert count(Path(tmp))==1 and len(messages(Path(tmp)))==1
                    assert page.get_by_role('link',name='CREATE & DECORATE MY PAGE').get_attribute('href')=='/#edit'
                    page.screenshot(path=str(OUT/'success.png'))
                else:page.keyboard.press('Escape')
            assert not errors,errors
            browser.close()
        checks+=['Desktop/390px/320px browser layout without overflow','Screenshot and community-color interactions','Accessible modal close and keyboard escape','Real browser signup through PHP to encrypted record and owner email spool','Optional account/page-builder invitation after signup']
report={'status':'PASS','checks':checks,'limits':'Isolated local contacts and mail spool only; real SMTP delivery is a separate deployment check.'}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
