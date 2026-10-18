"""User completes cPanel's normal browser verification; retain session encrypted."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'VIBECHOPPER/scripts'))
from namehero_access import STATE, protect
from playwright.sync_api import sync_playwright

subprocess.Popen([r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    '--user-data-dir='+str(STATE/'cpanel-browser-profile'),
    '--remote-debugging-address=127.0.0.1','--remote-debugging-port=9227',
    '--no-first-run','--no-default-browser-check','https://node613.namehero.net:2083/'])
with sync_playwright() as p:
    for attempt in range(20):
        try:
            browser=p.chromium.connect_over_cdp('http://127.0.0.1:9227');break
        except Exception:
            if attempt==19:raise
            time.sleep(1)
    context=browser.contexts[0]
    print('cPanel window ready. Waiting for normal user sign-in.',flush=True)
    for attempt in range(120):
        for page in context.pages:
            match=re.match(r'https://node613\.namehero\.net:2083(/cpsess\d+)(?:/|$)',page.url)
            if not match:continue
            try:
                result=page.evaluate('async path => (await fetch(path,{credentials:"same-origin",signal:AbortSignal.timeout(10000)})).json()',match.group(1)+'/execute/DomainInfo/list_domains')
                if result.get('result',result).get('status')!=1:continue
            except Exception:continue
            (STATE/'namehero-cpanel-browser-session.dpapi').write_bytes(protect(json.dumps({'base':'https://node613.namehero.net:2083'+match.group(1),'storage':context.storage_state()}).encode()))
            print('Authenticated session verified and encrypted.',flush=True)
            sys.exit(0)
        time.sleep(2)
    print('Sign-in is still needed. Rerun when ready.')
