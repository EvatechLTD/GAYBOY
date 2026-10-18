# Y2KCRISIS public alpha

Live: https://y2kcrisis.com/ — deployed and verified October 18, 2026 (UTC).
NameHero addon domain: `/home/centered/y2kcrisis.com`; private SQLite:
`/home/centered/y2kcrisis-private`. Root and www resolve to 198.175.150.30.
Let’s Encrypt covers both names. HTTP redirects to HTTPS. Read-only live checks
passed for TLS, public asset hashes, security headers, secure session cookies,
API responses and 1440/390/320px browser rendering. Local multi-account checks
passed for ownership, trades, DM isolation, tag history, blocking and mint limits.

Independent PHP/SQLite social network. GAYBOY remains the first linked app.

Run `network/start-local.ps1` from PowerShell and visit http://127.0.0.1:18982/.
Requires PHP 8.1+ with SQLite3 and mbstring. Set `Y2KCRISIS_DATA`
to an absolute private directory outside the web document root. Serve `network/`
as the document root. Apache reads the supplied security headers from `.htaccess`;
PHP's development server does not apply them. Use HTTPS in production.

Version 2 uses a shared visual homepage renderer and builder. Visit /~GAYBOY for
the reference page, or choose USE THE FULL GAYBOY TEMPLATE in the editor to make
an editable copy. Header, ticker, logo/artwork, sidebars, backgrounds, typography,
borders, spacing, badges, galleries, downloads, app embeds and social widgets
are stored as settings and up to twelve blocks per page. Members can add eight
extra pages at /~handle/page. GAYBOY's original site remains intact.

Media blocks auto-detect YouTube (including playlists/Shorts/live), SoundCloud,
Spotify, Vimeo, Mixcloud and Twitch. Bandcamp accepts its official embed URL/code.
Direct audio/video files play through native controls. Each page can also have
one sidebar soundtrack. Provider availability, playback rights and login rules
still apply. Players start with visitor interaction; arbitrary iframe HTML is not
executed. Playback clocks are not synchronized between different visitors.

Social features: buddy requests, featured eight, presence/away messages, floating
IM windows and optional sounds; member-created chatrooms with wallpaper, media,
capacity, privacy, participant lists, moderators, bans and history choices;
guestbooks with doodles and approval; private/displayable postcards; bathroom
sticker graffiti with approval and archives; searchable neighborhoods, webrings,
a finite chronological bulletin board and monthly questions/decorating prompts.
Typed uWu becomes a custom scene-face emoji in rooms and DMs. Common emoticons
and a picker are included. Message text stays unchanged in storage.

Pins retain individual ownership and provenance. Giving transfers ownership;
trades swap two owned pins atomically. Four finite creative achievements unlock
creation tokens. Each creates a one-of-one or fixed edition of two/three; editions
cannot be expanded. The jacket supports movable, rotated pins/stickers/stamps;
unplaced pins may remain private. The paint studio supports editable text/image
layers, five letter styles, freehand tools, pixelated uploads, limited palettes,
transparency, sticker outlines, undo/redo and PNG export. Only one tag is active;
old bathroom placements preserve their artwork.

Extras: recoverable local drafts, ten saved page versions, JSON design export/
import, additional pages, phone preview, one-time recovery codes, and old-session
invalidation after password recovery. There is no email recovery. DMs are stored
in the private database with participant-only API access, not end-to-end encrypted.
A history toggle controls the member's view; clear-history hides earlier messages
for that member without altering the other participant's copy.

The packaged GAYBOY app preserves the original emulator and tutorial. Its network
beat shelf captures running ROM sequences, attributes them to signed-in members,
and supports share-link playback while parking/restoring the listener's own beat.
Existing ROM files and original website code are not modified.

Audit: feature-audit.json maps the conversation requirements to implementations.
QA: verify_network_v2.py checks separate accounts, permissions and browser flows;
verify_network_builder.py checks template parity, export/import, drafts, restore
and provider parsing; verify_network_beats.py drives real ROM input, sharing and
session restoration. All run only against isolated local storage. The read-only
verify_network_live.py checks public HTTPS, asset hashes, CSP and live app boot.

Moderation: `python tools/network_moderate.py --data PRIVATE_DIRECTORY reports`
lists reports from a local/private database. `remove-mark ID` and
`remove-message ID` remove reported content. Back up `network.sqlite` with
SQLite's backup API, not by copying a live WAL database alone. No automatic
retention or email notification is configured. Review reports manually.

QA: `tools/verify_network.py` runs against an isolated server at 127.0.0.1:18981.
It creates disposable local accounts. Never point it at production.

Hosting helper: `tools/network_host.py setup|deploy|ssl|status` uses the existing
Windows-encrypted NameHero access helper. It never prints credentials. Deploy
verifies document root, backs up changed files locally, takes a private SQLite backup, verifies uploaded hashes,
and leaves SQLite outside the web root. Domain attachment requires an authenticated
cPanel session; `tools/network_panel_login.py` lets the owner sign in normally.
`stage` uploads and verifies files in the intended hosting directory before DNS
or domain attachment is ready; staging does not mean the domain is live.

The tag studio bundles Press Start 2P (SIL Open Font License) and Permanent Marker
(Apache License); their license files are in `fonts/` alongside the font files.
