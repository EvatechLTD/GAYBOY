"""Publish only neutral palette changes, preserving other live emulator edits."""
from pathlib import Path
from datetime import datetime, timezone
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp

OLD = '0xffa1e8d5, 0xff6dbb9c, 0xff486545, 0xff242d18'
NEW = '0xffffffff, 0xffaaaaaa, 0xff555555, 0xff000000'
CSS = '\n/* Neutral white emulator screen. */\n.demo-screen{background:#000}.demo-cover{background:repeating-linear-gradient(0deg,#0000 0 3px,#0001 3px 4px),#fff;color:#000}.demo-cover strong{text-shadow:2px 2px #aaa}.demo-cover button{background:#000;color:#fff;border-color:#aaa}\n'


def main():
    backup = ROOT / 'build' / ('neutral-palette-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    client = connect_sftp()
    sftp = client.open_sftp()
    try:
        for label, remote, base in (
            ('website', '/home/centered/buttholechopper.com/gayboy', 'https://buttholechopper.com/gayboy/'),
            ('network', '/home/centered/y2kcrisis.com/apps/gayboy', 'https://y2kcrisis.com/apps/gayboy/'),
        ):
            for name in ('emulator/player.js', 'emulator/player.css'):
                with sftp.open(remote + '/' + name, 'rb') as stream:
                    original = stream.read()
                (backup / (label + '-' + name.replace('/', '-'))).write_bytes(original)
                source = original.decode('utf-8')
                if name.endswith('.js'):
                    assert OLD in source or NEW in source
                    source = source.replace(OLD, NEW).replace('Explicit four-shade green palette for the original DMG aesthetic.', 'Neutral white palette, lightest to darkest, for every DMG layer.')
                elif '/* Neutral white emulator screen. */' not in source:
                    source += CSS
                with sftp.open(remote + '/' + name, 'wb') as stream:
                    stream.write(source.encode('utf-8'))
            for image in (ROOT / 'website/images').glob('*.png'):
                with sftp.open(remote + '/images/' + image.name, 'rb') as stream:
                    (backup / (label + '-' + image.name)).write_bytes(stream.read())
                sftp.put(str(image), remote + '/images/' + image.name)
                with urlopen(base + 'images/' + image.name, timeout=25) as response:
                    assert response.read() == image.read_bytes()
            with urlopen(base + 'emulator/player.js', timeout=25) as response:
                assert NEW in response.read().decode('utf-8')
            print('Verified live neutral palette and all five captures:', base)
    finally:
        sftp.close()
        client.close()


if __name__ == '__main__':
    main()
