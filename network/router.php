<?php
// PHP's local development server needs the same clean homepage routes as Apache.
$path=parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH);
if(preg_match('#(?:^|/)\.#',$path)){http_response_code(404);exit;}
$headers=__DIR__.(str_starts_with($path,'/apps/gayboy/')?'/apps/gayboy/.htaccess':(str_starts_with($path,'/retro/')?'/retro/.htaccess':'/.htaccess'));
if(is_file($headers)&&preg_match('/Header always set Content-Security-Policy "([^"]+)"/',file_get_contents($headers),$m))header('Content-Security-Policy: '.$m[1]);
if(preg_match('#^/~gayboy(?:/([a-z0-9-]+))?/?$#i',$path,$m)){header('Location: /gayboy'.(!empty($m[1])?'/'.$m[1]:''),true,301);return true;}
if(strtolower($path)==='/gayboy/'){header('Location: /gayboy',true,301);return true;}
if(preg_match('#^/gameboy(?:/([a-z0-9-]+))?/?$#i',$path,$m)){header('Location: /gayboy'.(!empty($m[1])?'/'.$m[1]:''),true,301);return true;}
if(preg_match('#^/gayboy(?:/[a-z0-9-]+)?$#i',$path)){header('Content-Type: text/html; charset=utf-8');readfile(__DIR__.'/index.html');return true;}
if(preg_match('#^/~[A-Za-z0-9_]+(?:/[a-z0-9-]+)?/?$#',$path)){header('Content-Type: text/html; charset=utf-8');readfile(__DIR__.'/index.html');return true;}
return false;
