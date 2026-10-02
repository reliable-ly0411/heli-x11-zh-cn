"""Extend original BMFont resources locally, preserving their Latin metrics."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import re, zipfile, io

def add_fonts(out, root, chars, fontfile, font_index):
    report = []
    for jar in ['libs/jme/styles.zip','libs/HeliX/HeliX11.jar']:
     with zipfile.ZipFile(root/jar) as z:
      for name in z.namelist():
       if not name.endswith('.fnt'):continue
       lines=z.read(name).decode('utf8').splitlines()
       common=next(l for l in lines if l.startswith('common ')); info=lines[0]
       vals=dict(re.findall(r'(\w+)=(-?\d+)',common));w=int(vals['scaleW']);h=int(vals['scaleH']);pages=int(vals['pages']);base=int(vals['base']);lineh=int(vals['lineHeight'])
       size=int(re.search(r' size=(-?\d+)',info)[1]); fs=max(10,min(abs(size)-2,lineh-2))
       font=ImageFont.truetype(fontfile,fs,index=font_index)
       retained=[l for l in lines if l.startswith('char ') and int(re.search(r'id=(-?\d+)',l)[1]) not in chars]
       page_lines=[l for l in lines if l.startswith('page ')];newchars=[];canvas=None;x=y=row=0;pageid=pages-1
       prefix=Path(name).stem+'_SC'
       def savepage():
        buf=io.BytesIO();canvas.save(buf,format='PNG');out.writestr(str(Path(name).parent/f'{prefix}_{pageid}.png'),buf.getvalue())
       for cp in chars:
        c=chr(cp);bbox=font.getbbox(c,anchor='ls');left,top,right,bottom=bbox;cw=right-left;ch=bottom-top
        if cw+2>w or ch+2>h:raise ValueError(name)
        if canvas is None or y+ch+2>h:
         if canvas is not None:savepage()
         pageid+=1;canvas=Image.new('RGBA',(w,h),(255,255,255,0));x=y=row=1
         page_lines.append(f'page id={pageid} file="{prefix}_{pageid}.png"')
        if x+cw+2>w:
         x=1;y+=row+2;row=0
         if y+ch+2>h:
          savepage();pageid+=1;canvas=Image.new('RGBA',(w,h),(255,255,255,0));x=y=row=1
          page_lines.append(f'page id={pageid} file="{prefix}_{pageid}.png"')
        ImageDraw.Draw(canvas).text((x-left,y-top),c,font=font,anchor='ls',fill=(255,255,255,255))
        # Keep CJK glyphs inside the original line box, aligned with Latin baseline.
        off=max(0,min(base+top,lineh-ch))
        newchars.append(f'char id={cp} x={x} y={y} width={cw} height={ch} xoffset={left} yoffset={off} xadvance={round(font.getlength(c))} page={pageid} chnl=15')
        x+=cw+2;row=max(row,ch)
       if canvas is not None:savepage()
       common=re.sub(r'pages=\d+',f'pages={pageid+1}',common)
       kern=[l for l in lines if l.startswith(('kernings ','kerning '))]
       out.writestr(name,'\n'.join([info,common]+page_lines+[f'chars count={len(retained)+len(newchars)}']+retained+newchars+kern)+'\n')
       report.append({'font':name,'lineHeight':lineh,'chinesePixelSize':fs,'chineseGlyphs':len(chars),'newPages':pageid+1-pages})
    return report
