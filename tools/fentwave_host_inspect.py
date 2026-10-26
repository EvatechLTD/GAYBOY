"""Read-only hosting preflight; never prints credentials or user data."""
from pathlib import Path
import hashlib,json,shlex,sys
sys.path.insert(0,'G:/DEVELOPMENT/VIBECHOPPER/scripts')
from namehero_access import connect_sftp
root=Path(__file__).resolve().parents[1]
out=root/'build/fentwave-live-baseline';out.mkdir(parents=True,exist_ok=True)
c=connect_sftp();s=c.open_sftp()
try:
    remote='/home/centered/y2kcrisis.com'
    with s.open(remote+'/.y2kcrisis-owner','rb') as f:assert f.read()==b'y2kcrisis-network-v1\n'
    for name in ['index.html','.htaccess','app.js','core.js']:
        with s.open(remote+'/'+name,'rb') as f:data=f.read()
        (out/name).write_bytes(data)
        print(name,len(data),hashlib.sha256(data).hexdigest())
    code='echo json_encode(["php"=>PHP_VERSION,"openssl"=>extension_loaded("openssl"),"sqlite"=>extension_loaded("sqlite3"),"mail"=>function_exists("mail"),"mbstring"=>extension_loaded("mbstring")]);'
    _,stdout,stderr=c.exec_command('/opt/cpanel/ea-php83/root/usr/bin/php -r '+shlex.quote(code),timeout=25)
    result=stdout.read().decode();assert stdout.channel.recv_exit_status()==0
    print('Server capabilities:',result)
    print('Baseline saved; existing private data was not read.')
finally:s.close();c.close()
