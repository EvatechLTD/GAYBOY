"""Owner beat moderation over the existing pinned SSH connection."""
import argparse
from pathlib import Path
import re
import shlex
import sys
parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['list','delete'])
parser.add_argument('beat_id',nargs='?')
args=parser.parse_args()
if args.action=='delete' and not re.fullmatch('[a-f0-9]{24}',args.beat_id or ''):
    parser.error('delete requires a beat ID from the list')
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp
client=connect_sftp()
try:
    command=['/opt/cpanel/ea-php83/root/usr/bin/php','/home/centered/gayboy-comments-private/admin.php','list-beats' if args.action=='list' else 'delete-beat']
    if args.action=='delete':command.append(args.beat_id)
    _,out,err=client.exec_command(' '.join(map(shlex.quote,command)),timeout=20)
    result=out.read().decode('utf-8')
    if out.channel.recv_exit_status()!=0:raise RuntimeError('Remote beat moderation failed')
    print(result,end='')
finally:client.close()
