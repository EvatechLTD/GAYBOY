<?php
declare(strict_types=1);
function admin_session(): void {
    if(session_status()===PHP_SESSION_ACTIVE)return;
    umask(0077);ini_set('session.use_strict_mode','1');ini_set('session.use_only_cookies','1');
    ini_set('session.gc_maxlifetime','86400');session_name('GAYBOYADMIN');session_save_path(__DIR__.'/sessions');
    session_set_cookie_params(['lifetime'=>86400,'path'=>wall_local()?'/admin/':'/gayboy/admin/',
        'secure'=>!wall_local(),'httponly'=>true,'samesite'=>'Strict']);
    session_start();$_SESSION['admin_csrf']??=bin2hex(random_bytes(32));
}
function admin_authenticated(): bool {
    return isset($_SESSION['admin_until']) && $_SESSION['admin_until']>time();
}
function admin_auth_file(): array {
    $bytes=@file_get_contents(__DIR__.'/admin-auth.json');
    if($bytes===false)wall_fail(503,'Admin setup is not ready yet.');
    $data=json_decode($bytes,true,16,JSON_THROW_ON_ERROR);
    if(!is_array($data))throw new RuntimeException('Invalid admin credentials');
    return $data;
}
function admin_write_auth(array $data): void {
    $path=__DIR__.'/admin-auth.json';$temp=$path.'.'.bin2hex(random_bytes(6));
    if(file_put_contents($temp,json_encode($data),LOCK_EX)===false)throw new RuntimeException('Could not save admin password');
    chmod($temp,0600);if(!rename($temp,$path))throw new RuntimeException('Could not install admin password');
}
function admin_post(): void {
    if($_SERVER['REQUEST_METHOD']!=='POST')wall_fail(405,'Use POST for that action.');
    if((int)($_SERVER['CONTENT_LENGTH']??0)>4096)wall_fail(413,'Request too large.');
    $allowed=['https://buttholechopper.com','https://www.buttholechopper.com'];
    if(wall_local())$allowed[]='http://'.($_SERVER['HTTP_HOST']??'');
    if(!in_array($_SERVER['HTTP_ORIGIN']??'',$allowed,true))wall_fail(403,'Use the admin page to do that.');
    $csrf=$_POST['csrf']??null;
    if(!is_string($csrf)||!hash_equals($_SESSION['admin_csrf'],$csrf))wall_fail(403,'Your form expired. Reload the admin page.');
}
function admin_counts(): array {
    $db=wall_db();
    $comments=(int)$db->querySingle('SELECT count(*) FROM comments WHERE reviewed=0');
    return ['new_comments'=>$comments];
}
function admin_handle(): never {
    header('Cache-Control: no-store');header('X-Robots-Tag: noindex, nofollow');
    $action=$_GET['action']??'status';if(!is_string($action))wall_fail(400,'Invalid action.');
    if($action==='status' && !isset($_COOKIE['GAYBOYADMIN']))wall_json(['authenticated'=>false]);
    admin_session();
    if($action==='session'||$action==='status'){
        $auth=admin_auth_file();$signed=admin_authenticated();
        wall_json(['authenticated'=>$signed,'csrf'=>$_SESSION['admin_csrf'],'setup_required'=>!isset($auth['password_hash']),...($signed?admin_counts():[])]);
    }
    if(in_array($action,['login','setup'],true)) {
        admin_post();wall_limit('admin-login',wall_actor(),900,10);
        $auth=admin_auth_file();$password=$_POST['password']??'';
        if(!is_string($password)||strlen($password)>200)wall_fail(422,'Invalid password.');
        if($action==='setup'){
            // Serialize the one-time setup so simultaneous requests cannot replace a password.
            $lock=fopen(__DIR__.'/admin-setup.lock','c');if(!$lock||!flock($lock,LOCK_EX))throw new RuntimeException('Setup lock unavailable');
            try{
                $auth=admin_auth_file();$token=$_POST['setup_token']??'';
                if(isset($auth['password_hash'])||!is_string($token)||!preg_match('/^[a-f0-9]{64}$/D',$token)||($auth['setup_expires']??0)<time()||!hash_equals($auth['setup_hash']??'',hash('sha256',$token)))
                    wall_fail(403,'That setup link is invalid or has expired.');
                if(strlen($password)<12)wall_fail(422,'Choose a password with at least 12 characters.');
                admin_write_auth(['password_hash'=>password_hash($password,PASSWORD_DEFAULT)]);
            }finally{flock($lock,LOCK_UN);fclose($lock);}
        }else{
            if(!isset($auth['password_hash'])||!password_verify($password,$auth['password_hash']))wall_fail(403,'The password did not match.');
        }
        session_regenerate_id(true);$_SESSION['admin_until']=time()+86400;$_SESSION['admin_csrf']=bin2hex(random_bytes(32));
        wall_json(['authenticated'=>true,'csrf'=>$_SESSION['admin_csrf'],...admin_counts()]);
    }
    if(!admin_authenticated())wall_fail(401,'Please log in to moderate.');
    if($action==='avatar' && $_SERVER['REQUEST_METHOD']==='GET'){
        $id=filter_var($_GET['id']??0,FILTER_VALIDATE_INT,['options'=>['min_range'=>1]]);
        if(!$id)wall_fail(404,'Thumbnail not found.');
        $row=wall_query('SELECT avatar FROM comments WHERE id=:id',['id'=>$id])->fetchArray(SQLITE3_ASSOC);
        if(!$row||$row['avatar']===null)wall_fail(404,'Thumbnail not found.');
        header('Content-Type: image/png');header('X-Content-Type-Options: nosniff');echo $row['avatar'];exit;
    }
    if($action==='list' && $_SERVER['REQUEST_METHOD']==='GET'){
        $before=filter_var($_GET['before']??PHP_INT_MAX,FILTER_VALIDATE_INT,['options'=>['min_range'=>1]]);
        if($before===false)wall_fail(400,'Invalid page.');
        $result=wall_query('SELECT id,name,body,created_at,(avatar IS NOT NULL) AS has_avatar,reviewed FROM comments WHERE id<:before ORDER BY id DESC LIMIT 51',['before'=>$before]);
        $rows=[];while($row=$result->fetchArray(SQLITE3_ASSOC))$rows[]=$row;
        $more=count($rows)>50;if($more)array_pop($rows);
        $beats=[];$db=wall_db();
        if($db->querySingle("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='beats'")){
            $result=wall_query('SELECT id,name,title,created_at FROM beats ORDER BY created_at DESC,id DESC LIMIT 100');
            while($row=$result->fetchArray(SQLITE3_ASSOC))$beats[]=$row;
        }
        wall_json(['comments'=>$rows,'beats'=>$beats,'next_before'=>$more?end($rows)['id']:null,...admin_counts()]);
    }
    admin_post();
    if($action==='logout'){
        $_SESSION=[];session_destroy();setcookie('GAYBOYADMIN','',['expires'=>time()-3600,'path'=>wall_local()?'/admin/':'/gayboy/admin/','secure'=>!wall_local(),'httponly'=>true,'samesite'=>'Strict']);wall_json(['authenticated'=>false]);
    }
    if(in_array($action,['approve','delete-comment'],true)){
        $id=filter_var($_POST['id']??0,FILTER_VALIDATE_INT,['options'=>['min_range'=>1]]);
        if(!$id)wall_fail(400,'Invalid comment.');
        wall_query($action==='approve'?'UPDATE comments SET reviewed=1 WHERE id=:id':'DELETE FROM comments WHERE id=:id',['id'=>$id]);
        wall_json(['updated'=>true,...admin_counts()]);
    }
    if($action==='delete-beat'){
        $id=$_POST['id']??'';if(!is_string($id)||!preg_match('/^[a-f0-9]{24}$/D',$id))wall_fail(400,'Invalid beat.');
        wall_query('DELETE FROM beats WHERE id=:id',['id'=>$id]);wall_json(['deleted'=>true]);
    }
    wall_fail(400,'Invalid action.');
}
try{admin_handle();}
catch(WallError $e){wall_json(['error'=>$e->getMessage()],$e->status);}
catch(Throwable $e){error_log('GAYBOY admin: '.$e->getMessage());wall_json(['error'=>'Admin is temporarily unavailable. Please try again.'],503);}
