<?php
// CLI only; preserves an existing password or unexpired setup link.
declare(strict_types=1);
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
umask(0077);$path=__DIR__.'/admin-auth.json';
$lock=fopen(__DIR__.'/admin-setup.lock','c');if(!$lock||!flock($lock,LOCK_EX))exit(2);
try{
    $auth=is_file($path)?json_decode(file_get_contents($path),true):[];
    if(isset($auth['password_hash'])){echo json_encode(['configured'=>true]);exit;}
    if(($auth['setup_expires']??0)>time() && ($argv[1]??'')!=='renew'){
        echo json_encode(['configured'=>false,'setup_link_exists'=>true]);exit;
    }
    $token=bin2hex(random_bytes(32));$tmp=$path.'.'.bin2hex(random_bytes(6));
    file_put_contents($tmp,json_encode(['setup_hash'=>hash('sha256',$token),'setup_expires'=>time()+86400]),LOCK_EX);chmod($tmp,0600);rename($tmp,$path);
    echo json_encode(['configured'=>false,'setup_token'=>$token]);
}finally{flock($lock,LOCK_UN);fclose($lock);}
