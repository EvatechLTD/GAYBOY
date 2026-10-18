<?php
if(!isset($db)){http_response_code(404);exit;}
$db->exec('BEGIN IMMEDIATE');
// Additive migrations preserve the first launch's accounts, pins and conversations.
$columns=array_column(rows('PRAGMA table_info(users)'),'name');
foreach(['settings'=>"TEXT DEFAULT '{}'",'updated'=>'INTEGER DEFAULT 0','seen'=>'INTEGER DEFAULT 0','visits'=>'INTEGER DEFAULT 0','recovery'=>'TEXT DEFAULT NULL','auth_version'=>'INTEGER DEFAULT 0'] as $name=>$type){
    if(!in_array($name,$columns,true))$db->exec("ALTER TABLE users ADD COLUMN $name $type");
}
$columns=array_column(rows('PRAGMA table_info(marks)'),'name');
foreach(['rotation'=>'INTEGER DEFAULT -8','approved'=>'INTEGER DEFAULT 1','archived'=>'INTEGER DEFAULT 0'] as $name=>$type){
    if(!in_array($name,$columns,true))$db->exec("ALTER TABLE marks ADD COLUMN $name $type");
}
$db->exec("CREATE TABLE IF NOT EXISTS pages(id INTEGER PRIMARY KEY,owner INTEGER REFERENCES users(id),slug TEXT,title TEXT,settings TEXT,blocks TEXT,updated INTEGER,UNIQUE(owner,slug));
CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,owner INTEGER,page TEXT,payload TEXT,created INTEGER);
CREATE TABLE IF NOT EXISTS friends(lo INTEGER REFERENCES users(id),hi INTEGER REFERENCES users(id),requester INTEGER,state TEXT DEFAULT 'pending',PRIMARY KEY(lo,hi));
CREATE TABLE IF NOT EXISTS guestbook(id INTEGER PRIMARY KEY,owner INTEGER REFERENCES users(id),author INTEGER REFERENCES users(id),body TEXT,art TEXT DEFAULT '',approved INTEGER DEFAULT 1,created INTEGER);
CREATE TABLE IF NOT EXISTS postcards(id INTEGER PRIMARY KEY,author INTEGER REFERENCES users(id),recipient INTEGER REFERENCES users(id),body TEXT,art TEXT,bg TEXT,displayed INTEGER DEFAULT 0,created INTEGER);
CREATE TABLE IF NOT EXISTS rooms(slug TEXT PRIMARY KEY,owner INTEGER REFERENCES users(id),title TEXT,topic TEXT DEFAULT '',color TEXT DEFAULT '#baff37',capacity INTEGER DEFAULT 30,privacy TEXT DEFAULT 'public',history INTEGER DEFAULT 1,media TEXT DEFAULT '',updated INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS room_people(room TEXT REFERENCES rooms(slug),user INTEGER REFERENCES users(id),role TEXT DEFAULT 'member',banned INTEGER DEFAULT 0,seen INTEGER DEFAULT 0,PRIMARY KEY(room,user));
CREATE TABLE IF NOT EXISTS rings(slug TEXT PRIMARY KEY,owner INTEGER REFERENCES users(id),title TEXT,description TEXT);
CREATE TABLE IF NOT EXISTS ring_members(ring TEXT REFERENCES rings(slug),user INTEGER REFERENCES users(id),PRIMARY KEY(ring,user));
CREATE TABLE IF NOT EXISTS bulletins(id INTEGER PRIMARY KEY,author INTEGER REFERENCES users(id),body TEXT,reply INTEGER DEFAULT NULL,created INTEGER);
CREATE TABLE IF NOT EXISTS beat_tracks(id TEXT PRIMARY KEY,author INTEGER REFERENCES users(id),title TEXT,snapshot TEXT,sha TEXT,created INTEGER);
CREATE INDEX IF NOT EXISTS message_room ON messages(room,id);
CREATE INDEX IF NOT EXISTS message_dm ON messages(author,recipient,id);
CREATE INDEX IF NOT EXISTS marks_owner ON marks(owner,id);
CREATE INDEX IF NOT EXISTS guestbook_owner ON guestbook(owner,id);
CREATE INDEX IF NOT EXISTS page_owner ON pages(owner);
CREATE INDEX IF NOT EXISTS revision_owner ON revisions(owner,page,id);");
$roomColumns=array_column(rows('PRAGMA table_info(rooms)'),'name');
if(!in_array('wallpaper',$roomColumns,true))$db->exec("ALTER TABLE rooms ADD COLUMN wallpaper TEXT DEFAULT ''");
foreach(['lobby'=>'The Lobby','music'=>'Music Exchange','late-night'=>'Late Night','under-construction'=>'Under Construction'] as $slug=>$title){
    q('INSERT OR IGNORE INTO rooms(slug,title,topic) VALUES(?,?,?)',[$slug,$title,'Make yourself comfortable. Leave room for other people.']);
}
if(is_file(__DIR__.'/gayboy.json')&&!rows('SELECT id FROM users WHERE handle=?',['GAYBOY'])){
    $g=json_decode(file_get_contents(__DIR__.'/gayboy.json'),true)['user'];
    q('INSERT OR IGNORE INTO users(handle,password,bio,color,wallpaper,status,away,bathroom,blocks,settings,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',[
        'GAYBOY',password_hash(bin2hex(random_bytes(40)),PASSWORD_DEFAULT),$g['bio'],$g['color'],$g['wallpaper'],'available',$g['away'],1,$g['blocks'],$g['settings'],time(),time()]);
}
$db->exec('COMMIT');

function settings(array $u): array {return json_decode($u['settings']??'{}',true)?:[];}
function text(mixed $v,int $max=600): string {return mb_substr(trim(is_string($v)?$v:''),0,$max);}
function color(mixed $v,string $default='#baff37'): string {return is_string($v)&&preg_match('/^#[a-f0-9]{6}$/i',$v)?$v:$default;}
function https_url(mixed $v,bool $empty=true): string {
    $v=text($v,2000);if(!$v&&$empty)return '';
    if(preg_match('#^/?api\.php\?action=asset&id=[a-f0-9]{64}$#',$v))return $v;
    if(str_starts_with($v,'apps/gayboy/')&&!str_contains($v,'..')&&preg_match('#^[a-zA-Z0-9/._-]+$#',$v))return $v;
    if(!filter_var($v,FILTER_VALIDATE_URL)||strtolower(parse_url($v,PHP_URL_SCHEME)??'')!=='https'||parse_url($v,PHP_URL_USER)||parse_url($v,PHP_URL_PASS))fail('Use an HTTPS URL or an uploaded image.');
    return $v;
}
function clean_settings(array $s): array {
    $c=[];
    foreach(['displayName'=>60,'pronouns'=>60,'title'=>100,'pretitle'=>160,'tagline'=>240,'welcome'=>300,'ticker'=>600,'quote'=>240,'mood'=>100,'location'=>100,'interests'=>600,'footer'=>300,'updateNote'=>240,'wallpaperImage'=>2000,'avatar'=>2000,'soundtrack'=>2000,'constructionText'=>100,'cursorImage'=>2000,'headerImage'=>2000,'logoImage'=>2000] as $k=>$max)$c[$k]=text($s[$k]??'',$max);
    foreach(['avatar','wallpaperImage','cursorImage','headerImage','logoImage'] as $k)$c[$k]=https_url($c[$k]);
    foreach(['background'=>'#190029','panel'=>'#210331','ink'=>'#fff0ff','accent'=>'#d5ff39','secondary'=>'#ff81d9','link'=>'#88f9ff','header'=>'#440d69'] as $k=>$d)$c[$k]=color($s[$k]??null,$d);
    foreach(['theme'=>['gayboy','acid','bubblegum','terminal','paper'],'pattern'=>['stars','grid','checker','stripes','plain'],'layout'=>['left','right','single'],'font'=>['verdana','pixel','mono','serif','bubble','marker'],'headingFont'=>['impact','pixel','marker','bubble','serif'],'border'=>['ridge','solid','dashed','double','none'],'cursor'=>['auto','crosshair','cell','help','pointer'],'bathroomMode'=>['everyone','friends','approve'],'guestbookMode'=>['everyone','friends','approve','off'],'dmPolicy'=>['everyone','friends','off'],'neighborhood'=>['music','art','night-owls','games','internet','other']] as $k=>$values)$c[$k]=in_array($s[$k]??'', $values,true)?$s[$k]:$values[0];
    foreach(['glitter','tickerMotion','construction','visitorCounter','showPins','showFriends','showGuestbook','showBathroom','showStatus','showContact','showInterests','sounds','saveDMs','gridEditor','jacketOnly','shadows'] as $k)$c[$k]=array_key_exists($k,$s)?(bool)$s[$k]:in_array($k,['showPins','showFriends','showGuestbook','showBathroom','showStatus','showContact','showInterests','saveDMs','tickerMotion','shadows'],true);
    $c['width']=max(700,min(1400,(int)($s['width']??1080)));$c['sidebarWidth']=max(180,min(350,(int)($s['sidebarWidth']??250)));$c['radius']=max(0,min(30,(int)($s['radius']??0)));$c['headerSize']=max(36,min(140,(int)($s['headerSize']??100)));
    $c['fontSize']=max(11,min(22,(int)($s['fontSize']??14)));$c['lineHeight']=max(1.2,min(2.2,(float)($s['lineHeight']??1.6)));$c['spacing']=max(10,min(40,(int)($s['spacing']??25)));$c['borderWidth']=max(0,min(6,(int)($s['borderWidth']??2)));$c['titleTilt']=max(-10,min(10,(int)($s['titleTilt']??-3)));
    $c['featuredFriends']=array_slice(array_values(array_unique(array_map('intval',is_array($s['featuredFriends']??null)?$s['featuredFriends']:[]))),0,8);
    $c['badges']=array_map(fn($v)=>text($v,100),array_slice(is_array($s['badges']??null)?$s['badges']:[],0,12));
    $c['links']=[];foreach(array_slice(is_array($s['links']??null)?$s['links']:[],0,16) as $v)$c['links'][]=['label'=>text($v['label']??'',80),'url'=>https_url($v['url']??'')];
    $c['decorations']=[];foreach(array_slice(is_array($s['decorations']??null)?$s['decorations']:[],0,40) as $v)$c['decorations'][]=['kind'=>in_array($v['kind']??'',['pin','sticker','stamp'],true)?$v['kind']:'stamp','pin'=>(int)($v['pin']??0),'art'=>($v['kind']??'')==='sticker'?art($v['art']??''):'','text'=>text($v['text']??'',80),'x'=>max(0,min(92,(float)($v['x']??10))),'y'=>max(0,min(90,(float)($v['y']??10))),'rotation'=>max(-180,min(180,(int)($v['rotation']??0))),'size'=>max(32,min(160,(int)($v['size']??80)))];
    return $c;
}
function clean_blocks(array $blocks): array {
    if(count($blocks)>12)fail('Your page has room for twelve blocks. Make another page for more.');$clean=[];
    foreach($blocks as $b){
        $type=$b['type']??'text';if(in_array($type,['youtube','soundcloud','spotify','vimeo','bandcamp','mixcloud','twitch'],true))$type='media';
        if($type==='link'){$b['items']=[['label'=>$b['caption']??$b['value']??'Link','url'=>$b['value']??'']];$type='links';}
        if(!in_array($type,['text','media','image','gallery','links','list','download','badges','divider','status','collection','app','room','guestbook','friends','pins','bathroom','webring'],true))fail('Unknown homepage block.');
        $v=text($b['value']??'',6000);
        if(in_array($type,['image','download'],true)&&$v)$v=https_url($v,false);
        $item=['id'=>preg_match('/^[a-zA-Z0-9_-]{1,60}$/',$b['id']??'')?$b['id']:bin2hex(random_bytes(5)),'type'=>$type,'title'=>text($b['title']??'',100),'value'=>$v,'caption'=>text($b['caption']??'',300),'column'=>($b['column']??'')==='sidebar'?'sidebar':'main','style'=>in_array($b['style']??'',['plain','loud','note','sticker','terminal'],true)?$b['style']:'plain','align'=>in_array($b['align']??'',['left','center','right'],true)?$b['align']:'left','items'=>[]];
        foreach(array_slice(is_array($b['items']??null)?$b['items']:[],0,24) as $it)$item['items'][]=['label'=>text($it['label']??'',160),'url'=>https_url($it['url']??''),'image'=>https_url($it['image']??''),'text'=>text($it['text']??'',400)];
        if($type==='app'&&$v!=='gayboy')fail('Choose an app from the app drawer.');
        $clean[]=$item;
    }return $clean;
}
function are_friends(int $a,int $b): bool {return $a===$b||!!rows("SELECT 1 FROM friends WHERE lo=? AND hi=? AND state='accepted'",[min($a,$b),max($a,$b)]);}
function member(int|string $who): array {$found=rows('SELECT id FROM users WHERE handle=?',[(string)$who])[0]??null;return $found?user((int)$found['id']):(ctype_digit((string)$who)?user((int)$who):[]);}
function available_awards(int $uid): array {
    $u=user($uid);$s=settings($u);$b=json_decode($u['blocks'],true)?:[];$k=array_unique(array_column($b,'type'));
    return ['made-my-place'=>!!($u['bio']&&$u['tag']&&count($b)),'personal-style'=>!!(($s['avatar']??'')&&($s['title']??'')&&($s['quote']??'')),'curator'=>count($k)>=3,'storyteller'=>mb_strlen($u['bio'])>=100&&!!rows('SELECT 1 FROM pages WHERE owner=?',[$uid])];
}
function room_access(string $slug,int $uid,bool $join=false): array {
    $r=rows('SELECT * FROM rooms WHERE slug=?',[$slug])[0]??[];if(!$r)fail('Room not found.',404);
    if($r['owner']&&blocked($uid,(int)$r['owner']))fail('Room unavailable.',403);
    $p=rows('SELECT * FROM room_people WHERE room=? AND user=?',[$slug,$uid])[0]??[];
    if($p['banned']??false)fail('You cannot enter this room.',403);
    if($r['privacy']==='friends'&&$r['owner']&&!are_friends($uid,(int)$r['owner']))fail('This room is for the host’s buddies.',403);
    if($join&&(!$p||$p['seen']<time()-90)&&count(rows('SELECT 1 FROM room_people WHERE room=? AND seen>? AND banned=0',[$slug,time()-90]))>=$r['capacity'])fail('This room is full. Try again later.');
    return $r;
}
