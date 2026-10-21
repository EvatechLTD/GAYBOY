"""Apply the user's approved privacy changes with private backups and scoped edits."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import secrets
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp

PHP='/opt/cpanel/ea-php83/root/usr/bin/php'
STAMP=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
BACKUP=ROOT/'build/privacy-hardening'/('deploy-'+STAMP)
BACKUP.mkdir(parents=True,exist_ok=True)

def execute(client,code):
    i,o,e=client.exec_command(PHP,timeout=90);i.write(code);i.flush();i.channel.shutdown_write()
    result=o.read().decode();error=e.read().decode()
    if o.channel.recv_exit_status()!=0:raise RuntimeError(error or result)
    return result

def write(sftp,path,payload):
    if isinstance(payload,str):payload=payload.encode()
    try:
        with sftp.open(path,'rb') as f:old=f.read()
        if old==payload:return
        saved=BACKUP/path.lstrip('/');saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(old)
    except FileNotFoundError:pass
    temporary='/home/centered/tmp/privacy-upload-'+secrets.token_hex(12)
    with sftp.open(temporary,'wb') as f:f.write(payload)
    sftp.chmod(temporary,0o600)
    if path.endswith('.php'):
        _,o,e=_CLIENT.exec_command(PHP+' -l '+shlex.quote(temporary),timeout=20)
        if o.channel.recv_exit_status()!=0:
            sftp.remove(temporary);raise RuntimeError('Staged PHP failed syntax validation')
    sftp.chmod(temporary,0o644)
    with sftp.open(temporary,'rb') as f:assert hashlib.sha256(f.read()).digest()==hashlib.sha256(payload).digest()
    sftp.posix_rename(temporary,path)
    print('Updated:',path)

def read(sftp,path):
    with sftp.open(path,'rb') as f:return f.read().decode('utf8')

def replace_once(text,old,new):
    if new in text:return text
    if text.count(old)!=1:raise RuntimeError('Remote source changed; refusing an ambiguous patch')
    return text.replace(old,new,1)

def main():
    global _CLIENT
    client=connect_sftp();_CLIENT=client;sftp=client.open_sftp()
    try:
        wp='/home/centered/evatechusa.com';net='/home/centered/y2kcrisis.com'
        for directory,expected in [(net,'y2kcrisis-network-v1\n')]:
            assert read(sftp,directory+'/.y2kcrisis-owner')==expected
        # Resolve every live-source transformation before changing any public source file.
        updates={}
        action=read(sftp,net+'/actions.php')
        old="    $dir=$home.'/uploads';if(!is_dir($dir))mkdir($dir,0700,true);$id=hash('sha256',$raw);"
        local=(ROOT/'network/actions.php').read_text(encoding='utf8')
        added=local[local.index("    $strip=$p['strip_metadata']"):local.index(old)]+old
        updates[net+'/actions.php']=replace_once(action,old,added)
        core=read(sftp,net+'/core.js');local=(ROOT/'network/core.js').read_text(encoding='utf8')
        before="export async function upload(file){if(!file)return '';if(file.size>2400000)throw Error('Choose an image under 2.4 MB.');const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file);});return (await api('upload',{data})).url;}"
        after=local[local.index('let stripUploadMetadata=true;'):local.index('export function formData')].rstrip()
        updates[net+'/core.js']=replace_once(core,before,after)
        editor=read(sftp,net+'/editor.js')
        editor=replace_once(editor,'notify,upload,field','notify,upload,uploadPrivacyControls,field')
        editor=replace_once(editor,"$('#builder-controls').innerHTML=`<form id=\"builder-form\">${controls}</form>`;","$('#builder-controls').innerHTML=`${uploadPrivacyControls()}<form id=\"builder-form\">${controls}</form>`;")
        updates[net+'/editor.js']=editor
        social=read(sftp,net+'/social.js')
        social=replace_once(social,'refresh,upload,url','refresh,upload,uploadPrivacyControls,setUploadPrivacy,url')
        social=replace_once(social,"document.addEventListener('change',async e=>{if(e.target.id==='room-wallpaper-upload')","document.addEventListener('change',async e=>{if(e.target.matches('[data-upload-privacy]')){setUploadPrivacy(e.target.checked);document.querySelectorAll('[data-upload-privacy]').forEach(el=>el.checked=e.target.checked);}if(e.target.id==='room-wallpaper-upload')")
        social=replace_once(social,'<label>Upload room wallpaper<input id="room-wallpaper-upload"','${uploadPrivacyControls()}<label>Upload room wallpaper<input id="room-wallpaper-upload"')
        updates[net+'/social.js']=social
        # Patch GitHub links in live files without replacing unrelated live content.
        paths=json.loads((ROOT/'build/privacy-hardening/github-updated-files.json').read_text())
        for relative in paths:
            p=Path(relative)
            if p.parts[0] not in ('website','network'):continue
            remote=('/home/centered/buttholechopper.com/gayboy/'+'/'.join(p.parts[1:])) if p.parts[0]=='website' else net+'/'+'/'.join(p.parts[1:])
            content=read(sftp,remote);updates[remote]=content.replace('dpjpandone','EvatechLTD')
        for localname in ['evatech-image-privacy.php','evatech-security.php','evatech-avatar.svg']:
            try:sftp.stat(wp+'/wp-content/mu-plugins')
            except FileNotFoundError:sftp.mkdir(wp+'/wp-content/mu-plugins',0o755)
            source=(ROOT/'network/image-privacy.php') if localname=='evatech-image-privacy.php' else (ROOT/'hosting/evatech'/localname)
            write(sftp,wp+'/wp-content/mu-plugins/'+localname,source.read_bytes())
        ht=read(sftp,wp+'/.htaccess')
        ht=re.sub(r'# BEGIN EVATECH PRIVACY SECURITY\n.*?# END EVATECH PRIVACY SECURITY\n?','',ht,flags=re.S)
        updates[wp+'/.htaccess']=(ROOT/'hosting/evatech/security-htaccess.txt').read_text()+"\n"+ht
        # Dependencies precede consumers; lint PHP before enabling the upload action.
        write(sftp,net+'/image-privacy.php',(ROOT/'network/image-privacy.php').read_bytes())
        for path,content in updates.items():write(sftp,path,content)
        for path in [net+'/image-privacy.php',net+'/actions.php',wp+'/wp-content/mu-plugins/evatech-security.php']:
            _,o,e=client.exec_command(PHP+' -l '+shlex.quote(path),timeout=20)
            if o.channel.recv_exit_status()!=0:raise RuntimeError(e.read().decode())
        result=execute(client,(ROOT/'hosting/evatech/apply-privacy.php').read_text(encoding='utf8'))
        (BACKUP/'wordpress-result.json').write_text(result,encoding='utf8');print(result)
        result=execute(client,r'''<?php
umask(0077);$home='/home/centered/y2kcrisis-private';
$db=new SQLite3($home.'/network.sqlite');$db->enableExceptions(true);$db->busyTimeout(5000);
$backup=$home.'/backups/privacy-'''+STAMP+r'''.sqlite';$copy=new SQLite3($backup);if(!$db->backup($copy))throw new Exception('Network backup failed');$copy->close();chmod($backup,0600);
$row=$db->querySingle("SELECT id,handle,settings FROM users WHERE handle='FarkSukerburg' COLLATE NOCASE",true);if(!$row)throw new Exception('Owner profile missing');
$s=json_decode($row['settings'],true);$removed=false;
if(str_contains($s['soundtrack']??'','soundcloud.com/jon-pandone/')){$s['soundtrack']='';$stmt=$db->prepare('UPDATE users SET settings=?,updated=? WHERE id=?');$stmt->bindValue(1,json_encode($s),SQLITE3_TEXT);$stmt->bindValue(2,time(),SQLITE3_INTEGER);$stmt->bindValue(3,$row['id'],SQLITE3_INTEGER);$stmt->execute();$removed=true;}
function clean_soundtrack($v){
 if(is_array($v)){foreach($v as $k=>$item)$v[$k]=clean_soundtrack($item);return $v;}
 if(!is_string($v))return $v;
 $decoded=json_decode($v,true);if(is_array($decoded))return json_encode(clean_soundtrack($decoded));
 return preg_replace('#https?://soundcloud\.com/jon-pandone/[^\s"<>]*#','',$v);
}
$revisions=$db->prepare('SELECT id,payload FROM revisions WHERE owner=?');$revisions->bindValue(1,$row['id'],SQLITE3_INTEGER);$r=$revisions->execute();$cleaned=0;
while($revision=$r->fetchArray(SQLITE3_ASSOC)){
 $decoded=json_decode($revision['payload'],true);if(!is_array($decoded))continue;
 $payload=json_encode(clean_soundtrack($decoded));
 if(str_contains(str_replace('\\/','/',$revision['payload']),'soundcloud.com/jon-pandone/')&&$payload!==$revision['payload']){$stmt=$db->prepare('UPDATE revisions SET payload=? WHERE id=?');$stmt->bindValue(1,$payload,SQLITE3_TEXT);$stmt->bindValue(2,$revision['id'],SQLITE3_INTEGER);$stmt->execute();$cleaned++;}
}
$r=$db->query("SELECT id,settings,blocks FROM users WHERE handle IN ('GAYBOY','buttholechopper','FarkSukerburg')");$github=0;
while($u=$r->fetchArray(SQLITE3_ASSOC)){
 $settings=str_replace('dpjpandone','EvatechLTD',$u['settings']);$blocks=str_replace('dpjpandone','EvatechLTD',$u['blocks']);
 if($settings!==$u['settings']||$blocks!==$u['blocks']){$stmt=$db->prepare('UPDATE users SET settings=?,blocks=? WHERE id=?');$stmt->bindValue(1,$settings,SQLITE3_TEXT);$stmt->bindValue(2,$blocks,SQLITE3_TEXT);$stmt->bindValue(3,$u['id'],SQLITE3_INTEGER);$stmt->execute();$github++;}
}
echo json_encode(['soundtrack_removed'=>$removed,'old_revisions_cleaned'=>$cleaned,'github_profiles_updated'=>$github,'private_backup'=>$backup]);
''')
        (BACKUP/'network-result.json').write_text(result,encoding='utf8');print(result)
        print('Deployment completed. Public browser/HTTPS verification is required next.')
    finally:sftp.close();client.close()

if __name__=='__main__':main()
