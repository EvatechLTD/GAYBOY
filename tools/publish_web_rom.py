"""Publish the packaged ROM/player update to the existing Y2KCRISIS app only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'network/apps/gayboy'
REMOTE = '/home/centered/y2kcrisis.com/apps/gayboy'
URL = 'https://y2kcrisis.com/apps/gayboy/'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    current = json.loads((SOURCE / 'emulator/tutorial-rom.json').read_text())
    practice = json.loads((SOURCE / 'emulator/practice-rom.json').read_text())
    registry = json.loads((SOURCE / 'emulator/rom-versions.json').read_text())
    rom = (ROOT / 'build/GAYBOY.gb').read_bytes()
    assert digest(rom) == current['sha256'] == registry['current']
    assert len(rom) == 1048576 and rom[0x147] == 0x1b and rom[0x149] == 3
    payloads = {}
    for sha, version in registry['versions'].items():
        name = version['rom']
        assert re.fullmatch(r'emulator/roms/GAYBOY[\w.-]*\.gb', name)
        data = (SOURCE / name).read_bytes()
        assert digest(data) == sha == version['sha256']
        payloads[name] = data
    assert digest(payloads[practice['rom']]) == practice['sha256']
    assert 'seqevents_lo' in practice['symbols']
    release_version = (ROOT / 'VERSION').read_text().strip()
    assert current['version'] == release_version and current['channel'] == 'stable'
    for name in ('downloads/GAYBOY.gb', 'downloads/GAYBOY-0.3.gb', 'downloads/GAYBOY-' + release_version + '.gb'):
        payloads[name] = (SOURCE / name).read_bytes()
        assert payloads[name] == rom
    payloads['downloads/GAYBOY-tutorial.gb'] = (SOURCE / 'downloads/GAYBOY-tutorial.gb').read_bytes()
    assert digest(payloads['downloads/GAYBOY-tutorial.gb']) == practice['sha256']
    for name in ('downloads/SHA256SUMS.txt', 'emulator/rom-versions.json',
                 'emulator/practice-rom.json', 'emulator/tutorial-rom.json', 'emulator/player.js'):
        payloads[name] = (SOURCE / name).read_bytes()
    assert b'emulator/practice-rom.json' in payloads['emulator/player.js']
    assert b'gayboy-browser-sram-0.3-10cc021b' in payloads['emulator/player.js']
    sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
    from namehero_access import connect_sftp
    backup = ROOT / 'build/web-rom-publish' / (datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3))
    backup.mkdir(parents=True)
    client = connect_sftp()
    sftp = client.open_sftp()
    sftp.get_channel().settimeout(30)
    changed = []
    try:
        assert stat.S_ISDIR(sftp.lstat(REMOTE).st_mode)

        def read(name):
            with sftp.open(REMOTE + '/' + name, 'rb') as f:
                f.prefetch()
                return f.read()

        live_registry = json.loads(read('emulator/rom-versions.json'))
        assert set(live_registry['versions']) <= set(registry['versions']), 'Package is missing live shared-beat versions'
        for sha, version in live_registry['versions'].items():
            assert version['symbols'] == registry['versions'][sha]['symbols'], 'Existing beat symbol map changed'
        # Preserve any live shell changes; only refresh the player cache version.
        html = read('player.html').decode('utf-8')
        assert 'id="live-demo"' in html
        html, matches = re.subn(r'emulator/player\.js(?:\?v=[^"\s]*)?',
                               'emulator/player.js?v=stable-1.0-20261022', html)
        assert matches == 1
        html, matches = re.subn(r'(<p class="demo-intro">).*?(</p>)',
                               lambda m: m[1] + 'GAYBOY ' + release_version + ' — stable release.' + m[2], html, count=1)
        assert matches == 1
        payloads['player.html'] = html.encode('utf-8')
        def normalized_player(data):
            return re.sub(rb'\?v=[A-Za-z0-9._-]+', b'?v=VERSION', data.replace(b'\r\n', b'\n'))
        known_players = [payloads['emulator/player.js']]
        for revision in ('HEAD', 'HEAD^'):
            known_players.append(subprocess.check_output(
                ['git', 'show', revision + ':network/apps/gayboy/emulator/player.js'], cwd=ROOT))
        live_player = read('emulator/player.js')
        assert normalized_player(live_player) in [normalized_player(p) for p in known_players], 'Live player has unmerged edits'
        # Read/back up every changed target before publishing any target.
        for name, data in payloads.items():
            try:
                entry = sftp.lstat(REMOTE + '/' + name)
                assert stat.S_ISREG(entry.st_mode), name
                prior = read(name)
            except FileNotFoundError:
                prior = None
            if prior == data:
                continue
            if prior is not None:
                saved = backup / name
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(prior)
            changed.append(name)
        for name in changed:
            target = REMOTE + '/' + name
            temporary = target + '.rom-upload-' + secrets.token_hex(6)
            with sftp.open(temporary, 'wx') as f:
                f.set_pipelined(True)
                f.write(payloads[name])
            sftp.chmod(temporary, 0o644)
            with sftp.open(temporary, 'rb') as f:
                assert digest(f.read()) == digest(payloads[name]), name
            sftp.posix_rename(temporary, target)
    finally:
        sftp.close()
        client.close()
    for name, data in payloads.items():
        with urlopen(URL + name, timeout=30) as response:
            assert digest(response.read()) == digest(data), 'Public mismatch: ' + name
    assert digest((ROOT / 'build/GAYBOY.gb').read_bytes()) == current['sha256'], 'Build changed during publication'
    report = {'url': URL, 'rom_sha256': current['sha256'], 'practice_sha256': practice['sha256'],
              'changed': changed, 'publicly_verified': list(payloads), 'backup': str(backup)}
    (backup / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
