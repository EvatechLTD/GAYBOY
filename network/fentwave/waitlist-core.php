<?php
declare(strict_types=1);
// Contact data and keys live outside the document root. Never log contact payloads.
if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) { http_response_code(404); exit; }
umask(0077);

function fw_home(): string {
    $base = getenv('Y2KCRISIS_DATA');
    if (!$base || !is_dir($base)) throw new RuntimeException('Private storage unavailable');
    $base = realpath($base);
    $doc = realpath(!empty($_SERVER['DOCUMENT_ROOT']) ? $_SERVER['DOCUMENT_ROOT'] : dirname(__DIR__));
    if (!$base || ($doc && str_starts_with(str_replace('\\', '/', $base).'/', str_replace('\\', '/', $doc).'/'))) {
        throw new RuntimeException('Private storage must be outside public files');
    }
    $home = $base.'/fentwave-waitlist';
    if (!is_dir($home) && !mkdir($home, 0700)) throw new RuntimeException('Private storage unavailable');
    if (is_link($home)) throw new RuntimeException('Unexpected storage path');
    chmod($home, 0700);
    return $home;
}

function fw_keys(): string {
    static $keys;
    if (isset($keys)) return $keys;
    if (!extension_loaded('openssl') || !in_array('aes-256-gcm', openssl_get_cipher_methods(), true)) {
        throw new RuntimeException('Contact encryption unavailable');
    }
    $path = fw_home().'/contact.keys';
    if (is_link($path)) throw new RuntimeException('Unexpected key path');
    if (!file_exists($path)) {
        if (file_exists(fw_home().'/contacts.sqlite')) throw new RuntimeException('Existing contacts require their original key');
        $stream = @fopen($path, 'x+b');
        if ($stream) {
            try { if (fwrite($stream, random_bytes(64)) !== 64) throw new RuntimeException('Key creation failed'); }
            finally { fclose($stream); }
            chmod($path, 0600);
        }
    }
    $keys = file_get_contents($path);
    if (!is_string($keys) || strlen($keys) !== 64) throw new RuntimeException('Contact key unavailable');
    chmod($path, 0600);
    return $keys;
}

function fw_db(): SQLite3 {
    static $db;
    if (isset($db)) return $db;
    fw_keys(); // Fail closed before accepting any contacts.
    $path = fw_home().'/contacts.sqlite';
    if (is_link($path)) throw new RuntimeException('Unexpected database path');
    $db = new SQLite3($path);
    $db->enableExceptions(true);
    $db->busyTimeout(5000);
    $db->exec('PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;');
    $db->exec("CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY, email_hmac TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
        created INTEGER NOT NULL, consent_version TEXT NOT NULL,
        notification TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
        accepted_at INTEGER, claimed_at INTEGER
    ); CREATE TABLE IF NOT EXISTS limits (bucket TEXT PRIMARY KEY, n INTEGER NOT NULL, expires INTEGER NOT NULL);");
    chmod($path, 0600);
    return $db;
}

function fw_query(string $sql, array $values = []): SQLite3Result|bool {
    $s = fw_db()->prepare($sql);
    foreach ($values as $i => $v) $s->bindValue($i + 1, $v, is_int($v) ? SQLITE3_INTEGER : ($v === null ? SQLITE3_NULL : SQLITE3_TEXT));
    return $s->execute();
}

function fw_encrypt(array $contact): string {
    $nonce = random_bytes(12); $tag = '';
    $ciphertext = openssl_encrypt(json_encode($contact, JSON_THROW_ON_ERROR), 'aes-256-gcm', substr(fw_keys(), 0, 32), OPENSSL_RAW_DATA, $nonce, $tag, 'fentwave-contact:v1', 16);
    if ($ciphertext === false) throw new RuntimeException('Contact encryption failed');
    return base64_encode($nonce.$tag.$ciphertext);
}

function fw_decrypt(string $payload): array {
    $raw = base64_decode($payload, true);
    if ($raw === false || strlen($raw) < 29) throw new RuntimeException('Invalid contact record');
    $json = openssl_decrypt(substr($raw, 28), 'aes-256-gcm', substr(fw_keys(), 0, 32), OPENSSL_RAW_DATA, substr($raw, 0, 12), substr($raw, 12, 16), 'fentwave-contact:v1');
    if ($json === false) throw new RuntimeException('Contact authentication failed');
    return json_decode($json, true, 8, JSON_THROW_ON_ERROR);
}

function fw_mail(array $contact, bool $test = false): bool {
    $to = 'evatechusa@gmail.com';
    $subject = $test ? 'FENTWAVE waitlist: delivery test' : 'FENTWAVE waitlist: new signup';
    $body = ($test ? "This is a deployment test, not a waitlist signup.\n\n" : "A new person joined the FENTWAVE development / launch waitlist.\n\n")
        .'Name: '.($contact['name'] ?: '(not provided)')."\nEmail: ".$contact['email']."\n"
        .'Joined (UTC): '.gmdate('Y-m-d H:i:s', (int)$contact['created'])."\n"
        ."Page: https://y2kcrisis.com/fentwave/\n\n"
        ."Consent: FENTWAVE development and launch updates only. No payment or preorder.\n"
        ."Contact details are private; do not publish this notification.\n";
    if (getenv('FENTWAVE_TEST_MODE') === '1') {
        $spool = getenv('FENTWAVE_MAIL_SPOOL');
        if (!$spool || getenv('FENTWAVE_TEST_MAIL_FAIL') === '1') return false;
        return file_put_contents($spool, json_encode(['to' => $to, 'subject' => $subject, 'body' => $body])."\n", FILE_APPEND | LOCK_EX) !== false;
    }
    return mail($to, $subject, $body, [
        'From' => 'FENTWAVE <waitlist@y2kcrisis.com>',
        'Reply-To' => $contact['email'],
        'MIME-Version' => '1.0',
        'Content-Type' => 'text/plain; charset=UTF-8',
        'X-FENTWAVE-Notification' => $test ? 'test' : 'signup',
    ], '-fwaitlist@y2kcrisis.com');
}

function fw_notify(string $id): bool {
    fw_query("UPDATE contacts SET notification='sending', attempts=attempts+1, claimed_at=? WHERE id=? AND notification='pending'", [time(), $id]);
    if (fw_db()->changes() !== 1) return false;
    try {
        $row = fw_query('SELECT payload FROM contacts WHERE id=?', [$id])->fetchArray(SQLITE3_ASSOC);
        $accepted = fw_mail(fw_decrypt($row['payload']));
        fw_query('UPDATE contacts SET notification=?, accepted_at=? WHERE id=?', [$accepted ? 'accepted' : 'pending', $accepted ? time() : null, $id]);
        return $accepted;
    } catch (Throwable $e) {
        fw_query("UPDATE contacts SET notification='pending' WHERE id=?", [$id]);
        error_log('FENTWAVE: notification delivery deferred');
        return false;
    }
}
