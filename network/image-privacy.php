<?php
declare(strict_types=1);

// Container edits preserve compressed pixels, animation, transparency and color profiles.
function image_privacy_orientation(string $app): int {
    $t=substr($app,0,6)==="Exif\0\0"?substr($app,6):$app;$le=substr($t,0,2)==='II';
    if(!$le&&substr($t,0,2)!=='MM')return 1;
    $read=function(int $at,int $bytes)use($t,$le): int {
        if($at<0||$at+$bytes>strlen($t))return -1;
        return unpack($bytes===2?($le?'v':'n'):($le?'V':'N'),substr($t,$at,$bytes))[1];
    };
    if($read(2,2)!==42)return 1;$off=$read(4,4);if($off<8)return 1;
    $count=$read($off,2);if($count<0||$count>256)return 1;
    for($n=0;$n<$count;$n++){
        $at=$off+2+$n*12;
        if($read($at,2)===274&&$read($at+2,2)===3&&$read($at+4,4)===1){$v=$read($at+8,2);return $v>=1&&$v<=8?$v:1;}
    }
    return 1;
}

function image_privacy_orientation_only(int $orientation): string {
    return "II\x2a\0\x08\0\0\0\x01\0\x12\x01\x03\0\x01\0\0\0".pack('v',$orientation)."\0\0\0\0\0\0";
}

