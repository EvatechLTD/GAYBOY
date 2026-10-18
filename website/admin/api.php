<?php
declare(strict_types=1);
$private = getenv('GAYBOY_COMMENTS_HOME') ?: '/home/centered/gayboy-comments-private';
define('GAYBOY_COMMENTS_LIBRARY_ONLY',true);
require $private.'/app.php';
require $private.'/admin-web.php';
