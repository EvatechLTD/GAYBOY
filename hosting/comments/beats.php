<?php
declare(strict_types=1);
// Versioned snapshots are stored as inert SQLite blobs outside the web root.
const BEAT_ROM = '622c70243cf4d4df0e17256f8ddedbbfdae4dd34cdb47e921465f99e4345bb88';
function beat_handle(): never {
    $db=wall_db();
    $db->exec('CREATE TABLE IF NOT EXISTS beats (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, title TEXT NOT NULL,
        created_at INTEGER NOT NULL, state BLOB NOT NULL, sha TEXT NOT NULL,
        delete_hash TEXT NOT NULL, author_key TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS beats_created ON beats(created_at DESC,id);
        CREATE INDEX IF NOT EXISTS beats_author ON beats(author_key,created_at);');
    $action=$_GET['action']??'list';$method=$_SERVER['REQUEST_METHOD'];
    if(!is_string($action))wall_fail(400,'Invalid beat request.');
    if($method==='GET' && $action==='list') {
        $offset=filter_var($_GET['offset']??0,FILTER_VALIDATE_INT,['options'=>['min_range'=>0,'max_range'=>1000]]);
        if($offset===false)wall_fail(400,'Invalid page.');
        $result=wall_query('SELECT id,name,title,created_at FROM beats ORDER BY created_at DESC,id DESC LIMIT 21 OFFSET :offset',['offset'=>$offset]);
        $rows=[];while($row=$result->fetchArray(SQLITE3_ASSOC))$rows[]=$row;
        $more=count($rows)>20;if($more)array_pop($rows);
        wall_json(['beats'=>$rows,'total'=>(int)$db->querySingle('SELECT count(*) FROM beats'),'next_offset'=>$more?$offset+20:null]);
    }
    if($method==='GET' && $action==='beat') {
        $id=$_GET['id']??'';
        if(!is_string($id)||!preg_match('/^[a-f0-9]{24}$/D',$id))wall_fail(404,'Beat not found.');
        $row=wall_query('SELECT id,name,title,created_at,state,sha FROM beats WHERE id=:id',['id'=>$id])->fetchArray(SQLITE3_ASSOC);
        if(!$row)wall_fail(404,'That beat is no longer on the wall.');
        $row['snapshot']=base64_encode($row['state']);$row['rom']=bin2hex(substr($row['state'],8,32));unset($row['state']);
        wall_json($row);
    }
    if($method==='GET' && in_array($action,['challenge','image','audio'],true))wall_handle();
    if($method!=='POST'){header('Allow: GET, POST');wall_fail(405,'Method not supported.');}
    if((int)($_SERVER['CONTENT_LENGTH']??0)>300000)wall_fail(413,'That beat is too large.');
    wall_limit('beat-attempt',wall_actor(),600,20);wall_origin();
    if($action==='delete') {
        wall_fail(403,'Only the site admin can delete shared beats.');
    }
    if($action!=='post')wall_fail(400,'Invalid beat request.');
    $nonce=is_string($_POST['nonce']??null)?$_POST['nonce']:'';
    $challenge=wall_challenge($nonce);unset($_SESSION['challenges'][$nonce]);
    $answer=$_POST['human_code']??'';$trap=$_POST['website']??'';
    if(!is_string($answer)||!is_string($trap)||$trap!==''||time()-$challenge['created']<2||!hash_equals($challenge['code'],preg_replace('/\s/','',$answer)))
        wall_fail(422,'The human check did not match. Get a new code and try again.');
    $name=$_POST['name']??'';$title=$_POST['title']??'';
    if(!is_string($name)||!is_string($title)||!mb_check_encoding($name,'UTF-8')||!mb_check_encoding($title,'UTF-8'))wall_fail(422,'Enter a name and beat title.');
    $name=trim(preg_replace('/[\x00-\x1F\x7F]/u',' ',$name));$title=trim(preg_replace('/[\x00-\x1F\x7F]/u',' ',$title));
    if(mb_strlen($name)<1||mb_strlen($name)>40||mb_strlen($title)<1||mb_strlen($title)>80)wall_fail(422,'Use a name up to 40 characters and a title up to 80.');
    $file=$_FILES['snapshot']??null;
    if(!$file||$file['error']!==UPLOAD_ERR_OK||$file['size']>262144||!is_uploaded_file($file['tmp_name']))wall_fail(422,'Capture your beat again and retry.');
    $bytes=file_get_contents($file['tmp_name']);
    if(strlen($bytes)!==83512||substr($bytes,0,8)!=='GBBT0001'||bin2hex(substr($bytes,8,32))!==BEAT_ROM||substr($bytes,-4)!=='BESS')wall_fail(422,'That beat does not match this version of GAYBOY.');
    $actor=wall_actor();$now=time();$sha=hash('sha256',$bytes);$id=bin2hex(random_bytes(12));$token=bin2hex(random_bytes(32));
    $db->exec('BEGIN IMMEDIATE');
    try {
        $recent=(int)wall_query('SELECT count(*) AS n FROM beats WHERE author_key=:actor AND created_at>:cutoff',['actor'=>$actor,'cutoff'=>$now-600])->fetchArray(SQLITE3_ASSOC)['n'];
        $daily=(int)wall_query('SELECT count(*) AS n FROM beats WHERE author_key=:actor AND created_at>:cutoff',['actor'=>$actor,'cutoff'=>$now-86400])->fetchArray(SQLITE3_ASSOC)['n'];
        if($recent>=3||$daily>=15)wall_fail(429,'You shared a few beats recently. Come back in a little while.');
        if((int)$db->querySingle('SELECT count(*) FROM beats')>=1000)wall_fail(503,'The beat wall is full for now.');
        $duplicate=wall_query('SELECT id FROM beats WHERE author_key=:actor AND sha=:sha AND created_at>:cutoff',['actor'=>$actor,'sha'=>$sha,'cutoff'=>$now-60])->fetchArray(SQLITE3_ASSOC);
        if($duplicate)wall_fail(409,'That beat was already shared.');
        $stmt=$db->prepare('INSERT INTO beats VALUES(:id,:name,:title,:now,:state,:sha,:hash,:actor)');
        foreach(['id'=>$id,'name'=>$name,'title'=>$title,'sha'=>$sha,'hash'=>hash('sha256',$token),'actor'=>$actor] as $k=>$v)$stmt->bindValue(':'.$k,$v,SQLITE3_TEXT);
        $stmt->bindValue(':now',$now,SQLITE3_INTEGER);$stmt->bindValue(':state',$bytes,SQLITE3_BLOB);$stmt->execute();$db->exec('COMMIT');
    } catch(Throwable $e){$db->exec('ROLLBACK');throw $e;}
    wall_json(['id'=>$id],201);
}
try{beat_handle();}
catch(WallError $e){wall_json(['error'=>$e->getMessage()],$e->status);}
catch(Throwable $e){error_log('GAYBOY beats: '.$e->getMessage());wall_json(['error'=>'The beat wall is temporarily unavailable. Please try again.'],503);}
