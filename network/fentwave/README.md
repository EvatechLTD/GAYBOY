# FENTWAVE homepage and private waitlist

Live: https://y2kcrisis.com/fentwave/ . Linked from the community navigation and https://y2kcrisis.com/#apps . The site remains on its existing NameHero/PHP hosting; no domain or account migration was performed.

The landing page uses actual software captures from the FENTWAVE stable release and identifies the cartridge as hardware in development. It collects optional name, required email and explicit consent for development/launch updates. Signup is separate from a community account. After signup, `/#edit` invites the visitor into the existing account/homepage-builder flow. No shipping date, price, payment or preorder is offered.

## Storage and notifications

- API: `waitlist.php`; HTTPS-only in production, strict HttpOnly session cookie, CSRF and Origin checks, input/size validation, honeypot and IP rate limits. No public contact-list endpoint.
- Storage: `Y2KCRISIS_DATA/fentwave-waitlist`, outside the document root, directory mode0700. `contact.keys` and `contacts.sqlite` are0600; WAL/SHM inherit the restrictive process umask.
- Names/emails are AES-256-GCM ciphertext with a fresh nonce and authentication tag per record. A separate key half computes HMAC deduplication and temporary IP buckets. Keys stay on the server, never in JavaScript, source control or publish artifacts. Original keys are required to recover existing contacts; missing keys fail closed.
- New unique signups notify `evatechusa@gmail.com`, using the fixed sender/envelope `waitlist@y2kcrisis.com`. Validated contact email is Reply-To. Duplicate signups do not generate more messages. There is no visitor confirmation email.
- PHP mail acceptance is recorded separately from final delivery. Notification emails are ordinary email, not end-to-end encrypted. Inbox placement is not proven merely by `mail()` returning true.
- Pending notifications retry every five minutes using the marked `fentwave-waitlist-retry` cron entry. Existing cron jobs are preserved. CLI worker: `Y2KCRISIS_DATA=/home/centered/y2kcrisis-private /opt/cpanel/ea-php83/root/usr/bin/php /home/centered/y2kcrisis.com/fentwave/notify.php --process`. The HTTP route is denied. A stalled `sending` record needs manual review before retrying, to avoid a duplicate notification after an interrupted delivery.
- Back up the private database using SQLite's backup mechanism and preserve its matching private key securely. Do not download contacts into public files or commit keys/backups. Public page privacy text directs removal requests to Jon; removal includes handling any notification copies in email.

To remove a specific contact following an authorized request, use a private CLI PHP session loading `waitlist-core.php`; read the email from stdin, normalize it as the API does, calculate `hash_hmac('sha256', $email, substr(fw_keys(),32))`, and delete only the matching `email_hmac` via `fw_query`. Do not expose an unauthenticated admin or export route.

## Verification and deployment

`tools/verify_fentwave_waitlist.py` runs isolated local API/security/mail-queue tests and headless desktop/390px/320px browser checks. It uses the existing portable PHP installation with explicit extensions and fake mail spool. It never submits test contacts to production. Results/screenshots: ignored `build/fentwave-verification/`.

`tools/publish_fentwave.py --publish` verifies existing hosting ownership, stages/lints PHP privately, initializes encrypted storage, deploys only the explicit FENTWAVE whitelist, adds one live navigation link, tests mail transport, installs the retry job and checks real HTTPS and private permissions. It preserves other live files. Backups and hash reports: ignored `build/fentwave-publish/`. `--verify-only` performs read-only verification without another mail test or publication. A sensitive-cookie attribute case check was corrected after first publication; read-only verification then passed.

`tools/publish_fentwave_apps.py` inserts the FENTWAVE card into the current live Apps route, preserving GAYBOY and unrelated live changes. Source and live JavaScript are syntax-checked, backed up and hash-verified.

`tools/verify_fentwave_live.py` checks the actual Apps-to-homepage path and account invitation, submits ONE clearly labelled owner-address fixture, verifies its encrypted record and accepted notification, then removes only that unguessable fixture. It sends a real test notification to Jon; do not repeatedly run it unnecessarily. Last live check passed2026-10-26. Results: ignored `build/fentwave-live-verification/`. Mail tracking was unavailable through the hosting account, so final recipient delivery/inbox placement remains unverified; transport accepted the test messages.

Do not publish the entire `network/` tree from an older checkout. That could remove newer community/Apps changes. Use the targeted helpers or first integrate this source revision.
