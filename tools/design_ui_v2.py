"""Original editable component exports and review sheet for the implemented UI v2."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import math,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'resources/ui/v2'
COLORS={'green':'#5ded1f','blue':'#2eceff','gold':'#ffd22b','purple':'#c256ff','red':'#f73930','dark':'#2a2835'}
def font(n):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',n)
def text(d,xy,value,n=32,color='white',anchor=None):d.text(xy,value,font=font(n),fill=color,stroke_width=max(1,n//16),stroke_fill='#0d0f14',anchor=anchor)
def component(name,w,h,color):
 p=OUT/'components';p.mkdir(parents=True,exist_ok=True)
 im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);c=tuple(bytes.fromhex(color[1:]))
 for y in range(4,h-4):
  v=1-.28*y/h;d.line((4,y,w-5,y),fill=tuple(int(x*v) for x in c)+(255,))
 d.rounded_rectangle((2,2,w-3,h-3),radius=7,outline='#0d0f14',width=5)
 d.rounded_rectangle((9,9,w-10,h-10),radius=3,outline=tuple(min(255,x+40) for x in c)+(180,),width=2)
 for x in range(16,w-8,24):
  for y in range(16,h-8,24):
   d.rectangle((x,y,x+6,y+6),outline=tuple(max(0,int(v*.65)) for v in c)+(150,),width=1)
 im.save(p/(name+'.png'))
 # Individually editable SVG source matching PNG visual structure.
 studs=''.join(f'<rect x="{x}" y="{y}" width="6" height="6" fill="none" stroke="#000" opacity=".12"/>' for x in range(16,w-8,24) for y in range(16,h-8,24))
 (p/(name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><defs><linearGradient id="g" x2="0" y2="1"><stop stop-color="{color}"/><stop offset="1" stop-color="{color}" stop-opacity=".72"/></linearGradient></defs><rect x="3" y="3" width="{w-6}" height="{h-6}" rx="7" fill="url(#g)" stroke="#0d0f14" stroke-width="5"/>{studs}</svg>')
 return im
for name,color in COLORS.items():
 component('header-'+name,852,78,color)
 component('button-'+name,300,68,color)
for rarity,color in [('common',COLORS['green']),('rare',COLORS['blue']),('legendary',COLORS['gold'])]:component('card-'+rarity,264,328,color)
component('popup-body',860,520,COLORS['dark']);component('progress-track',600,34,'#13151e')
close=component('close',72,72,COLORS['red']);d=ImageDraw.Draw(close);text(d,(36,35),'X',47,anchor='mm');close.save(OUT/'components/close.png')
(OUT/'components/close.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72"><rect x="3" y="3" width="66" height="66" rx="5" fill="#f73930" stroke="#0d0f14" stroke-width="5"/><path d="M22 20L50 52M50 20L22 52" stroke="#0d0f14" stroke-width="13"/><path d="M22 20L50 52M50 20L22 52" stroke="white" stroke-width="8"/></svg>')
burst=Image.new('RGBA',(512,512));d=ImageDraw.Draw(burst)
for i in range(16):
 a=i*math.tau/16
 points=[(256,256),(256+250*math.cos(a),256+250*math.sin(a)),(256+250*math.cos(a+.12),256+250*math.sin(a+.12))]
 d.polygon(points,fill=(255,222,70,85))
burst.save(OUT/'components/reward-burst.png')
# Asset index contact sheet, explicitly a design artifact.
sheet=Image.new('RGB',(1400,920),'#22212d');d=ImageDraw.Draw(sheet)
text(d,(35,25),'BE DINO / ORIGINAL UI ASSETS',44)
text(d,(35,86),'Individual transparent icons + reusable components',22,color='#2eceff')
for i,p in enumerate(sorted((OUT/'icons').glob('*.png'))):
 x=35+(i%4)*345;y=145+(i//4)*250
 icon=Image.open(p).convert('RGBA');icon.thumbnail((200,200));sheet.paste(icon,(x+60,y),icon);text(d,(x+160,y+212),p.stem.upper(),22,anchor='mm')
for i,name in enumerate(('green','blue','gold','purple')):
 im=Image.open(OUT/f'components/button-{name}.png');sheet.paste(im,(35+i*345,716),im)
 text(d,(185+i*345,750),name.upper(),24,anchor='mm')
text(d,(35,835),'Original Be Dino art. References are stored separately.',22)
(OUT/'previews').mkdir(exist_ok=True);sheet.save(OUT/'previews/asset-sheet.png')
# Collection layout review, matching runtime dimensions. Not an engine screenshot.
ui=Image.open(OUT/'components/popup-body.png').convert('RGBA')
header=Image.open(OUT/'components/header-blue.png');ui.alpha_composite(header,(4,4));d=ImageDraw.Draw(ui);text(d,(26,18),'Dino Index',40)
ui.alpha_composite(close.resize((62,62)),(782,12))
for i,(name,rarity) in enumerate(zip(('compy','triceratops','tyrannosaurus'),('common','rare','legendary'))):
 card=Image.open(OUT/f'components/card-{rarity}.png');x=18+i*276;ui.alpha_composite(card,(x,98));d=ImageDraw.Draw(ui)
 text(d,(x+132,112),{'compy':'Compy','triceratops':'Triceratops','tyrannosaurus':'T-Rex'}[name],26,anchor='mt');text(d,(x+132,145),rarity.title(),18,anchor='mt')
 portrait=Image.open(ROOT/f'resources/ui/previews/{name}.png');portrait.thumbnail((264,200));ui.alpha_composite(portrait,(x+(264-portrait.width)//2,161))
 btn=Image.open(OUT/'components/button-dark.png').resize((240,38));ui.alpha_composite(btn,(x+12,379));d=ImageDraw.Draw(ui);text(d,(x+132,386),'VIEW DINO',21,anchor='mt')
progress=Image.open(OUT/'components/progress-track.png');ui.alpha_composite(progress,(18,454));d=ImageDraw.Draw(ui);text(d,(318,458),'Discovered: 1 / 3',23,anchor='mt')
ui.save(OUT/'previews/dino-index-design.png')
print('Exported 19 component PNGs, editable SVGs and two design review sheets')
