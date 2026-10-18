"""Explicit local/private SQLite moderation; never expose an administrative web route."""
import argparse
import json
from pathlib import Path
import sqlite3

p=argparse.ArgumentParser()
p.add_argument('--data',type=Path,required=True)
p.add_argument('action',choices=['reports','remove-mark','remove-message'])
p.add_argument('id',type=int,nargs='?')
a=p.parse_args()
dbpath=a.data/'network.sqlite'
if not dbpath.is_file():p.error('Database does not exist.')
with sqlite3.connect(dbpath) as db:
    db.row_factory=sqlite3.Row
    if a.action=='reports':
        for row in db.execute('SELECT * FROM reports ORDER BY id DESC LIMIT 200'):
            print(json.dumps(dict(row),ensure_ascii=True))
    else:
        if not a.id:p.error('Specify the content ID.')
        table='marks' if a.action=='remove-mark' else 'messages'
        result=db.execute(f'DELETE FROM {table} WHERE id=?',(a.id,))
        print(f'Removed {result.rowcount} item(s).')
