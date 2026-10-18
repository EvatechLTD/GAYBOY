"""Publish GitHub panels and focused SEO changes, preserving live page edits."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import re
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp

ASSETS = ('gayboy-github.js', 'gayboy-github.css', 'github-repos.json')


def patch_html(html, website=False):
    if 'gayboy-github.js' not in html:
        assert '</head>' in html
        html = html.replace('</head>', '<link rel="stylesheet" href="gayboy-github.css?v=1"><script src="gayboy-github.js?v=1" defer></script></head>', 1)
    if website:
        local = (ROOT / 'website/index.html').read_text(encoding='utf-8')
        for pattern in (r'<title>.*?</title>', r'<meta name="description"[^>]+>'):
            html = re.sub(pattern, lambda _: re.search(pattern, local).group(), html, count=1)
        for tag in re.findall(r'<(?:link rel="canonical"|meta property="og:[^"]+"|meta name="twitter:card")[^>]+>', local):
            key = tag.split(' content=')[0].split(' href=')[0]
            if key not in html:
                html = html.replace('</head>', tag + '</head>', 1)
        if 'href="https://github.com/dpjpandone/GAYBOY"' not in html:
            html = html.replace('<a href="#about">', '<a href="https://github.com/dpjpandone/GAYBOY">GitHub source ↗</a><a href="#about">', 1)
    elif 'GAYBOY Game Boy synth on GitHub' not in html:
        html = html.replace('</footer>', ' · <a href="https://github.com/dpjpandone/GAYBOY">GAYBOY Game Boy synth on GitHub</a></footer>', 1)
    return html


def main():
    backup = ROOT / 'build' / ('github-presence-backup-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    client = connect_sftp()
    sftp = client.open_sftp()
    try:
        for folder, remote, base in (
            ('website', '/home/centered/buttholechopper.com/gayboy', 'https://buttholechopper.com/gayboy/'),
            ('network', '/home/centered/y2kcrisis.com', 'https://y2kcrisis.com/'),
        ):
            for name in (*ASSETS, 'index.html'):
                try:
                    with sftp.open(remote + '/' + name, 'rb') as stream:
                        previous = stream.read()
                    (backup / (folder + '-' + name)).write_bytes(previous)
                except FileNotFoundError:
                    assert name != 'index.html'
            with sftp.open(remote + '/index.html', 'rb') as stream:
                html = patch_html(stream.read().decode('utf-8'), folder == 'website')
            for name in ASSETS:
                sftp.put(str(ROOT / folder / name), remote + '/' + name)
            guide = ROOT / ('website/guide' if folder == 'website' else 'network/apps/gayboy/guide')
            guide_remote = remote + ('/guide' if folder == 'website' else '/apps/gayboy/guide')
            for local in [guide, *sorted(guide.rglob('*'))]:
                destination = guide_remote + ('/' + local.relative_to(guide).as_posix() if local != guide else '')
                if local.is_dir():
                    try:
                        sftp.stat(destination)
                    except FileNotFoundError:
                        sftp.mkdir(destination)
                else:
                    try:
                        with sftp.open(destination, 'rb') as stream:
                            old = stream.read()
                        saved = backup / folder / 'guide' / local.relative_to(guide)
                        saved.parent.mkdir(parents=True, exist_ok=True)
                        saved.write_bytes(old)
                    except FileNotFoundError:
                        pass
                    sftp.put(str(local), destination)
            with sftp.open(remote + '/index.html', 'wb') as stream:
                stream.write(html.encode('utf-8'))
            for name in ASSETS:
                with urlopen(base + name, timeout=25) as response:
                    assert hashlib.sha256(response.read()).digest() == hashlib.sha256((ROOT / folder / name).read_bytes()).digest()
            with urlopen(base, timeout=25) as response:
                assert 'gayboy-github.js' in response.read().decode('utf-8')
            print('GitHub panel deployed and verified:', base)
        print('Original live files backed up in', backup)
    finally:
        sftp.close()
        client.close()


if __name__ == '__main__':
    main()
