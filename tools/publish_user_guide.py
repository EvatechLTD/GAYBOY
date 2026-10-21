"""Publish only the approved guide files to y2k GAYBOY."""
from pathlib import Path
import sys,re,hashlib
from datetime import datetime,timezone
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp
out=ROOT/'network/apps/gayboy/guide';out.mkdir(parents=True,exist_ok=True)
s=(ROOT/'docs/user-guide/GAYBOY-user-guide.html').read_text(encoding='utf-8')
css=re.search(r'<style>(.*?)</style>',s,re.S).group(1)
(out/'guide.css').write_text(css,encoding='utf-8')
(out/'index.html').write_text(re.sub(r'<style>.*?</style>','<link rel="stylesheet" href="guide.css">',s,flags=re.S),encoding='utf-8')
(out/'GAYBOY-user-guide.pdf').write_bytes((ROOT/'docs/user-guide/GAYBOY-user-guide.pdf').read_bytes())
backup=ROOT/'build'/('guide-publish-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
remote='/home/centered/y2kcrisis.com/apps/gayboy/guide'
client=connect_sftp();ftp=client.open_sftp();ftp.get_channel().settimeout(30)
try:
 try:ftp.stat(remote)
 except FileNotFoundError:ftp.mkdir(remote)
 for name in ('guide.css','GAYBOY-user-guide.pdf','index.html'):
  try:ftp.get(remote+'/'+name,str(backup/name))
  except FileNotFoundError:pass
  ftp.put(str(out/name),remote+'/'+name+'.upload')
  ftp.chmod(remote+'/'+name+'.upload',0o644)
  ftp.posix_rename(remote+'/'+name+'.upload',remote+'/'+name)
finally:ftp.close();client.close()
for name in ('guide.css','GAYBOY-user-guide.pdf','index.html'):
 url='https://y2kcrisis.com/apps/gayboy/guide/'+name
 with urlopen(url,timeout=30) as r:data=r.read()
 assert hashlib.sha256(data).digest()==hashlib.sha256((out/name).read_bytes()).digest(),name
 print('Verified:',url)
