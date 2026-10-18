"""Package the review guide for both public sites, using external CSS for CSP."""
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'docs/user-guide'
    html = (source / 'GAYBOY-user-guide-review.html').read_text(encoding='utf-8')
    style = re.search(r'<style>(.*?)</style>', html, re.S)
    assert style
    css = style.group(1)
    html = html.replace(style.group(), '<link rel="stylesheet" href="guide.css">')
    html = html.replace('Nothing in this review package has been published.', 'This guide is published as a review draft; details may change.')
    html = html.replace('Local review draft', 'Review draft')
    html = html.replace('<nav aria-label="Contents">', '<nav aria-label="Contents"><a href="GAYBOY-user-guide-review.pdf">Download the PDF (review draft)</a><a href="https://github.com/dpjpandone/GAYBOY/tree/main/docs/user-guide">Guide source on GitHub</a>')
    for folder in ('website/guide', 'network/apps/gayboy/guide'):
        target = ROOT / folder
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(html, encoding='utf-8')
        (target / 'guide.css').write_text(css, encoding='utf-8')
        for name in ('GAYBOY-user-guide-review.pdf', 'capture-manifest.json'):
            shutil.copy2(source / name, target / name)
        shutil.copytree(source / 'screenshots', target / 'screenshots', dirs_exist_ok=True)
        print('Packaged review guide:', folder)


if __name__ == '__main__':
    main()
