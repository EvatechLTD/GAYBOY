<?php
declare(strict_types=1);
// Lives outside all document roots. Only comments/api.php is public.
final class WallError extends RuntimeException {
    public function __construct(public int $status, string $message) { parent::__construct($message); }
}
function wall_fail(int $status, string $message): never { throw new WallError($status, $message); }
function wall_local(): bool {
    return PHP_SAPI === 'cli-server' && getenv('GAYBOY_COMMENTS_LOCAL_TEST') === '1'
        && in_array($_SERVER['REMOTE_ADDR'] ?? '', ['127.0.0.1', '::1'], true);
}
function wall_db(): SQLite3 {
    static $db;
    if ($db) return $db;
    umask(0077);
    $db = new SQLite3(__DIR__ . '/comments.sqlite');
    $db->enableExceptions(true); $db->busyTimeout(5000);
    $db->exec('PRAGMA journal_mode=WAL; PRAGMA secure_delete=ON;');
    $db->exec('CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, body TEXT NOT NULL,
        created_at INTEGER NOT NULL, avatar BLOB, delete_hash TEXT NOT NULL,
        author_key TEXT NOT NULL, fingerprint TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS comments_author ON comments(author_key,created_at);
        CREATE TABLE IF NOT EXISTS limits (
        bucket TEXT NOT NULL, actor TEXT NOT NULL, started INTEGER NOT NULL, count INTEGER NOT NULL,
        PRIMARY KEY(bucket,actor,started));');
    $columns=$db->query('PRAGMA table_info(comments)');$reviewed=false;
    while($column=$columns->fetchArray(SQLITE3_ASSOC))if($column['name']==='reviewed')$reviewed=true;
    if(!$reviewed)$db->exec('ALTER TABLE comments ADD COLUMN reviewed INTEGER NOT NULL DEFAULT 0');
    return $db;
}
function wall_query(string $sql, array $params = []): SQLite3Result {
    $statement = wall_db()->prepare($sql);
    foreach ($params as $key => $value) $statement->bindValue(':' . $key, $value,
        is_int($value) ? SQLITE3_INTEGER : (is_null($value) ? SQLITE3_NULL : SQLITE3_TEXT));
    return $statement->execute();
}
function wall_key(): string {
    $key = @file_get_contents(__DIR__ . '/secret.bin');
    if ($key === false || strlen($key) !== 32) throw new RuntimeException('Private wall key unavailable');
    return $key;
}
function wall_actor(): string {
    return hash_hmac('sha256', $_SERVER['REMOTE_ADDR'] ?? '', wall_key());
}
function wall_limit(string $bucket, string $actor, int $seconds, int $max): void {
    $started = intdiv(time(), $seconds) * $seconds;
    $db = wall_db(); $db->exec('BEGIN IMMEDIATE'); $active=true;
    try {
        wall_query('INSERT INTO limits(bucket,actor,started,count) VALUES(:bucket,:actor,:started,1)
            ON CONFLICT(bucket,actor,started) DO UPDATE SET count=count+1', compact('bucket','actor','started'));
        $row = wall_query('SELECT count FROM limits WHERE bucket=:bucket AND actor=:actor AND started=:started',
            compact('bucket','actor','started'))->fetchArray(SQLITE3_ASSOC);
        wall_query('DELETE FROM limits WHERE started < :cutoff', ['cutoff'=>time()-86400]);
        $db->exec('COMMIT'); $active=false;
        if ((int)$row['count'] > $max) { header('Retry-After: ' . $seconds); wall_fail(429, 'Too many attempts. Please wait a few minutes and try again.'); }
    } catch (Throwable $e) { if ($active) $db->exec('ROLLBACK'); throw $e; }
}
function wall_session(): void {
    if (session_status() === PHP_SESSION_ACTIVE) return;
    umask(0077);
    if (!is_dir(__DIR__.'/sessions')) mkdir(__DIR__.'/sessions',0700);
    ini_set('session.use_strict_mode','1'); ini_set('session.use_only_cookies','1');
    ini_set('session.gc_maxlifetime','3600');
    session_name('GAYBOYWALL'); session_save_path(__DIR__.'/sessions');
    session_set_cookie_params(['lifetime'=>0,'path'=>wall_local()?'/':'/gayboy/',
        'secure'=>!wall_local(),'httponly'=>true,'samesite'=>'Strict']);
    session_start();
    $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
    $_SESSION['challenges'] ??= [];
    foreach ($_SESSION['challenges'] as $id=>$challenge)
        if ($challenge['created'] < time()-1200) unset($_SESSION['challenges'][$id]);
}
function wall_json(array $data, int $status=200): never {
    http_response_code($status); header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store'); header('X-Content-Type-Options: nosniff');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE); exit;
}
function wall_challenge(string $nonce): array {
    wall_session();
    if (!preg_match('/^[a-f0-9]{32}$/D',$nonce) || !isset($_SESSION['challenges'][$nonce]))
        wall_fail(400,'That human check expired. Get a new code and try again.');
    return $_SESSION['challenges'][$nonce];
}
function wall_image(string $code): never {
    $image=imagecreatetruecolor(320,90);
    $background=imagecolorallocate($image,213,232,161);
    $noise=imagecolorallocate($image,158,184,114);
    imagefill($image,0,0,$background);
    for($i=0;$i<330;$i++) imagesetpixel($image,random_int(0,319),random_int(0,89),$noise);
    for($i=0;$i<8;$i++) imageline($image,random_int(0,319),random_int(0,89),random_int(0,319),random_int(0,89),$noise);
    foreach(str_split($code) as $i=>$digit) {
        $letter=imagecreatetruecolor(18,23); imagefill($letter,0,0,imagecolorallocate($letter,213,232,161));
        imagestring($letter,5,4,3,$digit,imagecolorallocate($letter,24,45,36));
        $large=imagescale($letter,40,55,IMG_NEAREST_NEIGHBOUR);
        $rotated=imagerotate($large,random_int(-12,12),imagecolorallocate($large,213,232,161));
        imagecopy($image,$rotated,14+$i*49,random_int(12,20),0,0,imagesx($rotated),imagesy($rotated));
        imagedestroy($letter);imagedestroy($large);imagedestroy($rotated);
    }
    header('Content-Type: image/png'); header('Cache-Control: no-store');
    imagepng($image);imagedestroy($image);exit;
}
function wall_audio(string $code): never {
    $pcm='';
    foreach(str_split($code) as $digit) {
        $wav=file_get_contents(__DIR__.'/audio/'.$digit.'.wav');
        $offset=12;$data=null;
        while($offset+8<=strlen($wav)) {
            $type=substr($wav,$offset,4);$size=unpack('V',substr($wav,$offset+4,4))[1];
            if($type==='data') {$data=substr($wav,$offset+8,$size);break;}
            $offset+=8+$size+($size%2);
        }
        if($data===null) throw new RuntimeException('Audio clip unavailable');
        $pcm.=$data.str_repeat("\0",6400);
    }
    $header='RIFF'.pack('V',36+strlen($pcm)).'WAVEfmt '.pack('VvvVVvv',16,1,1,16000,32000,2,16)
        .'data'.pack('V',strlen($pcm));
    header('Content-Type: audio/wav');header('Cache-Control: no-store');
    header('Content-Length: '.(strlen($header)+strlen($pcm)));echo $header.$pcm;exit;
}
function wall_avatar(): ?string {
    if(!isset($_FILES['avatar']) || $_FILES['avatar']['error']===UPLOAD_ERR_NO_FILE) return null;
    $file=$_FILES['avatar'];
    if($file['error']!==UPLOAD_ERR_OK || $file['size']>2097152 || !is_uploaded_file($file['tmp_name']))
        wall_fail(422,'Choose a PNG, JPEG or WebP thumbnail smaller than 2 MB.');
    $bytes=file_get_contents($file['tmp_name']);$size=@getimagesizefromstring($bytes);
    if(!$size || !in_array($size['mime'],['image/jpeg','image/png','image/webp'],true)
        || $size[0]>2048 || $size[1]>2048 || $size[0]*$size[1]>4194304)
        wall_fail(422,'Use a PNG, JPEG or WebP up to 2048 × 2048 pixels.');
    $source=@imagecreatefromstring($bytes);
    if(!$source) wall_fail(422,'That image could not be read. Try a different thumbnail.');
    if($size['mime']==='image/jpeg' && function_exists('exif_read_data')) {
        $exif=@exif_read_data($file['tmp_name']);$orientation=(int)($exif['Orientation']??1);
        if(in_array($orientation,[2,4,5,7],true))imageflip($source,IMG_FLIP_HORIZONTAL);
        $angle=match($orientation){3,4=>180,5,6=>-90,7,8=>90,default=>0};
        if($angle){$turned=imagerotate($source,$angle,0);imagedestroy($source);$source=$turned;}
    }
    $width=imagesx($source);$height=imagesy($source);$crop=min($width,$height);
    $thumb=imagecreatetruecolor(128,128);imagefill($thumb,0,0,imagecolorallocate($thumb,213,232,161));
    imagecopyresampled($thumb,$source,0,0,intdiv($width-$crop,2),intdiv($height-$crop,2),128,128,$crop,$crop);
    ob_start();imagepng($thumb,null,7);$png=ob_get_clean();imagedestroy($source);imagedestroy($thumb);
    if(strlen($png)>100000)wall_fail(422,'That thumbnail is too complex. Please try a smaller image.');
    return $png;
}
function wall_origin(): void {
    $origin=$_SERVER['HTTP_ORIGIN']??'';
    $allowed=['https://buttholechopper.com','https://www.buttholechopper.com'];
    if(wall_local())$allowed[]='http://'.($_SERVER['HTTP_HOST']??'');
    if(!in_array($origin,$allowed,true))wall_fail(403,'Please post using the comment form on this page.');
    wall_session();
    if(!is_string($_POST['csrf']??null) || !hash_equals($_SESSION['csrf'],$_POST['csrf']))
        wall_fail(403,'Your form expired. Reload the human check and try again.');
}
function wall_handle(): never {
    $action=$_GET['action']??'list';$method=$_SERVER['REQUEST_METHOD'];
    if(!is_string($action))wall_fail(400,'Invalid request.');
    if($method==='GET' && $action==='list') {
        $before=filter_var($_GET['before']??PHP_INT_MAX,FILTER_VALIDATE_INT,['options'=>['min_range'=>1]]);
        if($before===false)wall_fail(400,'Invalid page.');
        $result=wall_query('SELECT id,name,body,created_at,(avatar IS NOT NULL) AS has_avatar
            FROM comments WHERE reviewed=1 AND id<:before ORDER BY id DESC LIMIT 21',['before'=>$before]);
        $rows=[];while($row=$result->fetchArray(SQLITE3_ASSOC)){$row['has_avatar']=(bool)$row['has_avatar'];$rows[]=$row;}
        $more=count($rows)>20;if($more)array_pop($rows);
        wall_json(['comments'=>$rows,'total'=>(int)wall_db()->querySingle('SELECT count(*) FROM comments WHERE reviewed=1'),
            'next_before'=>$more?end($rows)['id']:null]);
    }
    if($method==='GET' && $action==='avatar') {
        $id=filter_var($_GET['id']??0,FILTER_VALIDATE_INT,['options'=>['min_range'=>1]]);
        if(!$id)wall_fail(404,'Thumbnail not found.');
        $row=wall_query('SELECT avatar FROM comments WHERE id=:id AND reviewed=1',['id'=>$id])->fetchArray(SQLITE3_ASSOC);
        if(!$row || $row['avatar']===null)wall_fail(404,'Thumbnail not found.');
        header('Content-Type: image/png');header('Cache-Control: no-store');
        header('Content-Disposition: inline; filename="profile-'.$id.'.png"');
        echo $row['avatar'];exit;
    }
    if($method==='GET' && $action==='challenge') {
        wall_limit('challenge',wall_actor(),600,60);wall_session();
        while(count($_SESSION['challenges'])>=3)array_shift($_SESSION['challenges']);
        $nonce=bin2hex(random_bytes(16));$code='';for($i=0;$i<6;$i++)$code.=(string)random_int(0,9);
        $_SESSION['challenges'][$nonce]=['code'=>$code,'created'=>time()];
        wall_json(['csrf'=>$_SESSION['csrf'],'nonce'=>$nonce]);
    }
    if($method==='GET' && in_array($action,['image','audio'],true)) {
        $challenge=wall_challenge(is_string($_GET['nonce']??null)?$_GET['nonce']:'');
        if($action==='image')wall_image($challenge['code']);else wall_audio($challenge['code']);
    }
    if($method!=='POST') { header('Allow: GET, POST'); wall_fail(405,'Method not supported.'); }
    if((int)($_SERVER['CONTENT_LENGTH']??0)>2300000)wall_fail(413,'The upload is too large. Maximum thumbnail size is 2 MB.');
    wall_limit('attempt',wall_actor(),600,20);wall_origin();
    if($action==='delete') {
        $id=filter_var($_POST['id']??0,FILTER_VALIDATE_INT,['options'=>['min_range'=>1]]);
        $token=$_POST['delete_token']??'';
        if(!$id || !is_string($token) || !preg_match('/^[a-f0-9]{64}$/D',$token))wall_fail(403,'You can only delete your own comments.');
        $row=wall_query('SELECT delete_hash FROM comments WHERE id=:id',['id'=>$id])->fetchArray(SQLITE3_ASSOC);
        if(!$row || !hash_equals($row['delete_hash'],hash('sha256',$token)))wall_fail(403,'You can only delete your own comments.');
        wall_query('DELETE FROM comments WHERE id=:id',['id'=>$id]);wall_json(['deleted'=>true]);
    }
    if($action!=='post')wall_fail(400,'Invalid request.');
    $nonce=is_string($_POST['nonce']??null)?$_POST['nonce']:'';
    $challenge=wall_challenge($nonce);unset($_SESSION['challenges'][$nonce]);
    $answer=$_POST['human_code']??'';$trap=$_POST['website']??'';
    if(!is_string($answer)||!is_string($trap)||$trap!=='' || time()-$challenge['created']<2
        || !hash_equals($challenge['code'],preg_replace('/\s/','',$answer)))
        wall_fail(422,'The human check did not match. Try the new code below.');
    $name=$_POST['name']??'';$body=$_POST['body']??'';
    if(!is_string($name)||!is_string($body)||!mb_check_encoding($name,'UTF-8')||!mb_check_encoding($body,'UTF-8'))wall_fail(422,'Please enter a name and comment.');
    $name=trim(preg_replace('/[\x00-\x1F\x7F]/u',' ',$name));
    $body=trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u','',str_replace("\r\n","\n",$body)));
    if(mb_strlen($name)<1||mb_strlen($name)>40||mb_strlen($body)<1||mb_strlen($body)>1500)
        wall_fail(422,'Use a name up to 40 characters and a comment up to 1,500 characters.');
    $avatar=wall_avatar();$actor=wall_actor();$now=time();
    $token=bin2hex(random_bytes(32));$fingerprint=hash('sha256',$name."\0".$body);
    $db=wall_db();$db->exec('BEGIN IMMEDIATE');
    try {
        $recent=(int)wall_query('SELECT count(*) AS n FROM comments WHERE author_key=:actor AND created_at>:cutoff',
            ['actor'=>$actor,'cutoff'=>$now-600])->fetchArray(SQLITE3_ASSOC)['n'];
        $daily=(int)wall_query('SELECT count(*) AS n FROM comments WHERE author_key=:actor AND created_at>:cutoff',
            ['actor'=>$actor,'cutoff'=>$now-86400])->fetchArray(SQLITE3_ASSOC)['n'];
        if($recent>=5||$daily>=30)wall_fail(429,'You have posted a few comments recently. Please come back in a little while.');
        if((int)$db->querySingle('SELECT count(*) FROM comments')>=10000)wall_fail(503,'The wall is full for now. Please try again later.');
        $duplicate=wall_query('SELECT id FROM comments WHERE author_key=:actor AND fingerprint=:fingerprint AND created_at>:cutoff',
            ['actor'=>$actor,'fingerprint'=>$fingerprint,'cutoff'=>$now-60])->fetchArray(SQLITE3_ASSOC);
        if($duplicate)wall_fail(409,'That comment was already posted.');
        $stmt=$db->prepare('INSERT INTO comments(name,body,created_at,avatar,delete_hash,author_key,fingerprint)
            VALUES(:name,:body,:now,:avatar,:hash,:actor,:fingerprint)');
        foreach(['name'=>$name,'body'=>$body,'hash'=>hash('sha256',$token),'actor'=>$actor,'fingerprint'=>$fingerprint] as $key=>$value)$stmt->bindValue(':'.$key,$value,SQLITE3_TEXT);
        $stmt->bindValue(':now',$now,SQLITE3_INTEGER);$stmt->bindValue(':avatar',$avatar,$avatar===null?SQLITE3_NULL:SQLITE3_BLOB);
        $stmt->execute();$id=$db->lastInsertRowID();$db->exec('COMMIT');
    } catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
    wall_json(['id'=>$id,'delete_token'=>$token],201);
}
if(!defined('GAYBOY_COMMENTS_LIBRARY_ONLY')) {
    try { wall_handle(); }
    catch(WallError $e){wall_json(['error'=>$e->getMessage()],$e->status);}
    catch(Throwable $e){error_log('GAYBOY comments: '.$e->getMessage());wall_json(['error'=>'Comments are temporarily unavailable. Please try again shortly.'],503);}
}
