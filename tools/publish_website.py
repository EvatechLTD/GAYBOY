"""Publish only /gayboy using the existing workstation's encrypted SFTP helper."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import shlex
import stat
import struct
import sys
import urllib.request
import http.cookiejar

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'website'
HOSTING_REPO = ROOT.parent / 'VIBECHOPPER'
REMOTE = '/home/centered/buttholechopper.com/gayboy'
URL = 'https://buttholechopper.com/gayboy/'
MARKER = b'gayboy-static-page-v1\n'
FILES = ('.htaccess', 'favicon.svg', 'style.css', 'page.js',
         'emulator/sameboy.js', 'emulator/sameboy.wasm', 'emulator/player.js', 'emulator/player.css',
         'emulator/roms/GAYBOY.gb', 'emulator/tutorial.js', 'emulator/tutorial-rom.json', 'emulator/rom-versions.json', 'downloads/GAYBOY.gb', 'downloads/GAYBOY-tutorial.gb',
         'emulator/SAMEBOY-LICENSE.txt', 'emulator/SAMEBOY-UPSTREAM.txt', 'images/train.png',
         'images/turntable.png', 'images/drum-machine.png', 'images/sequencer.png',
         'images/mixer.png', 'downloads/GAYBOY-0.3.gb', 'downloads/SHA256SUMS.txt',
         'comments/style.css', 'comments/wall.js', 'comments/default-avatar.svg', 'comments/api.php',
         'beats/style.css', 'beats/wall.js', 'beats/api.php',
         'admin/index.html', 'admin/api.php', 'admin/admin.js', 'admin/style.css', 'admin/badge.js',
         'index.html')

PRIVATE_WALL = '/home/centered/gayboy-comments-private'
WALL_MARKER = b'gayboy-private-comments-v1\n'


def publish_private_wall(client, sftp, backup, payloads):
    try:
        entry = sftp.lstat(PRIVATE_WALL)
    except FileNotFoundError:
        sftp.mkdir(PRIVATE_WALL, 0o700)
        with sftp.open(PRIVATE_WALL + '/.owner', 'wx') as stream:
            stream.write(WALL_MARKER)
        sftp.chmod(PRIVATE_WALL + '/.owner', 0o600)
    else:
        if not stat.S_ISDIR(entry.st_mode):
            raise RuntimeError('Comment storage must be a real private directory.')
        with sftp.open(PRIVATE_WALL + '/.owner', 'rb') as stream:
            if stream.read() != WALL_MARKER:
                raise RuntimeError('Existing comment storage is not owned by this publisher.')
    sftp.chmod(PRIVATE_WALL, 0o700)
    for directory in ('audio', 'sessions', 'backups'):
        path = PRIVATE_WALL + '/' + directory
        try:
            entry = sftp.lstat(path)
        except FileNotFoundError:
            sftp.mkdir(path, 0o700)
        else:
            if not stat.S_ISDIR(entry.st_mode):
                raise RuntimeError('Private comment directory must not be a symlink.')
        sftp.chmod(path, 0o700)
    key_path = PRIVATE_WALL + '/secret.bin'
    try:
        entry = sftp.lstat(key_path)
    except FileNotFoundError:
        with sftp.open(key_path, 'wx') as stream:
            stream.write(secrets.token_bytes(32))
    else:
        if not stat.S_ISREG(entry.st_mode) or entry.st_size != 32:
            raise RuntimeError('Unexpected comment signing key.')
    sftp.chmod(key_path, 0o600)
    code = ('umask(0077); $p=' + json.dumps(PRIVATE_WALL) + ';'
            'if(file_exists($p."/comments.sqlite")) {'
            '$source=new SQLite3($p."/comments.sqlite");$source->busyTimeout(5000);'
            '$target=new SQLite3($p."/backups/".' + json.dumps(backup.name + '.sqlite') + ');'
            'if(!$source->backup($target)){exit(2);} echo "backed-up";'
            '} else {echo "new-database";}')
    _, output, _ = client.exec_command('/opt/cpanel/ea-php83/root/usr/bin/php -r ' + shlex.quote(code), timeout=30)
    result = output.read().decode().strip()
    if result not in ('backed-up', 'new-database'):
        raise RuntimeError('Could not back up existing comments before publication.')
    for name, data in payloads.items():
        path = PRIVATE_WALL + '/' + name
        try:
            entry = sftp.lstat(path)
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(entry.st_mode):
                raise RuntimeError('Refusing to replace a non-regular private file.')
            with sftp.open(path, 'rb') as stream:
                old = stream.read()
            if old == data:
                continue
            previous = backup / 'comments-private' / name
            previous.parent.mkdir(parents=True, exist_ok=True)
            previous.write_bytes(old)
        temporary = path + '.upload-' + secrets.token_hex(6)
        with sftp.open(temporary, 'wx') as stream:
            stream.write(data)
        sftp.chmod(temporary, 0o600)
        with sftp.open(temporary, 'rb') as stream:
            if stream.read() != data:
                raise RuntimeError('Private comment upload verification failed.')
        sftp.posix_rename(temporary, path)
    _, output, _ = client.exec_command('/opt/cpanel/ea-php83/root/usr/bin/php ' + shlex.quote(PRIVATE_WALL+'/admin-init.php'), timeout=20)
    admin = json.loads(output.read().decode())
    if 'setup_token' in admin:
        # The one-time key stays local; never put it in public assets or the deployment report.
        (backup/'admin-setup.json').write_text(json.dumps(admin),encoding='utf-8')
    return {'database_backup': result == 'backed-up', 'private_storage': PRIVATE_WALL,
            'admin_configured': admin.get('configured',False), 'admin_setup_link_created': 'setup_token' in admin}


def verify_comments_api():
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    endpoint = URL + 'comments/api.php?action='
    with opener.open(endpoint + 'list', timeout=20) as response:
        listing = json.loads(response.read())
    if not isinstance(listing.get('comments'), list) or not isinstance(listing.get('total'), int):
        raise RuntimeError('Public comments API did not return a valid listing.')
    with opener.open(endpoint + 'challenge', timeout=20) as response:
        challenge = json.loads(response.read())
    if set(challenge) != {'csrf', 'nonce'}:
        raise RuntimeError('Public human-check initialization failed.')
    with opener.open(endpoint + 'image&nonce=' + challenge['nonce'], timeout=20) as response:
        image = response.read()
    if not image.startswith(b'\x89PNG') or struct.unpack('>II', image[16:24]) != (320, 90):
        raise RuntimeError('Public human-check image failed.')
    with opener.open(endpoint + 'audio&nonce=' + challenge['nonce'], timeout=20) as response:
        audio = response.read()
    if not audio.startswith(b'RIFF') or audio[8:12] != b'WAVE':
        raise RuntimeError('Public human-check audio failed.')
    return True


def main():
    sys.path.insert(0, str(HOSTING_REPO / 'scripts'))
    from namehero_access import connect_sftp

    # Read the complete snapshot before connecting; never publish a partial build.
    payloads = {name: (SOURCE / name).read_bytes() for name in FILES}
    versions=json.loads(payloads['emulator/rom-versions.json'])
    for digest, version in versions['versions'].items():
        name=version['rom']
        if not name.startswith('emulator/roms/GAYBOY') or '/' in name[len('emulator/roms/'):] or not name.endswith('.gb'):
            raise RuntimeError('Unexpected archived cartridge path.')
        data=(SOURCE/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Archived beat cartridge checksum mismatch.')
        payloads[name]=data
    for name in ['emulator/roms/GAYBOY.gb','downloads/GAYBOY.gb','downloads/GAYBOY-0.3.gb','downloads/GAYBOY-tutorial.gb']:
        if payloads[name]!=payloads['downloads/GAYBOY.gb']:raise RuntimeError('Browser and download cartridges differ.')
    payloads['index.html']=payloads.pop('index.html')
    private_files = ('app.php', 'admin.php', 'beats.php', 'admin-web.php', 'admin-init.php', *(f'audio/{digit}.wav' for digit in range(10)))
    private_payloads = {name: (ROOT / 'hosting/comments' / name).read_bytes() for name in private_files}
    tutorial = json.loads(payloads['emulator/tutorial-rom.json'])
    if hashlib.sha256(payloads[tutorial['rom']]).hexdigest() != tutorial['sha256']:
        raise RuntimeError('Tutorial cartridge does not match its observation map.')
    if ("const BEAT_ROM = '"+tutorial['sha256']+"';").encode() not in private_payloads['beats.php']:
        raise RuntimeError('Shared beat ROM must stay pinned; retain v1 playback before changing cartridges.')
    rom = payloads['downloads/GAYBOY-0.3.gb']
    expected = payloads['downloads/SHA256SUMS.txt'].decode().split()[0]
    if hashlib.sha256(rom).hexdigest() != expected:
        raise RuntimeError('ROM checksum does not match the page snapshot.')
    if len(rom) != 1048576 or rom[0x147] != 0x1B or rom[0x149] != 3:
        raise RuntimeError('Unexpected ROM format.')
    if (sum(rom) - rom[0x14e] - rom[0x14f]) & 65535 != int.from_bytes(rom[0x14e:0x150], 'big'):
        raise RuntimeError('ROM internal checksum failed.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3)
    backup = ROOT / 'build' / 'website-publish' / stamp
    backup.mkdir(parents=True)
    client = connect_sftp()
    sftp = client.open_sftp()
    sftp.get_channel().settimeout(30)
    try:
        try:
            entry = sftp.lstat(REMOTE)
        except FileNotFoundError:
            sftp.mkdir(REMOTE, 0o755)
            with sftp.open(REMOTE + '/.gayboy-owner', 'wx') as stream:
                stream.write(MARKER)
        else:
            if not stat.S_ISDIR(entry.st_mode):
                raise RuntimeError('Page mount must be a directory.')
            with sftp.open(REMOTE + '/.gayboy-owner', 'rb') as stream:
                if stream.read() != MARKER:
                    raise RuntimeError('Existing directory is not owned by this page.')
        comments_report = publish_private_wall(client, sftp, backup, private_payloads)
        for folder in ('images', 'downloads', 'emulator', 'comments', 'beats', 'admin'):
            path = REMOTE + '/' + folder
            try:
                entry = sftp.lstat(path)
            except FileNotFoundError:
                sftp.mkdir(path, 0o755)
            else:
                if not stat.S_ISDIR(entry.st_mode):
                    raise RuntimeError('Asset directory must not be a symlink.')
        hashes = {}
        for name, data in payloads.items():
            if name == 'index.html':
                comments_report['api_image_audio_verified'] = verify_comments_api()
                with urllib.request.urlopen(URL+'beats/api.php?action=list',timeout=20) as response:
                    beats=json.loads(response.read())
                if not isinstance(beats.get('beats'),list) or not isinstance(beats.get('total'),int):
                    raise RuntimeError('Public beat wall did not return a valid listing.')
            path = REMOTE + '/' + name
            try:
                entry = sftp.lstat(path)
            except FileNotFoundError:
                pass
            else:
                if not stat.S_ISREG(entry.st_mode):
                    raise RuntimeError('Refusing to replace a non-regular file.')
                destination = backup / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with sftp.open(path, 'rb') as stream:
                    prior=stream.read()
                    if prior==data:
                        hashes[name]=hashlib.sha256(data).hexdigest()
                        continue
                    destination.write_bytes(prior)
            temporary = path + '.upload-' + secrets.token_hex(6)
            with sftp.open(temporary, 'wx') as stream:
                stream.write(data)
            sftp.chmod(temporary, 0o644)
            with sftp.open(temporary, 'rb') as stream:
                if stream.read() != data:
                    raise RuntimeError('Uploaded data differs from source.')
            sftp.posix_rename(temporary, path)
            hashes[name] = hashlib.sha256(data).hexdigest()
    finally:
        sftp.close()
        client.close()
    for name, expected_hash in hashes.items():
        if name == '.htaccess' or name.endswith('.php'):
            continue  # Server configuration is verified over SFTP, never public HTTPS.
        target = URL + ('' if name == 'index.html' else name) + '?verify=' + stamp
        request = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200 or hashlib.sha256(response.read()).hexdigest() != expected_hash:
                raise RuntimeError('Live HTTPS verification failed: ' + name)
    report = {'url': URL, 'files': hashes, 'https_verified': True, 'backup_directory': str(backup),
              'comments': comments_report}
    (backup / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    # The standalone site is retired; publishing must preserve its redirect.
    from deploy_gayboy_destination import main as publish_redirect
    publish_redirect(redirect_only=True)
