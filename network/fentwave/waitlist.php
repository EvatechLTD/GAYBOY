<?php
declare(strict_types=1);
ini_set('display_errors', '0');
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
function respond(array $body, int $status = 200): never { http_response_code($status); echo json_encode($body); exit; }
set_exception_handler(function (Throwable $e): never {
    error_log('FENTWAVE: waitlist request failed');
    respond(['error' => 'The waitlist is temporarily unavailable. Please try again shortly.'], 503);
});
$test = getenv('FENTWAVE_TEST_MODE') === '1';
$secure = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
if (!$secure && !$test) respond(['error' => 'Please use the secure HTTPS page.'], 426);
$method = $_SERVER['REQUEST_METHOD'] ?? '';
if (!in_array($method, ['GET', 'POST'], true)) { header('Allow: GET, POST'); respond(['error' => 'Method not allowed.'], 405); }
session_name('FENTWAVE_WAITLIST');
session_set_cookie_params(['httponly' => true, 'secure' => $secure, 'samesite' => 'Strict', 'path' => '/fentwave/']);
session_start();
if (empty($_SESSION['token']) || (int)($_SESSION['issued'] ?? 0) < time() - 7200) {
    $_SESSION['token'] = bin2hex(random_bytes(32)); $_SESSION['issued'] = time();
}
require __DIR__.'/waitlist-core.php';
if ($method === 'GET') {
    fw_db();
    respond(['csrf' => $_SESSION['token']]);
}
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$allowed = ['https://y2kcrisis.com', 'https://www.y2kcrisis.com'];
if ($test) $allowed[] = 'http://'.($_SERVER['HTTP_HOST'] ?? '');
if (!in_array($origin, $allowed, true)) respond(['error' => 'Please submit from the FENTWAVE page.'], 403);
if (!str_starts_with(strtolower($_SERVER['CONTENT_TYPE'] ?? ''), 'application/json')) respond(['error' => 'Use the signup form.'], 415);
if ((int)($_SERVER['CONTENT_LENGTH'] ?? 0) > 4096) respond(['error' => 'The form is too large.'], 413);
$raw = file_get_contents('php://input', false, null, 0, 4097);
if ($raw === false || strlen($raw) > 4096) respond(['error' => 'The form is too large.'], 413);
try { $p = json_decode($raw, true, 8, JSON_THROW_ON_ERROR); }
catch (JsonException $e) { respond(['error' => 'Please check the form and try again.'], 400); }
if (!is_array($p) || !is_string($p['csrf'] ?? null) || !hash_equals($_SESSION['token'], $p['csrf'])) respond(['error' => 'Please refresh the page and try again.'], 403);
if (!empty($p['website'])) respond(['ok' => true]); // Honeypot: no record or notification.
if (($p['consent'] ?? false) !== true) respond(['error' => 'Please agree to receive FENTWAVE updates.'], 422);
if (!is_string($p['email'] ?? null) || !is_string($p['name'] ?? '')) respond(['error' => 'Please check your contact details.'], 422);
$email = strtolower(trim($p['email'])); $name = trim($p['name'] ?? '');
if (strlen($email) > 254 || preg_match('/[\r\n\x00]/', $email) || !filter_var($email, FILTER_VALIDATE_EMAIL)) respond(['error' => 'Enter a valid email address.'], 422);
if (!mb_check_encoding($name, 'UTF-8') || mb_strlen($name) > 80 || preg_match('/[\x00-\x1F\x7F]/u', $name)) respond(['error' => 'Use a name under 80 characters, without line breaks.'], 422);
$digest = hash_hmac('sha256', $email, substr(fw_keys(), 32));
$ip = hash_hmac('sha256', $_SERVER['REMOTE_ADDR'] ?? 'unknown', substr(fw_keys(), 32));
$bucket = $ip.':'.intdiv(time(), 3600);
$db = fw_db();
$db->exec('BEGIN IMMEDIATE');
try {
    fw_query('DELETE FROM limits WHERE expires < ?', [time()]);
    fw_query('INSERT OR IGNORE INTO limits VALUES (?,0,?)', [$bucket, time() + 7200]);
    $n = fw_query('SELECT n FROM limits WHERE bucket=?', [$bucket])->fetchArray(SQLITE3_ASSOC)['n'];
    if ($n >= 8) { $db->exec('ROLLBACK'); header('Retry-After: 3600'); respond(['error' => 'Too many attempts. Please try again later.'], 429); }
    fw_query('UPDATE limits SET n=n+1 WHERE bucket=?', [$bucket]);
    $id = bin2hex(random_bytes(16)); $created = time();
    $contact = ['name' => $name, 'email' => $email, 'created' => $created];
    fw_query('INSERT OR IGNORE INTO contacts(id,email_hmac,payload,created,consent_version) VALUES(?,?,?,?,?)', [$id, $digest, fw_encrypt($contact), $created, 'fentwave-updates-v1']);
    $new = $db->changes() === 1;
    $db->exec('COMMIT');
} catch (Throwable $e) { $db->exec('ROLLBACK'); throw $e; }
session_write_close();
if ($new) fw_notify($id);
respond(['ok' => true]); // Never expose contact existence, records or mail-server state.
