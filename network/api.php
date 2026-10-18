<?php
declare(strict_types=1);
ini_set('display_errors','0');
set_exception_handler(function(Throwable $e): never {error_log('Y2KCRISIS: '.$e->getMessage());http_response_code(500);echo json_encode(['error'=>'The connection hit a snag. Please try again.']);exit;});
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
session_name('Y2KCRISIS');
session_set_cookie_params(['httponly'=>true,'secure'=>!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS']!=='off','samesite'=>'Strict','path'=>'/']);
session_start();
$_SESSION['csrf'] ??= bin2hex(random_bytes(24));
function fail(string $message,int $status=422): never {http_response_code($status);echo json_encode(['error'=>$message]);exit;}
function out(mixed $data): never {echo json_encode($data,JSON_INVALID_UTF8_SUBSTITUTE);exit;}
$home=getenv('Y2KCRISIS_DATA');
if (!$home) fail('Set Y2KCRISIS_DATA to a private directory outside the document root.',503);
if(!is_dir($home)) mkdir($home,0700,true);
$realHome=realpath($home);$docRoot=realpath($_SERVER['DOCUMENT_ROOT']??__DIR__);
if(!$realHome||($docRoot&&str_starts_with(strtolower(str_replace('\\','/',$realHome)).'/',strtolower(str_replace('\\','/',$docRoot)).'/')))fail('Database storage must be outside the document root.',503);
$db=new SQLite3($home.'/network.sqlite');$db->enableExceptions(true);$db->busyTimeout(5000);$db->exec('PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;');
$db->exec("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,handle TEXT UNIQUE COLLATE NOCASE,password TEXT,bio TEXT DEFAULT '',color TEXT DEFAULT '#baff37',wallpaper TEXT DEFAULT 'grid',status TEXT DEFAULT 'available',away TEXT DEFAULT '',bathroom INTEGER DEFAULT 1,tag TEXT DEFAULT '',blocks TEXT DEFAULT '[]',created INTEGER);
CREATE TABLE IF NOT EXISTS pins(id INTEGER PRIMARY KEY,owner INTEGER REFERENCES users(id),creator INTEGER REFERENCES users(id),name TEXT,art TEXT,history TEXT);
CREATE TABLE IF NOT EXISTS awards(user INTEGER REFERENCES users(id),name TEXT,PRIMARY KEY(user,name));
CREATE TABLE IF NOT EXISTS marks(id INTEGER PRIMARY KEY,owner INTEGER REFERENCES users(id),author INTEGER REFERENCES users(id),art TEXT,body TEXT,font TEXT,x INTEGER,y INTEGER,created INTEGER);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,author INTEGER REFERENCES users(id),recipient INTEGER REFERENCES users(id),room TEXT,body TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY,sender INTEGER REFERENCES users(id),recipient INTEGER REFERENCES users(id),offered INTEGER REFERENCES pins(id),wanted INTEGER REFERENCES pins(id),state TEXT DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS blocks(owner INTEGER REFERENCES users(id),target INTEGER REFERENCES users(id),PRIMARY KEY(owner,target));
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,author INTEGER,kind TEXT,target INTEGER,reason TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS limits(bucket TEXT PRIMARY KEY,n INTEGER);");
function q(string $sql,array $args=[]): SQLite3Result|bool {global $db;$s=$db->prepare($sql);foreach($args as $k=>$v)$s->bindValue($k+1,$v,$v===null?SQLITE3_NULL:(is_int($v)?SQLITE3_INTEGER:SQLITE3_TEXT));return $s->execute();}
function rows(string $sql,array $args=[]): array {$r=q($sql,$args);$a=[];while($v=$r->fetchArray(SQLITE3_ASSOC))$a[]=$v;return $a;}
function user(int $id): array {return rows('SELECT id,handle,bio,color,wallpaper,status,away,bathroom,tag,blocks,settings,updated,seen,visits FROM users WHERE id=?',[$id])[0]??[];}
function blocked(int $a,int $b): bool{return !!rows('SELECT 1 FROM blocks WHERE (owner=? AND target=?) OR (owner=? AND target=?)',[$a,$b,$b,$a]);}
function art(string $value): string {if(!preg_match('#^data:image/png;base64,([A-Za-z0-9+/=]+)$#',$value,$m))fail('Use a PNG from the paint editor.');$raw=base64_decode($m[1],true);if(!$raw || strlen($raw)>120000)fail('Artwork is too large.');$info=@getimagesizefromstring($raw);if(!$info||$info[0]!==128||$info[1]!==128||$info[2]!==IMAGETYPE_PNG)fail('Artwork must be a 128 × 128 PNG.');return $value;}
require __DIR__.'/schema.php';
$a=$_GET['action']??'session';$me=(int)($_SESSION['uid']??0);$p=[];
if($me&&(int)($_SESSION['auth_version']??0)!==(int)(rows('SELECT auth_version FROM users WHERE id=?',[$me])[0]['auth_version']??-1)){unset($_SESSION['uid']);$me=0;}
if($_SERVER['REQUEST_METHOD']==='POST'){
 if((int)($_SERVER['CONTENT_LENGTH']??0)>3500000)fail('Request too large.',413);
 $p=json_decode(file_get_contents('php://input'),true)??[];
 if(!hash_equals($_SESSION['csrf'],$_SERVER['HTTP_X_CSRF_TOKEN']??''))fail('Refresh the page and try again.',403);
 $bucket=hash('sha256',($_SERVER['REMOTE_ADDR']??'local').':'.$a.':'.floor(time()/60));
 q('INSERT INTO limits(bucket,n) VALUES(?,1) ON CONFLICT(bucket) DO UPDATE SET n=n+1',[$bucket]);
 if(random_int(1,100)===1)q('DELETE FROM limits WHERE rowid NOT IN (SELECT rowid FROM limits ORDER BY rowid DESC LIMIT 10000)');
 if(rows('SELECT n FROM limits WHERE bucket=?',[$bucket])[0]['n']>(in_array($a,['register','login','recover'],true)?10:60))fail('Take a breather. Try again in a minute.',429);
 if($a==='recover'){
  $u=rows('SELECT id,recovery FROM users WHERE handle=?',[text($p['handle']??'',20)])[0]??[];
  if(!$u||!$u['recovery']||!password_verify(text($p['code']??'',200),$u['recovery']))fail('Handle or recovery code is incorrect.',401);
  $pw=$p['password']??'';if(!is_string($pw)||strlen($pw)<10||strlen($pw)>200)fail('Choose a password of 10–200 characters.');
  q('UPDATE users SET password=?,recovery=NULL,auth_version=auth_version+1 WHERE id=? AND recovery=?',[password_hash($pw,PASSWORD_DEFAULT),(int)$u['id'],$u['recovery']]);if($db->changes()!==1)fail('That recovery code has already been used.',401);out(['ok'=>true]);
 }
 if(in_array($a,['login','register'],true)){
  $h=trim($p['handle']??'');$pw=$p['password']??'';
  if($a==='register'){
   if(!preg_match('/^[a-zA-Z0-9_]{3,20}$/',$h)||strlen($pw)<10||strlen($pw)>200)fail('Use a 3–20 character handle (letters, numbers, underscores) and a 10–200 character password.');
   if(in_array(strtolower($h),['gayboy','y2kcrisis','admin','moderator','system'],true))fail('That handle is reserved.');
   if(rows('SELECT id FROM users WHERE handle=?',[$h]))fail('That handle is taken.');
   q('INSERT INTO users(handle,password,created) VALUES(?,?,?)',[$h,password_hash($pw,PASSWORD_DEFAULT),time()]);$me=(int)$db->lastInsertRowID();
   foreach(['MIDNIGHT BUG','NO SIGNAL','YEAR 00'] as $name)q('INSERT INTO pins(owner,creator,name,art,history) VALUES(?,?,?,?,?)',[$me,$me,$name,'',json_encode(['Issued to @'.$h])]);
  }else{$u=rows('SELECT * FROM users WHERE handle=?',[$h])[0]??[];if(!$u||!password_verify($pw,$u['password']))fail('Handle or password is incorrect.',401);$me=(int)$u['id'];}
  session_regenerate_id(true);$_SESSION['uid']=$me;$_SESSION['auth_version']=(int)rows('SELECT auth_version FROM users WHERE id=?',[$me])[0]['auth_version'];out(['user'=>user($me),'csrf'=>$_SESSION['csrf']]);
 }
 if(!$me)fail('Sign in first.',401);
 require __DIR__.'/actions.php';
 if($a==='logout'){$_SESSION=[];session_regenerate_id(true);out(['ok'=>true]);}
 if($a==='profile'){
  $bio=mb_substr(trim($p['bio']??''),0,600);$color=$p['color']??'';if(!preg_match('/^#[a-f0-9]{6}$/i',$color))fail('Choose a color.');
  $blocks=$p['blocks']??[];if(!is_array($blocks)||count($blocks)>12)fail('Your homepage has room for 12 blocks.');
  $clean=[];foreach($blocks as $b){$type=$b['type']??'';$v=mb_substr(trim($b['value']??''),0,2000);if(!in_array($type,['text','youtube','soundcloud','link'],true))fail('Unknown block.');if($type!=='text'&&(!filter_var($v,FILTER_VALIDATE_URL)||parse_url($v,PHP_URL_SCHEME)!=='https'))fail('Use an HTTPS link.');$clean[]=['type'=>$type,'value'=>$v];}
  q('UPDATE users SET bio=?,color=?,wallpaper=?,status=?,away=?,bathroom=?,blocks=? WHERE id=?',[$bio,$color,in_array($p['wallpaper']??'',['grid','stars','plain'])?$p['wallpaper']:'grid',in_array($p['status']??'',['available','away','busy','invisible'])?$p['status']:'away',mb_substr($p['away']??'',0,160),!empty($p['bathroom'])?1:0,json_encode($clean),$me]);out(['ok'=>true]);
 }
 if($a==='tag'){q('UPDATE users SET tag=? WHERE id=?',[art($p['art']??''),$me]);out(['ok'=>true]);}
 if($a==='mint'){
  $u=user($me);if(!$u['bio']||!$u['tag']||$u['blocks']==='[]')fail('Finish your bio, add a homepage block, and make your tag to unlock a pin.');
  $image=art($p['art']??'');$name=mb_substr(trim($p['name']??''),0,40);if(!$name)fail('Name your pin.');
  $db->exec('BEGIN IMMEDIATE');if(rows('SELECT 1 FROM awards WHERE user=? AND name=?',[$me,'made-my-place'])){$db->exec('ROLLBACK');fail('You already used this achievement’s creation token.');}
  q('INSERT INTO awards VALUES(?,?)',[$me,'made-my-place']);q('INSERT INTO pins(owner,creator,name,art,history) VALUES(?,?,?,?,?)',[$me,$me,$name,$image,json_encode(['Created by @'.$u['handle']])]);$db->exec('COMMIT');out(['ok'=>true]);
 }
 if($a==='mark'){
  $target=(int)($p['owner']??0);$u=user($target);if(!$u||!$u['bathroom']||blocked($me,$target))fail('This bathroom is closed.',403);
  $body=mb_substr(trim($p['body']??''),0,160);$image=$body?'':user($me)['tag'];if(!$body&&!$image)fail('Make a tag first.');
  if(count(rows('SELECT id FROM marks WHERE owner=?',[$target]))>=100)fail('This wall is full. Its owner can remove marks to make space.');
  q('INSERT INTO marks(owner,author,art,body,font,x,y,created) VALUES(?,?,?,?,?,?,?,?)',[$target,$me,$image,$body,in_array($p['font']??'',['pixel','graffiti','ransom','bubble'])?$p['font']:'graffiti',max(0,min(80,(int)($p['x']??20))),max(0,min(75,(int)($p['y']??20))),time()]);out(['ok'=>true]);
 }
 if($a==='remove-mark'){q('DELETE FROM marks WHERE id=? AND (owner=? OR author=?)',[(int)$p['id'],$me,$me]);out(['ok'=>true]);}
 if($a==='send'){
  $body=mb_substr(trim($p['body']??''),0,1000);$room=$p['room']??'';$to=(int)($p['recipient']??0);if(!$body)fail('Write a message.');
  if($room){if(!in_array($room,['lobby','music','late-night','under-construction']))fail('Unknown room.');$to=null;}elseif(!$to||$to===$me||!user($to)||blocked($me,$to))fail('Cannot send this message.',403);
  q('INSERT INTO messages(author,recipient,room,body,created) VALUES(?,?,?,?,?)',[$me,$to,$room,$body,time()]);out(['ok'=>true]);
 }
 if($a==='give'||$a==='trade'){
  $to=(int)($p['recipient']??0);$pin=(int)($p['pin']??0);$wanted=(int)($p['wanted']??0);if(!$to||$to===$me||!user($to)||blocked($me,$to))fail('Choose another member.');
  $db->exec('BEGIN IMMEDIATE');$item=rows('SELECT * FROM pins WHERE id=? AND owner=?',[$pin,$me])[0]??[];if(!$item){$db->exec('ROLLBACK');fail('You do not own that pin.');}
  if($a==='give'){$history=json_decode($item['history'],true);$history[]='Given by @'.user($me)['handle'].' to @'.user($to)['handle'];q('UPDATE pins SET owner=?,history=? WHERE id=?',[$to,json_encode($history),$pin]);q("UPDATE trades SET state='cancelled' WHERE (offered=? OR wanted=?) AND state='pending'",[$pin,$pin]);}
  else{if(!rows('SELECT id FROM pins WHERE id=? AND owner=?',[$wanted,$to])){$db->exec('ROLLBACK');fail('That pin is no longer available.');}q('INSERT INTO trades(sender,recipient,offered,wanted) VALUES(?,?,?,?)',[$me,$to,$pin,$wanted]);}
  $db->exec('COMMIT');out(['ok'=>true]);
 }
 if($a==='trade-answer'){
  $db->exec('BEGIN IMMEDIATE');$t=rows("SELECT * FROM trades WHERE id=? AND recipient=? AND state='pending'",[(int)$p['id'],$me])[0]??[];if(!$t){$db->exec('ROLLBACK');fail('Trade is no longer pending.');}
  if(!empty($p['accept'])){if(blocked((int)$t['sender'],$me)){$db->exec('ROLLBACK');fail('Trade unavailable.');}foreach([[$t['offered'],$t['sender']],[$t['wanted'],$me]] as [$id,$owner])if(!rows('SELECT id FROM pins WHERE id=? AND owner=?',[(int)$id,(int)$owner])){$db->exec('ROLLBACK');fail('A pin has moved. This trade cannot complete.');}
   foreach([[$t['offered'],$me],[$t['wanted'],$t['sender']]] as [$id,$owner]){$pin=rows('SELECT * FROM pins WHERE id=?',[(int)$id])[0];$history=json_decode($pin['history'],true);$history[]='Traded to @'.user((int)$owner)['handle'];q('UPDATE pins SET owner=?,history=? WHERE id=?',[(int)$owner,json_encode($history),(int)$id]);}
   q("UPDATE trades SET state='cancelled' WHERE state='pending' AND (offered IN (?,?) OR wanted IN (?,?))",[(int)$t['offered'],(int)$t['wanted'],(int)$t['offered'],(int)$t['wanted']]);
  }q('UPDATE trades SET state=? WHERE id=?',[!empty($p['accept'])?'accepted':'declined',(int)$t['id']]);$db->exec('COMMIT');out(['ok'=>true]);
 }
 if($a==='block'){$target=(int)$p['target'];if($target===$me||!user($target))fail('Choose another member.');q('INSERT OR IGNORE INTO blocks VALUES(?,?)',[$me,$target]);out(['ok'=>true]);}
 if($a==='unblock'){q('DELETE FROM blocks WHERE owner=? AND target=?',[$me,(int)$p['target']]);out(['ok'=>true]);}
 if($a==='report'){$reason=mb_substr(trim($p['reason']??''),0,1000);if(!$reason)fail('Describe the issue.');q('INSERT INTO reports(author,kind,target,reason,created) VALUES(?,?,?,?,?)',[$me,mb_substr($p['kind']??'member',0,30),(int)$p['target'],$reason,time()]);out(['ok'=>true]);}
 fail('Unknown action.',404);
}
require __DIR__.'/queries.php';
if($a==='session')out(['user'=>$me?user($me):null,'csrf'=>$_SESSION['csrf']]);
if($a==='members')out(rows("SELECT id,handle,bio,CASE WHEN status='invisible' THEN 'away' ELSE status END AS status FROM users ORDER BY id DESC LIMIT 200"));
if($a==='page'){
 $id=(int)($_GET['id']??$me);$u=user($id);if(!$u||($me&&blocked($me,$id)))fail('Page unavailable.',404);if($u['status']==='invisible')$u['status']='away';
 $marks=$u['bathroom']?rows('SELECT m.*,u.handle FROM marks m JOIN users u ON u.id=m.author WHERE m.owner=? ORDER BY m.id',[$id]):[];
 if($me)$marks=array_values(array_filter($marks,fn($m)=>!blocked($me,(int)$m['author'])));
 out(['user'=>$u,'pins'=>rows('SELECT * FROM pins WHERE owner=?',[$id]),'marks'=>$marks]);
}
if(!$me)fail('Sign in first.',401);
if($a==='messages'){$room=$_GET['room']??'';$to=(int)($_GET['recipient']??0);if($room){if(!in_array($room,['lobby','music','late-night','under-construction']))fail('Unknown room.');$r=rows('SELECT m.*,u.handle FROM messages m JOIN users u ON u.id=m.author WHERE m.room=? ORDER BY m.id DESC LIMIT 80',[$room]);}else{$r=rows("SELECT m.*,u.handle FROM messages m JOIN users u ON u.id=m.author WHERE room='' AND ((author=? AND recipient=?) OR (author=? AND recipient=?)) ORDER BY m.id DESC LIMIT 80",[$me,$to,$to,$me]);}out(array_values(array_filter(array_reverse($r),fn($m)=>!blocked($me,(int)$m['author']))));}
if($a==='inventory')out(['pins'=>rows('SELECT * FROM pins WHERE owner=?',[$me]),'trades'=>rows("SELECT t.*,p.name offered_name,w.name wanted_name,u.handle FROM trades t JOIN pins p ON p.id=t.offered JOIN pins w ON w.id=t.wanted JOIN users u ON u.id=t.sender WHERE t.recipient=? AND t.state='pending'",[$me]),'awards'=>rows('SELECT name FROM awards WHERE user=?',[$me]),'blocked'=>rows('SELECT u.id,u.handle FROM blocks b JOIN users u ON u.id=b.target WHERE b.owner=?',[$me])]);
fail('Unknown action.',404);
