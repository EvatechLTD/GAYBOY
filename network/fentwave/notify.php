<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__.'/waitlist-core.php';
$mode = $argv[1] ?? '';
if ($mode === '--self-test') {
    $ok = fw_mail(['name' => 'FENTWAVE deployment check', 'email' => 'evatechusa@gmail.com', 'created' => time()], true);
    echo $ok ? "Test notification accepted by mail transport.\n" : "Test notification was not accepted.\n";
    exit($ok ? 0 : 1);
}
if ($mode !== '--process') { fwrite(STDERR, "Use --process or --self-test.\n"); exit(2); }
$rows = fw_query("SELECT id FROM contacts WHERE notification='pending' AND attempts<20 ORDER BY created LIMIT 10");
$ids = []; while ($row = $rows->fetchArray(SQLITE3_ASSOC)) $ids[] = $row['id'];
$accepted = 0; foreach ($ids as $id) if (fw_notify($id)) $accepted++;
echo 'Notifications accepted: '.$accepted.'; examined: '.count($ids)."\n";
