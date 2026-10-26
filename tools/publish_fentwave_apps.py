"""Add one FENTWAVE card to the existing Apps route; preserve other live changes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
sys.path.insert(0,'G:/DEVELOPMENT/VIBECHOPPER/scripts')
from namehero_access import connect_sftp
ROOT=Path(__file__).resolve().parents[1]
REMOTE='/home/centered/y2kcrisis.com'
CARD='<article class="app-card"><img src="/fentwave/images/main.png" alt="FENTWAVE SID patch editor on the Commodore 64" loading="lazy"><div><h2>FENTWAVE</h2><p>A SID music workstation for the Commodore 64, with a custom MIDI cartridge in development.</p><div class="actions"><a href="/fentwave/">VISIT ITS HOMEPAGE ↗</a></div><p class="muted">Follow the build and join the free development and launch waitlist. No payment or account required.</p></div></article>'
def add_card(source):
    start=source.index("else if(kind==='apps')")
    end=source.index('\n        else home();',start)
    block=source[start:end]
    if 'href="/fentwave/"' in block:return source
    point=block.rindex('</article>')+len('</article>')
    return source[:start]+block[:point]+CARD+block[point:]+source[end:]
def main():
    target=ROOT/'network/app.js';target.write_text(add_card(target.read_text(encoding='utf-8')),encoding='utf-8')
    subprocess.run(['node','--check',str(target)],check=True)
    c=connect_sftp();s=c.open_sftp()
    def read(path):
        with s.open(path,'rb') as f:return f.read()
    try:
        assert read(REMOTE+'/.y2kcrisis-owner')==b'y2kcrisis-network-v1\n'
        before=read(REMOTE+'/app.js');after=add_card(before.decode()).encode()
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup=ROOT/'build/fentwave-apps-publish'/stamp;backup.mkdir(parents=True)
        (backup/'app.js.before').write_bytes(before);(backup/'app.js').write_bytes(after)
        subprocess.run(['node','--check',str(backup/'app.js')],check=True)
        assert read(REMOTE+'/app.js')==before,'Live app changed concurrently'
        if after!=before:
            temporary=REMOTE+'/app.js.fentwave-apps-upload'
            with s.open(temporary,'wb') as f:f.write(after)
            s.chmod(temporary,0o644);assert read(temporary)==after;s.posix_rename(temporary,REMOTE+'/app.js')
        assert read(REMOTE+'/app.js')==after
        report={'status':'published','apps_url':'https://y2kcrisis.com/#apps','homepage':'https://y2kcrisis.com/fentwave/','app_js_sha256':hashlib.sha256(after).hexdigest(),'utc':datetime.now(timezone.utc).isoformat()}
        (backup/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:s.close();c.close()
if __name__=='__main__':main()
