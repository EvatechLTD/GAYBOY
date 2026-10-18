<?php
// CLI-only moderation. This file is never placed in the web document root.
declare(strict_types=1);
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
define('GAYBOY_COMMENTS_LIBRARY_ONLY',true);require __DIR__.'/app.php';
$action=$argv[1]??'list';
if($action==='list-beats') {
    if(!wall_db()->querySingle("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='beats'"))exit;
    $result=wall_query('SELECT id,name,title,created_at FROM beats ORDER BY created_at DESC LIMIT 50');
    while($row=$result->fetchArray(SQLITE3_ASSOC))echo json_encode($row,JSON_UNESCAPED_UNICODE)."\n";
    exit;
}
if($action==='delete-beat' && preg_match('/^[a-f0-9]{24}$/D',$argv[2]??'')) {
    wall_query('DELETE FROM beats WHERE id=:id',['id'=>$argv[2]]);echo json_encode(['deleted'=>wall_db()->changes()])."\n";exit;
}
if($action==='delete' && ctype_digit($argv[2]??'')){
    wall_query('DELETE FROM comments WHERE id=:id',['id'=>(int)$argv[2]]);
    echo json_encode(['deleted'=>wall_db()->changes()])."\n";
} elseif($action==='list') {
    $result=wall_query('SELECT id,name,body,created_at FROM comments ORDER BY id DESC LIMIT 50');
    while($row=$result->fetchArray(SQLITE3_ASSOC))echo json_encode($row,JSON_UNESCAPED_UNICODE)."\n";
} else {fwrite(STDERR,"Usage: php admin.php list | delete ID\n");exit(1);}
