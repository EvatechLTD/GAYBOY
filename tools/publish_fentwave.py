"""Targeted FENTWAVE publication to the existing NameHero site; preserves other apps."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,shlex,stat,sys,urllib.request,urllib.error
sys.path.insert(0,'G:/DEVELOPMENT/VIBECHOPPER/scripts')
from namehero_access import connect_sftp
ROOT=Path(__file__).resolve().parents[1]
REMOTE='/home/centered/y2kcrisis.com'
PRIVATE='/home/centered/y2kcrisis-private'
PHP='/opt/cpanel/ea-php83/root/usr/bin/php'
def digest(data):return hashlib.sha256(data).hexdigest()
def verify_public(sources,report):
    with urllib.request.urlopen(report['url'],timeout=30) as response:
        html=response.read();assert response.status==200 and digest(html)==digest(sources['fentwave/index.html'])
        report['tls']='Verified HTTPS'
    with urllib.request.urlopen(report['url']+'waitlist.php',timeout=30) as response:
        data=json.load(response);assert set(data)=={'csrf'} and len(data['csrf'])==64
        attributes={p.strip().lower() for p in response.headers.get('Set-Cookie','').split(';')[1:]}
        assert {'secure','httponly','samesite=strict'}<=attributes,'Required secure cookie attributes missing'
    for name in ['notify.php','waitlist-core.php']:
        try:urllib.request.urlopen(report['url']+name,timeout=20);raise RuntimeError('Private worker was publicly accessible')
        except urllib.error.HTTPError as e:assert e.code in [403,404]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    sources={p.relative_to(ROOT/'network').as_posix():p.read_bytes() for p in (ROOT/'network/fentwave').rglob('*') if p.is_file() and p.suffix in {'.html','.php','.css','.js','.png'} or p.is_file() and p.name=='.htaccess'}
    assert set(sources)=={'fentwave/'+n for n in ['index.html','fentwave.css','fentwave.js','waitlist.php','waitlist-core.php','notify.php','.htaccess','images/main.png','images/mod.png']}
    report={'utc':datetime.now(timezone.utc).isoformat(),'url':'https://y2kcrisis.com/fentwave/','public_files':{n:digest(b) for n,b in sources.items()},'status':'plan'}
    if not args.publish and not args.verify_only:print(json.dumps(report,indent=2));return
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=ROOT/'build/fentwave-publish'/stamp;backup.mkdir(parents=True)
    c=connect_sftp();s=c.open_sftp();s.get_channel().settimeout(30)
    def read(path):
        with s.open(path,'rb') as f:return f.read()
    def command(text):
        _,out,err=c.exec_command(text,timeout=40);raw=out.read().decode();exit_code=out.channel.recv_exit_status()
        if exit_code:raise RuntimeError('Remote operation failed (exit '+str(exit_code)+'); no secrets logged')
        return raw
    def directory(path,mode):
        try:
            if not stat.S_ISDIR(s.lstat(path).st_mode):raise RuntimeError('Destination is not a real directory')
        except FileNotFoundError:s.mkdir(path,mode)
    def upload(path,body,mode=0o644):
        temporary=path+'.fentwave-upload'
        with s.open(temporary,'wb') as f:f.write(body)
        s.chmod(temporary,mode)
        if digest(read(temporary))!=digest(body):raise RuntimeError('Upload verification failed')
        s.posix_rename(temporary,path)
    try:
        for path in [REMOTE,PRIVATE]:
            assert read(path+'/.y2kcrisis-owner')==b'y2kcrisis-network-v1\n','Unexpected owner marker'
        info=json.loads(command('uapi --output=json DomainInfo single_domain_data domain=y2kcrisis.com'))['result']
        assert info['status']==1 and info['data']['documentroot']==REMOTE
        if args.verify_only:
            verify_public(sources,report)
            assert b'href="/fentwave/"' in read(REMOTE+'/index.html')
            for name,body in sources.items():assert digest(read(REMOTE+'/'+name))==digest(body)
            assert read(REMOTE+'/fentwave/.fentwave-owner')==b'fentwave-waitlist-v1\n'
            assert stat.S_IMODE(s.stat(PRIVATE+'/fentwave-waitlist').st_mode)==0o700
            for name in ['contact.keys','contacts.sqlite']:assert stat.S_IMODE(s.stat(PRIVATE+'/fentwave-waitlist/'+name).st_mode)==0o600
            cron=command('crontab -l');assert '# fentwave-waitlist-retry' in cron
            report.update(status='published-and-verified',notification_retry='Installed; every five minutes',private_permissions='Directory0700; encryption key/database0600',mail_test='Accepted during preceding publication; not repeated by read-only verification')
            (backup/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return
        target=REMOTE+'/fentwave'
        try:
            s.stat(target)
            assert read(target+'/.fentwave-owner')==b'fentwave-waitlist-v1\n','Existing page is not this deployment'
        except FileNotFoundError:
            try:
                existing=s.listdir(target)
                if existing:raise RuntimeError('Refusing to replace an existing FENTWAVE page')
            except FileNotFoundError:directory(target,0o755)
            upload(target+'/.fentwave-owner',b'fentwave-waitlist-v1\n')
        stage=PRIVATE+'/fentwave-stage-'+stamp;directory(stage,0o700)
        for name,body in sources.items():
            if name.endswith('.php'):
                dest=stage+'/'+name.rsplit('/',1)[-1];upload(dest,body,0o600);command(PHP+' -l '+shlex.quote(dest))
        # Initialize encrypted storage before exposing the form. No keys are fetched or printed.
        init='$_SERVER["DOCUMENT_ROOT"]='+json.dumps(REMOTE)+';require '+json.dumps(stage+'/waitlist-core.php')+';fw_db();echo "Encrypted storage initialized";'
        command('Y2KCRISIS_DATA='+shlex.quote(PRIVATE)+' '+PHP+' -r '+shlex.quote(init))
        directory(target+'/images',0o755)
        # Publish PHP dependencies first, HTML entry point last.
        ordered=sorted(sources,key=lambda name:(name.endswith('index.html'),name))
        for name in ordered:
            path=REMOTE+'/'+name
            try:
                old=read(path)
                prior=backup/name;prior.parent.mkdir(parents=True,exist_ok=True);prior.write_bytes(old)
            except FileNotFoundError:pass
            upload(path,sources[name])
        # Insert one navigation link into the current live document, retaining all other live changes.
        before=read(REMOTE+'/index.html');anchor=b'<a href="#apps">[ APPS ]</a>'
        if b'href="/fentwave/"' not in before:
            assert before.count(anchor)==1,'Navigation anchor changed'
            after=before.replace(anchor,anchor+b'<a href="/fentwave/">[ FENTWAVE ]</a>')
            (backup/'index.html').write_bytes(before)
            assert read(REMOTE+'/index.html')==before,'Live navigation changed concurrently'
            upload(REMOTE+'/index.html',after)
        else:after=before
        report['root_index_sha256']=digest(after)
        report['mail_test']=command('Y2KCRISIS_DATA='+shlex.quote(PRIVATE)+' '+PHP+' '+shlex.quote(target+'/notify.php')+' --self-test').strip()
        cron_line='*/5 * * * * Y2KCRISIS_DATA='+PRIVATE+' '+PHP+' '+target+'/notify.php --process >/dev/null 2>&1 # fentwave-waitlist-retry'
        stdin,out,err=c.exec_command('crontab -l',timeout=20);current=out.read().decode();cron_error=err.read().decode();rc=out.channel.recv_exit_status()
        if rc!=0 and not (rc==1 and 'no crontab for' in cron_error.lower()):raise RuntimeError('Cannot read existing cron configuration safely')
        if '# fentwave-waitlist-retry' not in current:
            updated=current.rstrip()+'\n'+cron_line+'\n'
            stdin,out,err=c.exec_command('crontab -',timeout=20);stdin.write(updated);stdin.channel.shutdown_write();out.read()
            if out.channel.recv_exit_status()!=0:raise RuntimeError('Notification retry cron could not be installed')
        report['notification_retry']='Every five minutes; existing jobs preserved'
        # Certificate-verified HTTPS, never a disabled verification context.
        verify_public(sources,report)
        report['status']='published-and-verified'
        (backup/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:s.close();c.close()
if __name__=='__main__':main()
