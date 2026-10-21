"""Refresh public repository cards; optionally update GitHub About metadata.

Run with --metadata to use Git Credential Manager without printing credentials.
Deploy github-repos.json to both sites after refreshing the cards.
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPO = 'EvatechLTD/GAYBOY'
DESCRIPTION = 'GAYBOY is a Game Boy synth, piano-roll sequencer, sample drum machine and MIDI chiptune workstation. Play in your browser or download the homebrew ROM.'


def api(path, data=None, method=None, token=None):
    headers = {'User-Agent': 'GAYBOY-project-site', 'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if data is not None:
        headers['Content-Type'] = 'application/json'
    request = Request('https://api.github.com/' + path,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers=headers, method=method)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', action='store_true')
    args = parser.parse_args()
    if args.metadata:
        result = subprocess.run(['git', 'credential', 'fill'],
                                input='protocol=https\nhost=github.com\n\n',
                                text=True, capture_output=True, check=True)
        credential = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        token = credential['password']
        api('repos/' + REPO, {'description': DESCRIPTION, 'homepage': 'https://buttholechopper.com/gayboy/'}, 'PATCH', token)
        api('repos/' + REPO + '/topics', {'names': ['gayboy', 'gameboy', 'game-boy', 'gameboy-color', 'chiptune', 'synthesizer', 'sequencer', 'drum-machine', 'midi', 'arduino-boy', 'homebrew', 'gbdk', 'music-production', '8-bit']}, 'PUT', token)
        print('GitHub About description, website and topics updated.')
    repos = api('users/EvatechLTD/repos?sort=pushed&direction=desc&per_page=100')
    repos = [r for r in repos if not r['fork'] and not r['archived'] and not r['private']][:4]
    data = {'refreshed': datetime.now(timezone.utc).isoformat(), 'repositories': [
        {'name': r['name'], 'url': r['html_url'], 'description': r['description'], 'updated': r['pushed_at']}
        for r in repos]}
    for folder in ('website', 'network'):
        (ROOT / folder / 'github-repos.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('Public repository cards refreshed:', ', '.join(r['name'] for r in repos))


if __name__ == '__main__':
    main()
