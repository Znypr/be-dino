"""Compile transparent PNGs into merged GUI rectangles for permission-free previews.
Production can bind the same logical IDs to uploaded ImageLabels instead.
"""
from pathlib import Path
from PIL import Image
from compile_resources import lua
ROOT=Path(__file__).resolve().parents[1]
assets={}
paths={p.stem:p for p in (ROOT/'resources/ui/icons').glob('*.png')}
paths.update({p.stem:p for p in (ROOT/'resources/ui/v2/icons').glob('*.png')})
for name,p in paths.items():
 size=32
 im=Image.open(p).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
 alpha=im.getchannel('A')
 rgb=im.convert('RGB').quantize(colors=24,method=Image.Quantize.MEDIANCUT).convert('RGB')
 palette=[];rows=[]
 for y in range(size):
  row=[];x=0
  while x<size:
   if alpha.getpixel((x,y))<100:x+=1;continue
   color=rgb.getpixel((x,y))
   if color not in palette:palette.append(color)
   idx=palette.index(color)+1;start=x;x+=1
   while x<size and alpha.getpixel((x,y))>=100 and rgb.getpixel((x,y))==color:x+=1
   row.append([start,y,x-start,1,idx])
  rows.append(row)
 tiles=[];pending={}
 for row in rows:
  current={}
  for rect in row:
   key=(rect[0],rect[2],rect[4])
   if key in pending:old=pending.pop(key);old[3]+=1;current[key]=old
   else:current[key]=rect
  tiles.extend(pending.values());pending=current
 tiles.extend(pending.values())
 assets[name]={'size':size,'colors':[list(c) for c in palette],'tiles':tiles}
 print(name,len(tiles),'GUI rectangles')
(ROOT/'src/shared/IconTiles.luau').write_text('--!strict\n-- Generated exact quantized native icon tiles.\nreturn '+lua(assets)+'\n')
