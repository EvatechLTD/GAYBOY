"""Remove GPS metadata from existing WordPress photo files with private backups."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import apply_site_privacy as deploy

def main():
    c=deploy.connect_sftp();deploy._CLIENT=c;s=c.open_sftp()
    try:
        for name,source in [('evatech-image-privacy.php',ROOT/'network/image-privacy.php'),('evatech-security.php',ROOT/'hosting/evatech/evatech-security.php')]:
            deploy.write(s,'/home/centered/evatechusa.com/wp-content/mu-plugins/'+name,source.read_bytes())
        result=deploy.execute(c,r'''<?php
require '/home/centered/evatechusa.com/wp-load.php';umask(0077);
$root=realpath(ABSPATH.'wp-content/uploads');$backup='/home/centered/tmp/photo-privacy-'.gmdate('Ymd-His').'-'.bin2hex(random_bytes(4));mkdir($backup,0700);
$seen=[];$changed=[];$owners=[];
foreach(get_posts(['post_type'=>'attachment','post_status'=>'inherit','numberposts'=>-1]) as $p){
 $main=get_attached_file($p->ID);$meta=wp_get_attachment_metadata($p->ID);$paths=[$main];
 foreach(($meta['sizes']??[]) as $size)$paths[]=dirname($main).'/'.$size['file'];
 if(!empty($meta['original_image']))$paths[]=dirname($main).'/'.$meta['original_image'];
 foreach($paths as $path){
  $path=realpath($path);if(!$path||!str_starts_with($path,$root.'/')||isset($seen[$path])||!preg_match('/\.(?:jpe?g|tiff?)$/i',$path))continue;$seen[$path]=true;
  $ex=@exif_read_data($path,null,true);if(empty($ex['GPS']))continue;
  $info=getimagesize($path);if(!$info||$info['mime']!=='image/jpeg')continue;
  $raw=file_get_contents($path);$clean=image_privacy_strip($raw,$info['mime']);
  $saved=$backup.'/'.count($changed).'.jpg';if(file_put_contents($saved,$raw,LOCK_EX)!==strlen($raw))throw new Exception('Photo backup failed');chmod($saved,0600);
  $stage=tempnam('/home/centered/tmp','clean-photo-');if(file_put_contents($stage,$clean,LOCK_EX)!==strlen($clean))throw new Exception('Photo write failed');
  chmod($stage,fileperms($path)&0777);if(!rename($stage,$path))throw new Exception('Photo replacement failed');
  clearstatcache(true,$path);$ex=@exif_read_data($path,null,true);if(!empty($ex['GPS']))throw new Exception('GPS removal failed');
  $changed[]=['attachment'=>$p->ID,'relative_path'=>substr($path,strlen($root)+1),'backup'=>basename($saved)];$owners[$p->ID]=true;
 }
}
file_put_contents($backup.'/manifest.json',json_encode($changed,JSON_PRETTY_PRINT));chmod($backup.'/manifest.json',0600);
wp_cache_flush();do_action('litespeed_purge_all');echo json_encode(['attachments_sanitized'=>count($owners),'photo_files_sanitized'=>count($changed),'private_backup'=>$backup,'new_upload_protection'=>true]);
''')
        (ROOT/'build/privacy-hardening/photo-sanitization.json').write_text(result,encoding='utf8');print(result)
    finally:s.close();c.close()

if __name__=='__main__':main()
