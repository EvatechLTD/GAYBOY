"""Deploy only the optional tip assets and inject tags into existing live pages."""
from pathlib import Path
import hashlib
import sys
from datetime import datetime, timezone
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp


def main():
    backup = ROOT / 'build' / ('tips-backup-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    client = connect_sftp()
    sftp = client.open_sftp()
    targets = [
        ('website', '/home/centered/buttholechopper.com/gayboy', 'https://buttholechopper.com/gayboy/'),
        ('network', '/home/centered/y2kcrisis.com', 'https://y2kcrisis.com/'),
    ]
    try:
        for folder, remote, base in targets:
            with sftp.open(remote + '/index.html', 'rb') as stream:
                original = stream.read()
            (backup / (folder + '-index.html')).write_bytes(original)
            for filename in ('gayboy-tips.js', 'gayboy-tips.css', 'gayboy-tips.json'):
                sftp.put(str(ROOT / folder / filename), remote + '/' + filename)
            html = original.decode('utf-8')
            if 'gayboy-tips.js' not in html:
                assert '</head>' in html
                tags = '<link rel="stylesheet" href="gayboy-tips.css?v=1"><script src="gayboy-tips.js?v=1" defer></script>'
                html = html.replace('</head>', tags + '</head>', 1)
                with sftp.open(remote + '/index.html', 'wb') as stream:
                    stream.write(html.encode('utf-8'))
            for filename in ('gayboy-tips.js', 'gayboy-tips.css', 'gayboy-tips.json'):
                with urlopen(base + filename, timeout=25) as response:
                    deployed = response.read()
                assert hashlib.sha256(deployed).digest() == hashlib.sha256((ROOT / folder / filename).read_bytes()).digest()
            print('Tip assets deployed and verified:', base)
    finally:
        sftp.close()
        client.close()


if __name__ == '__main__':
    main()