function image_privacy_strip(string $raw,string $mime): string {
    $size=strlen($raw);
    if($mime==='image/jpeg'){
        if(substr($raw,0,2)!=="\xff\xd8")throw new RuntimeException('Invalid JPEG');
        $out="\xff\xd8";$at=2;$orientation=1;
        while($at<$size){
            if(ord($raw[$at])!==255)throw new RuntimeException('Invalid JPEG marker');
            $start=$at;while($at<$size&&ord($raw[$at])===255)$at++;
            if($at>=$size)throw new RuntimeException('Truncated JPEG');$marker=ord($raw[$at++]);
            if($marker===0xda){
                if($orientation!==1){
                    $exif="Exif\0\0".image_privacy_orientation_only($orientation);
                    $out.="\xff\xe1".pack('n',strlen($exif)+2).$exif;
                }
                $orientation=1;
                if($at+2>$size)throw new RuntimeException('Truncated JPEG scan');
                $len=unpack('n',substr($raw,$at,2))[1];if($len<2||$at+$len>$size)throw new RuntimeException('Invalid JPEG scan');
                $at+=$len;
                while($at<$size){
                    if(ord($raw[$at])!==255){$at++;continue;}
                    $next=$at+1;while($next<$size&&ord($raw[$next])===255)$next++;
                    if($next>=$size)throw new RuntimeException('Truncated JPEG scan');$code=ord($raw[$next]);
                    if($code===0||($code>=0xd0&&$code<=0xd7)){$at=$next+1;continue;}
                    break;
                }
                $out.=substr($raw,$start,$at-$start);continue;
            }
            if($marker===0xd9)return $out."\xff\xd9";
            if($marker===1||($marker>=0xd0&&$marker<=0xd7)){$out.=substr($raw,$start,$at-$start);continue;}
            if($at+2>$size)throw new RuntimeException('Truncated JPEG segment');
            $len=unpack('n',substr($raw,$at,2))[1];if($len<2||$at+$len>$size)throw new RuntimeException('Invalid JPEG length');
            if($marker===0xe1&&substr($raw,$at+2,6)==="Exif\0\0")$orientation=image_privacy_orientation(substr($raw,$at+2,$len-2));
            // APP1: EXIF/XMP; APP13: IPTC; COM: free-text comments.
            if(!in_array($marker,[0xe1,0xed,0xfe],true))$out.=substr($raw,$start,$at+$len-$start);
            $at+=$len;
        }
        throw new RuntimeException('Incomplete JPEG');
    }
    if($mime==='image/png'){
        if(substr($raw,0,8)!=="\x89PNG\r\n\x1a\n")throw new RuntimeException('Invalid PNG');
        $out=substr($raw,0,8);$at=8;
        while($at+12<=$size){
            $len=unpack('N',substr($raw,$at,4))[1];if($len>$size-$at-12)throw new RuntimeException('Invalid PNG length');
            $kind=substr($raw,$at+4,4);
            if($kind==='eXIf'){
                $orientation=image_privacy_orientation(substr($raw,$at+8,$len));
                if($orientation!==1){$tiff=image_privacy_orientation_only($orientation);$out.=pack('N',strlen($tiff)).'eXIf'.$tiff.pack('N',crc32('eXIf'.$tiff));}
            }
            if(!in_array($kind,['eXIf','tEXt','zTXt','iTXt'],true))$out.=substr($raw,$at,$len+12);
            $at+=$len+12;if($kind==='IEND')return $out;
        }
        throw new RuntimeException('Incomplete PNG');
    }
    if($mime==='image/webp'){
        if(substr($raw,0,4)!=='RIFF'||substr($raw,8,4)!=='WEBP')throw new RuntimeException('Invalid WebP');
        $out='WEBP';$at=12;$flagOffset=null;$hasExif=false;$end=unpack('V',substr($raw,4,4))[1]+8;if($end>$size)throw new RuntimeException('Truncated WebP');
        while($at+8<=$end){
            $kind=substr($raw,$at,4);$len=unpack('V',substr($raw,$at+4,4))[1];$total=8+$len+($len%2);
            if($total>$end-$at)throw new RuntimeException('Invalid WebP length');
            $chunk=substr($raw,$at,$total);
            if($kind==='VP8X'&&$len>=10){$flagOffset=strlen($out)+8;$chunk[8]=chr(ord($chunk[8])&~12);}
            if($kind==='EXIF'){
                $orientation=image_privacy_orientation(substr($raw,$at+8,$len));
                if($orientation!==1){$tiff=image_privacy_orientation_only($orientation);$out.='EXIF'.pack('V',strlen($tiff)).$tiff.(strlen($tiff)%2?"\0":'');$hasExif=true;}
            }
            if(!in_array($kind,['EXIF','XMP '],true))$out.=$chunk;
            $at+=$total;
        }
        if($at!==$end)throw new RuntimeException('Invalid WebP chunks');
        if($flagOffset!==null&&$hasExif)$out[$flagOffset]=chr(ord($out[$flagOffset])|8);
        return 'RIFF'.pack('V',strlen($out)).$out;
    }
    if($mime==='image/gif'){
        if(!in_array(substr($raw,0,6),['GIF87a','GIF89a'],true)||$size<13)throw new RuntimeException('Invalid GIF');
        $at=13;if(ord($raw[10])&128)$at+=3*(2**((ord($raw[10])&7)+1));
        if($at>$size)throw new RuntimeException('Invalid GIF palette');$out=substr($raw,0,$at);
        $blocks=function(int &$pos)use($raw,$size): void {
            while($pos<$size){$len=ord($raw[$pos++]);if($len===0)return;if($pos+$len>$size)break;$pos+=$len;}
            throw new RuntimeException('Invalid GIF data blocks');
        };
        while($at<$size){
            $start=$at;$kind=ord($raw[$at++]);
            if($kind===0x3b)return $out."\x3b";
            if($kind===0x21){
                if($at>=$size)throw new RuntimeException('Invalid GIF extension');$label=ord($raw[$at++]);
                $app=substr($raw,$at+1,11);$blocks($at);
                if($label!==0xfe&&($label!==0xff||in_array($app,['NETSCAPE2.0','ANIMEXTS1.0'],true)))$out.=substr($raw,$start,$at-$start);
            }elseif($kind===0x2c){
                if($at+9>$size)throw new RuntimeException('Invalid GIF image');$packed=ord($raw[$at+8]);$at+=9;
                if($packed&128)$at+=3*(2**(($packed&7)+1));if($at>=$size)throw new RuntimeException('Invalid GIF frame');
                $at++;$blocks($at);$out.=substr($raw,$start,$at-$start);
            }else throw new RuntimeException('Invalid GIF block');
        }
        throw new RuntimeException('Incomplete GIF');
    }
    throw new RuntimeException('Unsupported image type');
}
