"""Owner moderation over pinned SSH. No public admin password or endpoint."""
import argparse
from pathlib import Path
import shlex
import sys

parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['list','delete'])
parser.add_argument('comment_id',nargs='?',type=int)
args=parser.parse_args()
if args.action=='delete' and (args.comment_id is None or args.comment_id<1):
    parser.error('delete requires a positive comment ID')
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'VIBECHOPPER/scripts'))
from namehero_access import connect_sftp
client=connect_sftp()
try:
    command=['/opt/cpanel/ea-php83/root/usr/bin/php','/home/centered/gayboy-comments-private/admin.php',args.action]
    if args.action=='delete':command.append(str(args.comment_id))
    _,out,err=client.exec_command(' '.join(map(shlex.quote,command)),timeout=20)
    result=out.read().decode('utf-8')
    if out.channel.recv_exit_status()!=0:raise RuntimeError('Remote comment moderation failed')
    print(result,end='')
finally:client.close()
