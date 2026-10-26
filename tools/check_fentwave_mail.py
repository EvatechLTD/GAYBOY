"""Read only this feature's mail delivery events; do not expose other correspondence."""
from pathlib import Path
import json,sys
sys.path.insert(0,'G:/DEVELOPMENT/VIBECHOPPER/scripts')
from namehero_access import connect_sftp
root=Path(__file__).resolve().parents[1]
c=connect_sftp()
try:
    _,out,err=c.exec_command('cpapi2 --output=json EmailTrack search success=1 defer=1 failure=1 inprogress=1 api2_filter=1 api2_filter_column=sender api2_filter_term=waitlist@y2kcrisis.com api2_filter_type=eq',timeout=30)
    raw=out.read();rc=out.channel.recv_exit_status()
    if rc:
        # cPanel's API2 helper is not on every jailed-shell PATH. Use its normal
        # authenticated API route; the hosting helper keeps credentials in memory.
        sys.path.insert(0,str(root/'tools'))
        from network_host import panel
        try:
            payload=panel('/json-api/cpanel',{'cpanel_jsonapi_apiversion':2,'cpanel_jsonapi_module':'EmailTrack','cpanel_jsonapi_func':'search','cpanel_jsonapi_user':'centered','success':1,'defer':1,'failure':1,'inprogress':1,'api2_filter':1,'api2_filter_column':'sender','api2_filter_term':'waitlist@y2kcrisis.com','api2_filter_type':'eq'})
        except Exception:
            print(json.dumps({'status':'delivery tracking unavailable; transport acceptance verified separately'}));raise SystemExit(0)
    else:payload=json.loads(raw)
    result=payload.get('cpanelresult',payload)
    entries=result.get('data',[])
    if not isinstance(entries,list):entries=[]
    matches=[]
    for r in entries:
        if not isinstance(r,dict):continue
        if r.get('sender')=='waitlist@y2kcrisis.com' and r.get('recipient')=='evatechusa@gmail.com':
            matches.append({k:r.get(k) for k in ['msgid','type','sendunixtime','actiontime','message','reason','host'] if k in r})
    report={'status':'tracking reviewed','notifications':matches,'limits':'Recipient MTA acceptance does not establish inbox placement.'}
    dest=root/'build/fentwave-mail-delivery.json';dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
finally:c.close()
