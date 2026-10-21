<?php
if(!isset($db)){http_response_code(404);exit;}
if($a==='music'){
    $id=$_GET['id']??'';$format=$_GET['format']??'';
    if(!is_string($id)||!is_string($format)||!preg_match('/^[a-f0-9]{64}$/',$id)||!rows('SELECT id FROM music_files WHERE id=? AND format=? LIMIT 1',[$id,$format])||!is_file($home.'/music/'.$id))fail('Music file not found.',404);
    $path=$home.'/music/'.$id;
    header('Content-Type: application/octet-stream');header('X-Content-Type-Options: nosniff');
    header('Content-Disposition: attachment; filename="soundtrack.'.$format.'"');
    header('Cache-Control: public, max-age=31536000, immutable');header('Content-Length: '.filesize($path));
    session_write_close();readfile($path);exit;
}
if($a==='asset'){
    $id=$_GET['id']??'';if(!preg_match('/^[a-f0-9]{64}$/',$id)||!is_file($home.'/uploads/'.$id))fail('Image not found.',404);$path=$home.'/uploads/'.$id;$info=getimagesize($path);
    header('Content-Type: '.$info['mime']);header('X-Content-Type-Options: nosniff');header('Cache-Control: public, max-age=31536000, immutable');header('Content-Length: '.filesize($path));readfile($path);exit;
}
if($a==='beats'){
    $tracks=rows('SELECT b.id,b.title,b.created,b.author,u.handle FROM beat_tracks b JOIN users u ON u.id=b.author ORDER BY b.created DESC,b.id DESC LIMIT 40');
    out($me?array_values(array_filter($tracks,fn($b)=>!blocked($me,(int)$b['author']))):$tracks);
}
if($a==='beat'){
    $id=text($_GET['id']??'',24);$beat=rows('SELECT b.*,u.handle FROM beat_tracks b JOIN users u ON u.id=b.author WHERE b.id=?',[$id])[0]??null;if(!$beat||($me&&blocked($me,(int)$beat['author'])))fail('Beat not found.',404);out($beat);
}
function public_user(array $u,int $viewer): array {
    if($u['id']!==$viewer){if($u['status']==='invisible')$u['status']='away';unset($u['seen']);}
    return $u;
}
function friend_list(int $uid): array {
    $f=rows("SELECT u.id,u.handle,u.bio,u.status,u.away,u.seen,u.settings,f.requester,f.state FROM friends f JOIN users u ON u.id=CASE WHEN f.lo=? THEN f.hi ELSE f.lo END WHERE (f.lo=? OR f.hi=?)",[$uid,$uid,$uid]);
    foreach($f as &$u){if($u['status']==='invisible'||$u['seen']<time()-120)$u['status']='away';unset($u['seen']);}$f=array_filter($f,fn($u)=>!blocked($uid,(int)$u['id']));return array_values($f);
}
if($a==='members'){
    $list=rows('SELECT id,handle,bio,status,away,seen,updated,settings FROM users ORDER BY updated DESC,id DESC LIMIT 200');
    if($me)$list=array_values(array_filter($list,fn($u)=>!blocked($me,(int)$u['id'])));
    foreach($list as &$u){if($u['status']==='invisible'||$u['seen']<time()-120)$u['status']='away';unset($u['seen']);}
    out($list);
}
if($a==='featured'){
    if(($_GET['slug']??'')!=='gayboy')fail('Page not found.',404);$a='page';$_GET['handle']='GAYBOY';unset($_GET['slug']);
}
if($a==='page'){
    $u=isset($_GET['handle'])?member((string)$_GET['handle']):user((int)($_GET['id']??$me));if(!$u||($me&&blocked($me,(int)$u['id'])))fail('Page unavailable.',404);$uid=(int)$u['id'];$own=$uid===$me;$s=settings($u);$sub=text($_GET['slug']??'',40);
    if($sub){$extra=rows('SELECT * FROM pages WHERE owner=? AND slug=?',[$uid,$sub])[0]??null;if(!$extra)fail('This page does not exist.',404);$u['settings']=$extra['settings'];$u['blocks']=$extra['blocks'];$u['pageTitle']=$extra['title'];$u['pageSlug']=$sub;}
    if(!$own&&!empty($s['visitorCounter'])&&empty($_SESSION['visits'][$uid])){q('UPDATE users SET visits=visits+1 WHERE id=?',[$uid]);$_SESSION['visits'][$uid]=true;$u['visits']++;}
    $marks=$u['bathroom']?rows('SELECT m.*,u.handle FROM marks m JOIN users u ON u.id=m.author WHERE m.owner=? AND (m.approved=1 OR m.owner=? OR m.author=?) AND (m.archived=0 OR m.owner=?) ORDER BY m.id',[$uid,$me,$me,$me]):[];
    $notes=($s['guestbookMode']??'everyone')!=='off'?rows('SELECT g.*,u.handle,u.settings FROM guestbook g JOIN users u ON u.id=g.author WHERE g.owner=? AND (g.approved=1 OR g.owner=? OR g.author=?) ORDER BY g.id DESC LIMIT 50',[$uid,$me,$me]):[];
    if($me){$marks=array_values(array_filter($marks,fn($m)=>!blocked($me,(int)$m['author'])));$notes=array_values(array_filter($notes,fn($m)=>!blocked($me,(int)$m['author'])));}
    $buddies=array_values(array_filter(friend_list($uid),fn($u)=>$u['state']==='accepted'));
    out(['user'=>public_user($u,$me),'pins'=>array_values(array_filter(rows('SELECT * FROM pins WHERE owner=?',[$uid]),fn($pin)=>$own||empty($s['jacketOnly'])||in_array($pin['id'],array_column($s['decorations']??[],'pin')))),'marks'=>$marks,'guestbook'=>$notes,'friends'=>$buddies,'pages'=>rows('SELECT slug,title FROM pages WHERE owner=? ORDER BY id',[$uid]),'postcards'=>rows('SELECT p.*,u.handle FROM postcards p JOIN users u ON u.id=p.author WHERE recipient=? AND displayed=1 ORDER BY p.id',[$uid]),'rings'=>rows('SELECT r.* FROM rings r JOIN ring_members m ON m.ring=r.slug WHERE m.user=?',[$uid])]);
}
if($a==='rings'){
    $r=rows('SELECT * FROM rings ORDER BY title');foreach($r as &$ring)$ring['members']=rows('SELECT u.id,u.handle FROM ring_members m JOIN users u ON u.id=m.user WHERE m.ring=? ORDER BY u.id',[$ring['slug']]);out($r);
}
if($a==='board'){
    $r=rows('SELECT b.*,u.handle FROM bulletins b JOIN users u ON u.id=b.author ORDER BY b.id DESC LIMIT 60');if($me)$r=array_values(array_filter($r,fn($b)=>!blocked($me,(int)$b['author'])));out($r);
}
if($a==='rooms'){
    $r=rows('SELECT r.*,(SELECT COUNT(*) FROM room_people p WHERE p.room=r.slug AND p.seen>? AND p.banned=0) AS present FROM rooms r ORDER BY r.owner IS NOT NULL,r.title',[time()-90]);
    out(array_values(array_filter($r,fn($r)=>!$r['owner']||($me&&!blocked($me,(int)$r['owner'])&&($r['privacy']==='public'||are_friends($me,(int)$r['owner']))))));
}
if(!$me)return;
if($a==='music-library')out(rows('SELECT id,format,name,size FROM music_files WHERE owner=? ORDER BY created DESC',[$me]));
if($a==='friends')out(friend_list($me));
if($a==='desk'){
    $friends=friend_list($me);out(['friends'=>$friends,'postcards'=>rows('SELECT p.*,u.handle FROM postcards p JOIN users u ON u.id=p.author WHERE p.recipient=? ORDER BY p.id DESC LIMIT 100',[$me]),'conversations'=>rows("SELECT u.id,u.handle,MAX(m.id) last_id FROM messages m JOIN users u ON u.id=CASE WHEN m.author=? THEN m.recipient ELSE m.author END WHERE m.room='' AND (m.author=? OR m.recipient=?) GROUP BY u.id ORDER BY last_id DESC LIMIT 40",[$me,$me,$me]),'pages'=>rows('SELECT * FROM pages WHERE owner=? ORDER BY id',[$me])]);
}
if($a==='revisions')out(rows('SELECT id,created FROM revisions WHERE owner=? AND page=? ORDER BY id DESC LIMIT 10',[$me,text($_GET['slug']??'',40)]));
if($a==='inventory'){
    out(['pins'=>rows('SELECT * FROM pins WHERE owner=?',[$me]),'trades'=>rows("SELECT t.*,p.name offered_name,w.name wanted_name,u.handle FROM trades t JOIN pins p ON p.id=t.offered JOIN pins w ON w.id=t.wanted JOIN users u ON u.id=t.sender WHERE t.recipient=? AND t.state='pending'",[$me]),'awards'=>rows('SELECT name FROM awards WHERE user=?',[$me]),'available'=>available_awards($me),'blocked'=>rows('SELECT u.id,u.handle FROM blocks b JOIN users u ON u.id=b.target WHERE b.owner=?',[$me])]);
}
if($a==='room'){
    $slug=text($_GET['room']??'',60);$r=room_access($slug,$me);$people=rows('SELECT u.id,u.handle,u.status,p.role,p.banned,p.seen FROM room_people p JOIN users u ON u.id=p.user WHERE room=? AND (p.seen>? OR p.banned=1)',[$slug,time()-90]);
    $mod=$r['owner']===$me||!!rows("SELECT 1 FROM room_people WHERE room=? AND user=? AND role='moderator'",[$slug,$me]);if(!$mod)$people=array_values(array_filter($people,fn($p)=>!$p['banned']));out(['room'=>$r,'people'=>$people,'moderator'=>$mod]);
}
if($a==='messages'){
    $slug=text($_GET['room']??'',60);$to=(int)($_GET['recipient']??0);$before=max(0,(int)($_GET['before']??0));
    if($slug){$r=room_access($slug,$me);$cutoff=$r['history']?0:(int)($_SESSION['roomStart'][$slug]??PHP_INT_MAX);
        $messages=rows('SELECT m.*,u.handle FROM messages m JOIN users u ON u.id=m.author WHERE room=? AND m.id>? AND (?=0 OR m.id<?) ORDER BY m.id DESC LIMIT 80',[$slug,$cutoff,$before,$before]);
    }else{
        if(blocked($me,$to))fail('Conversation unavailable.',403);
        $db->exec('CREATE TABLE IF NOT EXISTS dm_clear(owner INTEGER,target INTEGER,before_id INTEGER,PRIMARY KEY(owner,target))');$cut=(int)(rows('SELECT before_id FROM dm_clear WHERE owner=? AND target=?',[$me,$to])[0]['before_id']??0);
        if(!(settings(user($me))['saveDMs']??true)){$_SESSION['dmStart'][$to]??=(int)(rows('SELECT MAX(id) n FROM messages')[0]['n']??0);$cut=max($cut,(int)$_SESSION['dmStart'][$to]);}
        $messages=rows("SELECT m.*,u.handle FROM messages m JOIN users u ON u.id=m.author WHERE room='' AND ((author=? AND recipient=?) OR (author=? AND recipient=?)) AND m.id>? AND (?=0 OR m.id<?) ORDER BY m.id DESC LIMIT 80",[$me,$to,$to,$me,$cut,$before,$before]);
        $_SESSION['dmStart'][$to]??=(int)(rows('SELECT MAX(id) n FROM messages')[0]['n']??0);
    }
    out(array_values(array_filter(array_reverse($messages),fn($m)=>!blocked($me,(int)$m['author']))));
}
