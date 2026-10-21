"""Y2KCRISIS hosting: use existing encrypted credentials, never log secrets."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shlex
import stat
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp, load_credentials, STATE, protect

DOMAIN = 'y2kcrisis.com'
REMOTE = '/home/centered/y2kcrisis.com'
PRIVATE = '/home/centered/y2kcrisis-private'


def panel(path, params):
    # Use the owner's authenticated browser so normal verification remains intact.
    from playwright.sync_api import sync_playwright
    import re
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.connect_over_cdp('http://127.0.0.1:9227', timeout=2000)
            for context in browser.contexts:
                for page in context.pages:
                    match = re.match(r'https://node613\.namehero\.net:2083(/cpsess\d+)(?:/|$)',page.url)
                    if match:
                        target = match.group(1)+path+'?'+urllib.parse.urlencode(params)
                        result = page.evaluate('async path => (await fetch(path,{credentials:"same-origin",signal:AbortSignal.timeout(60000)})).json()',target)
                        return result.get('result',result)
        except Exception:
            pass
    saved = STATE / 'namehero-cpanel-browser-session.dpapi'
    if saved.exists():
        session = json.loads(protect(saved.read_bytes(), decrypt=True))
        cookie = '; '.join(c['name']+'='+c['value'] for c in session['storage']['cookies']
                           if 'namehero.net' in c['domain'])
        request = urllib.request.Request(session['base'] + path + '?' + urllib.parse.urlencode(params),
                                         headers={'Cookie': cookie})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
        try:
            result = json.loads(raw)
            return result.get('result', result)
        except json.JSONDecodeError:
            pass
    creds = load_credentials()
    auth = base64.b64encode((creds['username'] + ':' + creds['password']).encode()).decode()
    request = urllib.request.Request('https://node613.namehero.net:2083' + path,
        data=urllib.parse.urlencode(params).encode(), headers={'Authorization': 'Basic ' + auth})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    finally:
        creds['password'] = ''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['setup', 'stage', 'deploy', 'ssl', 'status'])
    args = parser.parse_args()
    if args.action == 'setup':
        domains = panel('/execute/DomainInfo/list_domains', {})
        if domains.get('status') != 1:
            raise RuntimeError('Could not verify existing hosting domains.')
        if DOMAIN not in domains['data']['addon_domains']:
            result = panel('/json-api/cpanel', {'cpanel_jsonapi_apiversion': 2,
                'cpanel_jsonapi_module': 'AddonDomain', 'cpanel_jsonapi_func': 'addaddondomain',
                'cpanel_jsonapi_user': 'centered',
                'dir': REMOTE, 'newdomain': DOMAIN, 'subdomain': 'y2kcrisis'})
            print(json.dumps(result))
        else:
            print('Domain already attached; preserving its configuration.')
    elif args.action == 'ssl':
        print(json.dumps(panel('/execute/SSL/start_autossl_check', {})))
    elif args.action == 'status':
        print(json.dumps(panel('/execute/DomainInfo/single_domain_data', {'domain': DOMAIN})))
        result=panel('/execute/SSL/installed_hosts', {})
        print(json.dumps({'certificates':[
            {'domains':host.get('certificate',{}).get('domains'),
             'expires':host.get('certificate',{}).get('not_after'),
             'issuer':host.get('certificate',{}).get('issuer.organizationName')}
            for host in result.get('data',[]) if DOMAIN in host.get('fqdns',[])]}))
    elif args.action in ('deploy', 'stage'):
        client = connect_sftp()
        if args.action == 'deploy':
            _,stdout,stderr=client.exec_command('uapi --output=json DomainInfo single_domain_data domain='+DOMAIN,timeout=25)
            info=json.loads(stdout.read().decode())['result']
            if info.get('status') != 1 or info.get('data', {}).get('documentroot') != REMOTE:
                client.close()
                raise RuntimeError('Domain document root does not match the intended deployment directory.')
        sftp = client.open_sftp()
        try:
            for path in (REMOTE, PRIVATE):
                try:
                    entry = sftp.lstat(path)
                    if not stat.S_ISDIR(entry.st_mode):
                        raise RuntimeError('Deployment directory is not a real directory.')
                except FileNotFoundError:
                    sftp.mkdir(path, 0o700 if path == PRIVATE else 0o755)
                marker=path+'/.y2kcrisis-owner'
                try:
                    with sftp.open(marker,'rb') as stream:
                        if stream.read()!=b'y2kcrisis-network-v1\n':
                            raise RuntimeError('Unexpected directory ownership marker.')
                except FileNotFoundError:
                    if set(sftp.listdir(path))-{'cgi-bin'}:
                        raise RuntimeError('Refusing to claim a populated directory.')
                    with sftp.open(marker,'wx') as stream:
                        stream.write(b'y2kcrisis-network-v1\n')
            sftp.chmod(PRIVATE, 0o700)
            try:
                sftp.stat(PRIVATE+'/network.sqlite')
                backup_dir=PRIVATE+'/backups'
                try:
                    if not stat.S_ISDIR(sftp.lstat(backup_dir).st_mode):
                        raise RuntimeError('Backup directory must be a real directory.')
                except FileNotFoundError:
                    sftp.mkdir(backup_dir,0o700)
                target=backup_dir+'/network-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite'
                code='umask(0077);$s=new SQLite3('+json.dumps(PRIVATE+'/network.sqlite')+');$d=new SQLite3('+json.dumps(target)+');if(!$s->backup($d)){exit(2);}echo "Private SQLite backup saved.\\n";'
                _,stdout,stderr=client.exec_command('/opt/cpanel/ea-php83/root/usr/bin/php -r '+shlex.quote(code),timeout=30)
                result=stdout.read().decode()
                if stdout.channel.recv_exit_status()!=0:raise RuntimeError('Private database backup failed.')
                print(result.strip())
            except FileNotFoundError:
                pass
            # Only public program files. Private DB never enters document root.
            files = {name: (ROOT/'network'/name).read_bytes() for name in
                     ('schema.php','actions.php','image-privacy.php','queries.php','core.js','themes.js','media.js',
                      'emoji.js','homepage.js','editor.js','studio.js','social.js','app.js',
                      'style.css','community.css','homepage.css','favicon.svg','gayboy.json','feature-audit.json')}
            for path in (ROOT/'network/fonts').iterdir():
                if path.suffix in ('.ttf', '.txt'):
                    files['fonts/'+path.name] = path.read_bytes()
            for path in (ROOT/'network/retro').iterdir():
                if path.is_file() and (path.suffix in ('.html','.js','.css','.wasm','.txt') or path.name=='.htaccess'):
                    files['retro/'+path.name] = path.read_bytes()
            files['emoji/uwu.png']=(ROOT/'network/emoji/uwu.png').read_bytes()
            files['emoji/uwu-source.json']=(ROOT/'network/emoji/uwu-source.json').read_bytes()
            for path in (ROOT/'network/apps/gayboy').rglob('*'):
                if path.is_file() and (path.suffix in ('.html','.js','.css','.json','.wasm','.png','.gb','.txt') or path.name=='.htaccess'):
                    files[path.relative_to(ROOT/'network').as_posix()]=path.read_bytes()
            # Publish entry points after every file they depend on.
            for name in ('api.php','.htaccess','index.html'):
                files[name]=(ROOT/'network'/name).read_bytes()
            files['.htaccess'] += ('\nSetEnv Y2KCRISIS_DATA ' + PRIVATE + '\n').encode()
            directories=set()
            for name in files:
                parts=name.split('/')[:-1]
                for count in range(1,len(parts)+1):directories.add('/'.join(parts[:count]))
            for relative in sorted(directories,key=lambda x:(x.count('/'),x)):
                path=REMOTE+'/'+relative
                try:
                    if not stat.S_ISDIR(sftp.lstat(path).st_mode):raise RuntimeError('Asset path is not a real directory.')
                except FileNotFoundError:
                    sftp.mkdir(path,0o755)
            for name, payload in files.items():
                dest = REMOTE + '/' + name
                try:
                    old = sftp.lstat(dest)
                    if not stat.S_ISREG(old.st_mode):
                        raise RuntimeError('Refusing to replace a non-file.')
                    with sftp.open(dest, 'rb') as stream:
                        prior = stream.read()
                    if prior == payload:
                        print('Unchanged:', name)
                        continue
                    backup = ROOT/'build/network-publish'/hashlib.sha256(prior).hexdigest()/name
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    backup.write_bytes(prior)
                except FileNotFoundError:
                    pass
                temporary = dest + '.upload'
                with sftp.open(temporary, 'wb') as stream:
                    stream.write(payload)
                sftp.chmod(temporary, 0o644)
                with sftp.open(temporary, 'rb') as stream:
                    if hashlib.sha256(stream.read()).digest() != hashlib.sha256(payload).digest():
                        raise RuntimeError('Upload verification failed.')
                sftp.posix_rename(temporary, dest)
                print('Verified upload:', name)
            for name in ('api.php','schema.php','actions.php','queries.php'):
                command = '/opt/cpanel/ea-php83/root/usr/bin/php -l ' + shlex.quote(REMOTE+'/'+name)
                _, stdout, stderr = client.exec_command(command, timeout=25)
                print(stdout.read().decode().strip())
                if stdout.channel.recv_exit_status() != 0:
                    raise RuntimeError('Remote PHP syntax check failed.')
        finally:
            sftp.close()
            client.close()


if __name__ == '__main__':
    main()
