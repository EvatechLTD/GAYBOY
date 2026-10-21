"""Move the live browser ROM namespace and redirect the retired standalone page."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LEGACY = '/home/centered/buttholechopper.com/gayboy'
APP = '/home/centered/y2kcrisis.com/apps/gayboy'
NOTE = ('The browser player does not support physical link cable connections. '
        'Download the ROM for compatible hardware and external MIDI setups. '
        'Planned link cable sync will require a compatible setup outside this browser player.')


def main(redirect_only=False):
    sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
    from namehero_access import connect_sftp
    backup = ROOT / 'build/destination-migration' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True)
    client = connect_sftp()
    sftp = client.open_sftp()
    sftp.get_channel().settimeout(30)
    try:
        def read(path):
            with sftp.open(path, 'rb') as stream:
                stream.prefetch()
                return stream.read()

        changes = {}
        if not redirect_only:
            # Transform live manifests, preserving the exact deployed build and beat maps.
            for name in ('emulator/tutorial-rom.json', 'emulator/rom-versions.json'):
                manifest = json.loads(read(APP + '/' + name))
                versions = manifest['versions'].values() if 'versions' in manifest else [manifest]
                for version in versions:
                    old = version['rom']
                    if not re.fullmatch(r'(?:downloads|emulator/roms)/GAYBOY[\w.-]*\.gb', old):
                        raise RuntimeError('Unexpected cartridge path')
                    cartridge = read(APP + '/' + old)
                    if hashlib.sha256(cartridge).hexdigest() != version['sha256']:
                        raise RuntimeError('Live cartridge checksum mismatch')
                    version['rom'] = 'emulator/roms/' + old.rsplit('/', 1)[-1]
                    changes[APP + '/' + version['rom']] = cartridge
                changes[APP + '/' + name] = (json.dumps(manifest, indent=2) + '\n').encode()
            player = read(APP + '/emulator/player.js').decode()
            player = re.sub(r'emulator/(tutorial-rom|rom-versions)\.json\?v=[^\'\"]+',
                            r'emulator/\1.json?v=rom-paths-20261019', player)
            changes[APP + '/emulator/player.js'] = player.encode()
            html = read(APP + '/player.html').decode()
            html = re.sub(r'emulator/player\.js(?:\?v=[^\"]*)?"',
                          'emulator/player.js?v=rom-paths-20261019"', html)
            if 'demo-hardware-note' not in html:
                html = html.replace('<p class="demo-status"',
                                    '<p class="demo-hardware-note">' + NOTE + '</p>\n<p class="demo-status"', 1)
            changes[APP + '/player.html'] = html.encode()
        # Publish the redirect last, after destination dependencies.
        changes[LEGACY + '/.htaccess'] = (ROOT / 'website/.htaccess').read_bytes()
        for remote, payload in changes.items():
            relative = remote.removeprefix('/home/centered/')
            try:
                prior = read(remote)
            except FileNotFoundError:
                prior = None
            if prior == payload:
                continue
            if prior is not None:
                target = backup / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(prior)
            parent = remote.rsplit('/', 1)[0]
            try:
                sftp.stat(parent)
            except FileNotFoundError:
                sftp.mkdir(parent, 0o755)
            temporary = remote + '.destination-upload'
            with sftp.open(temporary, 'wb') as stream:
                stream.set_pipelined(True)
                stream.write(payload)
            sftp.chmod(temporary, 0o644)
            if read(temporary) != payload:
                raise RuntimeError('Upload verification failed')
            sftp.posix_rename(temporary, remote)
        (backup / 'report.json').write_text(json.dumps({
            'files': list(changes), 'redirect': 'https://y2kcrisis.com/gayboy',
            'utc': datetime.now(timezone.utc).isoformat()}, indent=2))
        print('Published destination migration; backup:', backup)
    finally:
        sftp.close()
        client.close()


if __name__ == '__main__':
    main('--redirect-only' in sys.argv)
