<?php
if(!isset($db)){http_response_code(404);exit;}
// New authenticated mutations. Unhandled actions continue through the v1 API.
if($a==='upload'){
    $data=$p['data']??'';if(!is_string($data)||!preg_match('#^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)$#',$data,$m))fail('Choose a PNG, JPEG, GIF or WebP image.');
    $raw=base64_decode($m[2],true);$info=$raw?@getimagesizefromstring($raw):false;
    if(!$info||strlen($raw)>2400000||$info[0]>4096||$info[1]>4096||$info['mime']!==$m[1])fail('Images must be under 2.4 MB and 4096 × 4096 pixels.');
    $dir=$home.'/uploads';if(!is_dir($dir))mkdir($dir,0700,true);$id=hash('sha256',$raw);
    if(!is_file($dir.'/'.$id))file_put_contents($dir.'/'.$id,$raw,LOCK_EX);
    out(['url'=>'api.php?action=asset&id='.$id]);
}
if($a==='share-beat'){
    $title=text($p['title']??'',80);$encoded=$p['snapshot']??'';$bytes=is_string($encoded)?base64_decode($encoded,true):false;
    $metadata=json_decode(file_get_contents(__DIR__.'/apps/gayboy/emulator/tutorial-rom.json'),true);
    if(!$title||!$bytes||strlen($bytes)!==83512||substr($bytes,0,8)!=='GBBT0001'||bin2hex(substr($bytes,8,32))!==$metadata['sha256']||substr($bytes,-4)!=='BESS')fail('Capture a running beat from this version of GAYBOY.');
    if(count(rows('SELECT id FROM beat_tracks WHERE author=? AND created>?',[$me,time()-600]))>=3||count(rows('SELECT id FROM beat_tracks WHERE author=? AND created>?',[$me,time()-86400]))>=15)fail('A few beats at a time. Try again later.',429);
    if(count(rows('SELECT id FROM beat_tracks'))>=1000)fail('The beat shelf is full for now.',503);
    $sha=hash('sha256',$bytes);if(rows('SELECT id FROM beat_tracks WHERE author=? AND sha=? AND created>?',[$me,$sha,time()-60]))fail('You just shared this beat.',409);
    $id=bin2hex(random_bytes(12));q('INSERT INTO beat_tracks VALUES(?,?,?,?,?,?)',[$id,$me,$title,base64_encode($bytes),$sha,time()]);out(['id'=>$id]);
}
if($a==='delete-beat'){q('DELETE FROM beat_tracks WHERE id=? AND author=?',[text($p['id']??'',24),$me]);out(['ok'=>true]);}
if($a==='recovery-code'){
    $code=bin2hex(random_bytes(16));q('UPDATE users SET recovery=? WHERE id=?',[password_hash($code,PASSWORD_DEFAULT),$me]);out(['code'=>$code]);
}
if($a==='heartbeat'){
    q('UPDATE users SET seen=? WHERE id=?',[time(),$me]);
    if(!empty($p['room'])){$db->exec('BEGIN IMMEDIATE');room_access(text($p['room'],60),$me,true);if(!rows('SELECT 1 FROM room_people WHERE room=? AND user=?',[text($p['room'],60),$me]))fail('Enter the room first.',403);q('UPDATE room_people SET seen=? WHERE room=? AND user=?',[time(),text($p['room'],60),$me]);$db->exec('COMMIT');}
    out(['ok'=>true]);
}
if($a==='profile'||$a==='save-page'){
    $u=user($me);$slug=text($p['slug']??'',40);if($slug&&!preg_match('/^[a-z0-9][a-z0-9-]{0,39}$/',$slug))fail('Use letters, numbers and hyphens in the page address.');
    $old=$slug?(rows('SELECT * FROM pages WHERE owner=? AND slug=?',[$me,$slug])[0]??null):$u;
    if(!$old&&count(rows('SELECT 1 FROM pages WHERE owner=?',[$me]))>=8)fail('You have room for eight extra pages.');
    $s=clean_settings(is_array($p['settings']??null)?$p['settings']:settings($u));$blocks=clean_blocks(is_array($p['blocks']??null)?$p['blocks']:[]);
    $title=text($p['title']??$s['title'],100);$bio=text($p['bio']??$u['bio'],600);$accent=color($p['color']??$s['accent']);
    $db->exec('BEGIN IMMEDIATE');
    if($old){q('INSERT INTO revisions(owner,page,payload,created) VALUES(?,?,?,?)',[$me,$slug,json_encode($old),time()]);q('DELETE FROM revisions WHERE owner=? AND page=? AND id NOT IN (SELECT id FROM revisions WHERE owner=? AND page=? ORDER BY id DESC LIMIT 10)',[$me,$slug,$me,$slug]);}
    if($slug){q('INSERT INTO pages(owner,slug,title,settings,blocks,updated) VALUES(?,?,?,?,?,?) ON CONFLICT(owner,slug) DO UPDATE SET title=excluded.title,settings=excluded.settings,blocks=excluded.blocks,updated=excluded.updated',[$me,$slug,$title,json_encode($s),json_encode($blocks),time()]);}
    else{q('UPDATE users SET bio=?,color=?,wallpaper=?,status=?,away=?,bathroom=?,blocks=?,settings=?,updated=? WHERE id=?',[$bio,$accent,in_array($p['wallpaper']??$s['pattern'],['grid','stars','plain'])?($p['wallpaper']??$s['pattern']):'stars',in_array($p['status']??$u['status'],['available','away','busy','invisible'])?($p['status']??$u['status']):'away',text($p['away']??$u['away'],160),array_key_exists('bathroom',$p)?(int)(bool)$p['bathroom']:(int)$u['bathroom'],json_encode($blocks),json_encode($s),time(),$me]);}
    $db->exec('COMMIT');out(['ok'=>true]);
}
if($a==='delete-page'){
    $slug=text($p['slug']??'',40);if(!$slug)fail('Your main homepage cannot be deleted.');q('DELETE FROM pages WHERE owner=? AND slug=?',[$me,$slug]);out(['ok'=>true]);
}
if($a==='restore-page'){
    $r=rows('SELECT * FROM revisions WHERE id=? AND owner=?',[(int)($p['id']??0),$me])[0]??null;if(!$r)fail('Saved version not found.',404);$d=json_decode($r['payload'],true);
    if($r['page'])q('UPDATE pages SET title=?,settings=?,blocks=?,updated=? WHERE owner=? AND slug=?',[$d['title'],$d['settings'],$d['blocks'],time(),$me,$r['page']]);
    else q('UPDATE users SET settings=?,blocks=?,bio=?,color=?,wallpaper=?,status=?,away=?,bathroom=?,updated=? WHERE id=?',[$d['settings'],$d['blocks'],$d['bio'],$d['color'],$d['wallpaper'],$d['status'],$d['away'],(int)$d['bathroom'],time(),$me]);out(['ok'=>true]);
}
if($a==='friend'){
    $target=(int)($p['target']??0);if(!$target||$target===$me||!user($target)||blocked($me,$target))fail('This connection is unavailable.');
    $lo=min($me,$target);$hi=max($me,$target);$op=$p['op']??'request';$f=rows('SELECT * FROM friends WHERE lo=? AND hi=?',[$lo,$hi])[0]??null;
    if($op==='remove'||$op==='decline'){q('DELETE FROM friends WHERE lo=? AND hi=?',[$lo,$hi]);}
    elseif($op==='accept'){if(!$f||$f['requester']===$me||$f['state']!=='pending')fail('No incoming request.');q("UPDATE friends SET state='accepted' WHERE lo=? AND hi=?",[$lo,$hi]);}
    else{if($f)fail('You already have a connection or pending request.');q('INSERT INTO friends(lo,hi,requester) VALUES(?,?,?)',[$lo,$hi,$me]);}out(['ok'=>true]);
}
if($a==='guestbook'){
    $owner=(int)($p['owner']??0);$u=user($owner);if(!$u||blocked($owner,$me))fail('Guestbook unavailable.',403);$mode=settings($u)['guestbookMode']??'everyone';if($mode==='off'||($mode==='friends'&&!are_friends($owner,$me)))fail('This guestbook is closed to visitors.',403);
    $body=text($p['body']??'',1500);$image=!empty($p['art'])?art($p['art']):'';if(!$body&&!$image)fail('Leave a note or a doodle.');
    q('INSERT INTO guestbook(owner,author,body,art,approved,created) VALUES(?,?,?,?,?,?)',[$owner,$me,$body,$image,$mode==='approve'&&$me!==$owner?0:1,time()]);out(['ok'=>true,'pending'=>$mode==='approve'&&$me!==$owner]);
}
if(in_array($a,['moderate-note','moderate-mark'],true)){
    $table=$a==='moderate-note'?'guestbook':'marks';$id=(int)($p['id']??0);$item=rows("SELECT * FROM $table WHERE id=?",[$id])[0]??null;if(!$item||($item['owner']!==$me&&$item['author']!==$me))fail('You cannot change this contribution.',403);
    if(($p['op']??'')==='approve'){if($item['owner']!==$me)fail('Only the page owner can approve this.',403);q("UPDATE $table SET approved=1 WHERE id=?",[$id]);}
    elseif($table==='marks'&&($p['op']??'')==='archive'){if($item['owner']!==$me)fail('Only the page owner can archive this.',403);q('UPDATE marks SET archived=1 WHERE id=?',[$id]);}
    elseif($table==='marks'&&($p['op']??'')==='restore'){if($item['owner']!==$me)fail('Only the page owner can restore this.',403);q('UPDATE marks SET archived=0 WHERE id=?',[$id]);}
    else q("DELETE FROM $table WHERE id=?",[$id]);out(['ok'=>true]);
}
if($a==='mark'){
    $owner=(int)($p['owner']??0);$u=user($owner);if(!$u||!$u['bathroom']||blocked($me,$owner))fail('This bathroom is closed.',403);$mode=settings($u)['bathroomMode']??'everyone';if($mode==='friends'&&!are_friends($owner,$me))fail('This bathroom is for buddies.',403);
    $body=text($p['body']??'',160);$image=$body?'':user($me)['tag'];if(!$body&&!$image)fail('Make your tag first.');
    if(count(rows('SELECT id FROM marks WHERE owner=? AND archived=0',[$owner]))>=100)fail('The wall is full. Its owner can archive some marks.');
    q('INSERT INTO marks(owner,author,art,body,font,x,y,created,rotation,approved) VALUES(?,?,?,?,?,?,?,?,?,?)',[$owner,$me,$image,$body,in_array($p['font']??'',['pixel','graffiti','ransom','bubble'])?$p['font']:'graffiti',max(0,min(80,(int)($p['x']??20))),max(0,min(75,(int)($p['y']??20))),time(),max(-180,min(180,(int)($p['rotation']??-8))),$mode==='approve'&&$owner!==$me?0:1]);out(['ok'=>true,'pending'=>$mode==='approve'&&$owner!==$me]);
}
if($a==='postcard'){
    $to=(int)($p['recipient']??0);$u=user($to);if(!$u||$to===$me||blocked($me,$to))fail('Choose an available neighbor.');$mode=settings($u)['dmPolicy']??'everyone';if($mode==='off'||($mode==='friends'&&!are_friends($me,$to)))fail('This member only accepts postcards from buddies.',403);
    $body=text($p['body']??'',1000);if(!$body)fail('Write a little message.');q('INSERT INTO postcards(author,recipient,body,art,bg,created) VALUES(?,?,?,?,?,?)',[$me,$to,$body,user($me)['tag'],color($p['bg']??null,'#ff81d9'),time()]);out(['ok'=>true]);
}
if($a==='display-postcard'){q('UPDATE postcards SET displayed=? WHERE id=? AND recipient=?',[(int)!empty($p['displayed']),(int)($p['id']??0),$me]);out(['ok'=>true]);}
if($a==='mint'){
    $name=text($p['name']??'',40);$image=art($p['art']??'');if(!$name)fail('Name your pin.');$available=available_awards($me);$which=text($p['award']??'made-my-place',40);if(!($available[$which]??false))fail('Finish this achievement before creating its pin.');
    $count=max(1,min(3,(int)($p['edition']??1)));$db->exec('BEGIN IMMEDIATE');
    if(rows('SELECT 1 FROM awards WHERE user=? AND name=?',[$me,$which])){$db->exec('ROLLBACK');fail('This achievement’s creation token has already been used.');}
    q('INSERT INTO awards VALUES(?,?)',[$me,$which]);
    for($i=1;$i<=$count;$i++)q('INSERT INTO pins(owner,creator,name,art,history) VALUES(?,?,?,?,?)',[$me,$me,$name.($count>1?" · $i/$count":''),$image,json_encode(['Created by @'.user($me)['handle'],'Fixed edition of '.$count.'; achievement: '.$which])]);
    $db->exec('COMMIT');out(['ok'=>true]);
}
if($a==='room-save'){
    $slug=text($p['slug']??'',60);if(!$slug)$slug='room-'.bin2hex(random_bytes(5));if(!preg_match('/^[a-z0-9-]{3,60}$/',$slug))fail('Room addresses use lowercase letters, numbers and hyphens.');
    $r=rows('SELECT * FROM rooms WHERE slug=?',[$slug])[0]??null;
    if($r&&$r['owner']!==$me)fail('Only the host can decorate this room.',403);
    if(!$r&&count(rows('SELECT 1 FROM rooms WHERE owner=?',[$me]))>=5)fail('You can host five rooms.');
    $title=text($p['title']??'',80);if(!$title)fail('Name your room.');
    q('INSERT INTO rooms(slug,owner,title,topic,color,capacity,privacy,history,media,updated) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET title=excluded.title,topic=excluded.topic,color=excluded.color,capacity=excluded.capacity,privacy=excluded.privacy,history=excluded.history,media=excluded.media,updated=excluded.updated',[$slug,$me,$title,text($p['topic']??'',300),color($p['color']??null),max(2,min(50,(int)($p['capacity']??20))),($p['privacy']??'')==='friends'?'friends':'public',(int)(bool)($p['history']??true),text($p['media']??'',2000),time()]);
    q('UPDATE rooms SET wallpaper=? WHERE slug=?',[https_url($p['wallpaper']??''),$slug]);
    out(['slug'=>$slug]);
}
if($a==='room-join'){
    $db->exec('BEGIN IMMEDIATE');$slug=text($p['room']??'',60);$r=room_access($slug,$me,true);q("INSERT INTO room_people(room,user,role,seen) VALUES(?,?,?,?) ON CONFLICT(room,user) DO UPDATE SET seen=excluded.seen",[$slug,$me,$r['owner']===$me?'host':'member',time()]);
    $_SESSION['roomJoined'][$slug]??=time();$_SESSION['roomStart'][$slug]??=(int)(rows('SELECT MAX(id) n FROM messages WHERE room=?',[$slug])[0]['n']??0);$db->exec('COMMIT');out(['ok'=>true]);
}
if($a==='room-leave'){q('UPDATE room_people SET seen=0 WHERE room=? AND user=?',[text($p['room']??'',60),$me]);unset($_SESSION['roomJoined'][text($p['room']??'',60)],$_SESSION['roomStart'][text($p['room']??'',60)]);out(['ok'=>true]);}
if($a==='room-moderate'){
    $slug=text($p['room']??'',60);$r=room_access($slug,$me);$role=rows('SELECT role FROM room_people WHERE room=? AND user=?',[$slug,$me])[0]['role']??'member';
    if($r['owner']!==$me&&$role!=='moderator')fail('Only room hosts and moderators can do this.',403);
    $target=(int)($p['target']??0);if($target===$r['owner'])fail('The host cannot be removed.');$op=$p['op']??'';
    if($op==='delete-message')q('DELETE FROM messages WHERE id=? AND room=?',[(int)($p['id']??0),$slug]);
    elseif($op==='moderator'){if($r['owner']!==$me)fail('Only the host can assign moderators.',403);q("UPDATE room_people SET role='moderator' WHERE room=? AND user=?",[$slug,$target]);}
    elseif($op==='unban')q('UPDATE room_people SET banned=0 WHERE room=? AND user=?',[$slug,$target]);
    elseif($op==='ban')q("INSERT INTO room_people(room,user,banned) VALUES(?,?,1) ON CONFLICT(room,user) DO UPDATE SET banned=1,seen=0",[$slug,$target]);
    else fail('Choose a moderation action.');out(['ok'=>true]);
}
if($a==='send'){
    $body=text($p['body']??'',1000);if(!$body)fail('Write a message.');$slug=text($p['room']??'',60);$to=(int)($p['recipient']??0);
    if($slug){room_access($slug,$me);$rp=rows('SELECT seen FROM room_people WHERE room=? AND user=?',[$slug,$me])[0]??null;if(!$rp||$rp['seen']<time()-120)fail('Enter the room before sending.');$to=null;}
    else{$u=user($to);if(!$u||$to===$me||blocked($me,$to))fail('Cannot send this message.',403);$policy=settings($u)['dmPolicy']??'everyone';if($policy==='off'||($policy==='friends'&&!are_friends($me,$to)))fail('This member accepts messages from buddies only.',403);}
    q('INSERT INTO messages(author,recipient,room,body,created) VALUES(?,?,?,?,?)',[$me,$to,$slug,$body,time()]);out(['ok'=>true]);
}
if($a==='clear-dm'){
    // Clearing only hides history for this member; the other participant keeps theirs.
    $db->exec('CREATE TABLE IF NOT EXISTS dm_clear(owner INTEGER,target INTEGER,before_id INTEGER,PRIMARY KEY(owner,target))');
    $id=(int)(rows('SELECT MAX(id) n FROM messages')[0]['n']??0);q('INSERT INTO dm_clear VALUES(?,?,?) ON CONFLICT(owner,target) DO UPDATE SET before_id=excluded.before_id',[$me,(int)($p['target']??0),$id]);out(['ok'=>true]);
}
if($a==='ring-save'){
    $slug=text($p['slug']??'',40);if(!preg_match('/^[a-z0-9-]{3,40}$/',$slug))fail('Use a short lowercase name with hyphens for your ring.');$r=rows('SELECT * FROM rings WHERE slug=?',[$slug])[0]??null;if($r&&$r['owner']!==$me)fail('That ring name is taken.');
    $title=text($p['title']??'',80);if(!$title)fail('Name your webring.');q('INSERT INTO rings(slug,owner,title,description) VALUES(?,?,?,?) ON CONFLICT(slug) DO UPDATE SET title=excluded.title,description=excluded.description',[$slug,$me,$title,text($p['description']??'',400)]);q('INSERT OR IGNORE INTO ring_members VALUES(?,?)',[$slug,$me]);out(['ok'=>true]);
}
if($a==='ring-join'){
    $slug=text($p['ring']??'',40);if(!rows('SELECT 1 FROM rings WHERE slug=?',[$slug]))fail('Ring not found.');if(!empty($p['leave']))q('DELETE FROM ring_members WHERE ring=? AND user=?',[$slug,$me]);else q('INSERT OR IGNORE INTO ring_members VALUES(?,?)',[$slug,$me]);out(['ok'=>true]);
}
if($a==='bulletin'){
    $body=text($p['body']??'',600);if(!$body)fail('Write a status or answer.');$reply=(int)($p['reply']??0);if($reply&&!rows('SELECT 1 FROM bulletins WHERE id=?',[$reply]))fail('That conversation is gone.');q('INSERT INTO bulletins(author,body,reply,created) VALUES(?,?,?,?)',[$me,$body,$reply?:null,time()]);out(['ok'=>true]);
}
if($a==='delete-bulletin'){q('DELETE FROM bulletins WHERE id=? AND author=?',[(int)($p['id']??0),$me]);out(['ok'=>true]);}
