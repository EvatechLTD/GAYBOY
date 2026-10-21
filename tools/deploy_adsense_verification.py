"""Publish the owner's AdSense verification without enabling automatic ads."""
from pathlib import Path
import sys
from datetime import datetime, timezone
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp

META = '<meta name="google-adsense-account" content="ca-pub-7514332629179533">'
SELLER = 'google.com, pub-7514332629179533, DIRECT, f08c47fec0942fa0'


def main():
    backup = ROOT / 'build' / ('adsense-backup-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    client = connect_sftp()
    sftp = client.open_sftp()
    try:
        for label, root, page, base in (
            ('network', '/home/centered/y2kcrisis.com', '/index.html', 'https://y2kcrisis.com/'),
            ('website', '/home/centered/buttholechopper.com', '/gayboy/index.html', 'https://buttholechopper.com/'),
        ):
            # Verification belongs on each root homepage as well as GAYBOY.
            for relative in dict.fromkeys(('/index.html', page)):
                with sftp.open(root + relative, 'rb') as stream:
                    original = stream.read()
                (backup / (label + relative.replace('/', '-') )).write_bytes(original)
                html = original.decode('utf-8')
                if META not in html:
                    assert '</head>' in html
                    with sftp.open(root + relative, 'wb') as stream:
                        stream.write(html.replace('</head>', META + '</head>', 1).encode('utf-8'))
            try:
                with sftp.open(root + '/ads.txt', 'rb') as stream:
                    old = stream.read()
            except FileNotFoundError:
                old = b''
            (backup / (label + '-ads.txt')).write_bytes(old)
            lines = old.decode('utf-8').splitlines()
            if SELLER not in lines:
                with sftp.open(root + '/ads.txt', 'wb') as stream:
                    stream.write(('\n'.join(lines + [SELLER]) + '\n').encode('utf-8'))
            with urlopen(base + 'ads.txt', timeout=25) as response:
                assert SELLER in response.read().decode('utf-8')
            for relative in dict.fromkeys(('/index.html', page)):
                with urlopen(base.rstrip('/') + relative, timeout=25) as response:
                    assert META in response.read().decode('utf-8')
            print('Verified publisher tag and root ads.txt:', base)
    finally:
        sftp.close()
        client.close()


if __name__ == '__main__':
    main()
