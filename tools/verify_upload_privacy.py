"""Verify upload metadata choices on an isolated local PHP server; never production."""
import base64
import io
import json
import os
from pathlib import Path
import secrets
import site
import subprocess
import sys
import time
import urllib.request

sys.path.append(str(Path(sys.base_prefix)/'Lib/site-packages'))
sys.path.append(site.getusersitepackages())
from PIL import Image, PngImagePlugin, TiffImagePlugin
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'build'/('upload-privacy-qa-'+secrets.token_hex(4));DATA.mkdir()
BASE='http://127.0.0.1:18986/'
MARK=b'PRIVATE-GPS-AUTHOR-TEST'
image=Image.new('RGB',(20,12),'#baff37')
exif=Image.Exif();exif[274]=6;exif[315]=MARK.decode();exif[34853]={1:'N',2:(TiffImagePlugin.IFDRational(41),TiffImagePlugin.IFDRational(5),TiffImagePlugin.IFDRational(0)),3:'W',4:(TiffImagePlugin.IFDRational(80),TiffImagePlugin.IFDRational(38),TiffImagePlugin.IFDRational(0))}
fixtures=[]
for progressive in [False,True]:
 buf=io.BytesIO();image.save(buf,format='JPEG',exif=exif,progressive=progressive);fixtures.append(('jpeg-progressive' if progressive else 'jpeg','image/jpeg',buf.getvalue()))
meta=PngImagePlugin.PngInfo();meta.add_text('GPS',MARK.decode());meta.add_text('Author',MARK.decode(),zip=True);meta.add_itxt('location',MARK.decode())
buf=io.BytesIO();image.save(buf,format='PNG',pnginfo=meta,exif=exif);fixtures.append(('png','image/png',buf.getvalue()))
buf=io.BytesIO();image.save(buf,format='WEBP',lossless=True,exif=exif,xmp=MARK);fixtures.append(('webp','image/webp',buf.getvalue()))
buf=io.BytesIO();image.save(buf,format='GIF',save_all=True,append_images=[Image.new('RGB',(20,12),'#ff69b4')],duration=[120,240],loop=0,comment=MARK);fixtures.append(('gif','image/gif',buf.getvalue()))
buf=io.BytesIO();image.save(buf,format='PNG',save_all=True,append_images=[Image.new('RGB',(20,12),'#ff69b4')],duration=[120,240],loop=0,pnginfo=meta);fixtures.append(('apng','image/png',buf.getvalue()))

env=dict(os.environ,Y2KCRISIS_DATA=str(DATA))
server=subprocess.Popen([str(ROOT/'build/php/php.exe'),'-S','127.0.0.1:18986','-t',str(ROOT/'network'),str(ROOT/'network/router.php')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(40):
  try:
   urllib.request.urlopen(BASE+'api.php',timeout=1).close();break
  except Exception:time.sleep(.1)
 else:raise RuntimeError('Local server did not start')
 with sync_playwright() as p:
  browser=p.chromium.launch(channel='chrome');context=browser.new_context();request=context.request
  token=request.get(BASE+'api.php').json()['csrf']
  def post(action,data):return request.post(BASE+'api.php?action='+action,data=data,headers={'X-CSRF-Token':token})
  assert post('register',{'handle':'privacy_'+secrets.token_hex(4),'password':secrets.token_urlsafe(20)}).status==200
  for name,mime,raw in fixtures:
   assert MARK in raw,name
   encoded='data:'+mime+';base64,'+base64.b64encode(raw).decode()
   for choice in [None,True,False]:
    data={'data':encoded}
    if choice is not None:data['strip_metadata']=choice
    response=post('upload',data);assert response.status==200,(name,choice,response.text())
    result=request.get(BASE+response.json()['url']).body()
    if choice is False:assert result==raw,(name,'opt-out changed original')
    else:
     assert MARK not in result,(name,'metadata still present')
     clean=Image.open(io.BytesIO(result));original=Image.open(io.BytesIO(raw))
     assert clean.size==original.size and getattr(clean,'n_frames',1)==getattr(original,'n_frames',1),name
     for frame in range(getattr(original,'n_frames',1)):
      clean.seek(frame);original.seek(frame);assert clean.convert('RGBA').tobytes()==original.convert('RGBA').tobytes(),(name,'pixels changed')
     if mime in ['image/jpeg','image/webp'] or name=='png':
      assert clean.getexif().get(274)==6,name
      assert 34853 not in clean.getexif() and 315 not in clean.getexif(),name
    assert post('upload',{'data':encoded,'strip_metadata':'false'}).status==422
   print('PASS:',name,'default stripping, explicit stripping, exact opt-out, pixels/animation, input validation')
  page=context.new_page();page.goto(BASE+'#edit');page.locator('[data-upload-privacy]').wait_for()
  toggle=page.locator('[data-upload-privacy]');assert toggle.is_checked();toggle.uncheck()
  assert page.evaluate("localStorage.getItem('y2k-strip-upload-metadata')")=='false'
  page.reload();page.locator('[data-upload-privacy]').wait_for();assert not page.locator('[data-upload-privacy]').is_checked()
  page.locator('[data-upload-privacy]').check();assert page.evaluate("localStorage.getItem('y2k-strip-upload-metadata')")=='true'
  page.screenshot(path=str(DATA/'upload-privacy-toggle.png'),full_page=True)
  context2=browser.new_context();assert context2.request.post(BASE+'api.php?action=upload',data={}).status==403
  browser.close()
  print('PASS: browser default-on toggle, persistence across reload, opt-in restoration, unauthorized upload blocked')
finally:
 server.terminate();server.wait(timeout=10)
