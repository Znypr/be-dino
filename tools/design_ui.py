"""Original Be Dino UI sources/exports, driven by the native UI palette."""
from pathlib import Path
import json, math
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'resources/ui'
NAVY='#102a38';TEAL='#214756';MINT='#78d8a7';GOLD='#f6ca77';CREAM='#fff7db'
def font(size,bold=True):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
def rgb(h):return tuple(bytes.fromhex(h.lstrip('#')))
def panel(size,top,bottom,radius=20):
 w,h=size;image=Image.new('RGBA',size);mask=Image.new('L',size);d=ImageDraw.Draw(mask);d.rounded_rectangle((3,3,w-4,h-4),radius=radius,fill=255)
 grad=Image.new('RGBA',size);g=ImageDraw.Draw(grad);a,b=rgb(top),rgb(bottom)
 for y in range(h):g.line((0,y,w,y),fill=tuple(round(a[i]+(b[i]-a[i])*y/(h-1)) for i in range(3))+(255,))
 image.paste(grad,(0,0),mask);d=ImageDraw.Draw(image);d.rounded_rectangle((3,3,w-4,h-4),radius=radius,outline=NAVY,width=5);d.rounded_rectangle((10,10,w-11,h-11),radius=max(3,radius-5),outline='#6596a0',width=1)
 d.line((radius+6,12,w-radius-6,12),fill='#a6cbc7',width=2)
 return image
def component(name,size,top,bottom,radius=20):
 p=OUT/'components';p.mkdir(exist_ok=True);image=panel(size,top,bottom,radius);image.save(p/(name+'.png'))
 w,h=size
 (p/(name+'.svg')).write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><linearGradient id="g" x2="0" y2="1"><stop stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient></defs><rect x="3" y="3" width="{w-6}" height="{h-6}" rx="{radius}" fill="url(#g)" stroke="{NAVY}" stroke-width="5"/><rect x="10" y="10" width="{w-20}" height="{h-20}" rx="{radius-5}" fill="none" stroke="#6596a0"/></svg>''')
 return image

def icon_extra():
 icons={
 'settings':'<path d="M54 15H74L78 30L91 37L106 33L116 51L104 62V76L116 86L106 104L90 99L78 107L74 121H54L49 107L36 100L21 105L11 87L23 76V62L11 51L21 33L36 38L49 30Z" fill="#79cbaa"/><circle cx="64" cy="68" r="20" fill="#173c42"/>',
 'shop':'<path d="M25 25H103L111 58H17Z" fill="#f6ca77"/><path d="M25 61V105H103V61M45 105V77H70V105" fill="#78cbaa"/>',
 'lock':'<path d="M39 56V38C39 9 89 9 89 38V56" fill="none" stroke="#ffe9b9" stroke-width="12"/><path d="M26 53H102V109H26Z" fill="#f6ca77"/><circle cx="64" cy="76" r="8" fill="#173c42"/><path d="M61 78H67V94H61Z" fill="#173c42"/>',
 'trophy':'<path d="M38 20H90V53C90 84 38 84 38 53Z" fill="#f6ca77"/><path d="M37 30H17V48Q17 66 40 66M91 30H111V48Q111 66 88 66" fill="none" stroke="#f6ca77" stroke-width="9"/><path d="M59 75H69V95H88V109H40V95H59Z" fill="#f6ca77"/>',
 'bolt':'<path d="M66 12L27 72H56L48 116L104 51H72L86 12Z" fill="#f6ca77"/>',
 'gift':'<path d="M20 55H108V110H20Z" fill="#78cbaa"/><path d="M15 42H113V62H15Z" fill="#9ce3c0"/><path d="M57 43H72V110H57Z" fill="#f6ca77"/><path d="M63 43C8 49 31 4 49 18L63 40C70 5 113 19 87 37Z" fill="#f6ca77"/>',
 'snow':'<path d="M64 17V111M22 40L106 88M22 88L106 40M51 25L64 36L78 25M51 102L64 91L78 102M27 55L39 49L39 35M90 101L90 87L102 81M27 81L39 88L39 102M90 35L90 49L102 55" fill="none" stroke="#b1e8ef" stroke-width="7" stroke-linecap="round"/>',
 'play':'<path d="M42 22L103 64L42 106Z" fill="#78cbaa"/>',
 }
 for name,body in icons.items():
  (OUT/'icons'/(name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 128 128"><g stroke="#173c42" stroke-width="5" stroke-linejoin="round">{body}</g></svg>')
 from render_resources import svg_icon
 for p in (OUT/'icons').glob('*.svg'):svg_icon(p)

def mesh_portrait(name):
 from render_resources import read_mesh
 import matplotlib.pyplot as plt
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 fig=plt.figure(figsize=(4,4));ax=fig.add_subplot(111,projection='3d');polys,colors=read_mesh(name)
 ax.add_collection3d(Poly3DCollection(polys,facecolors=colors,edgecolors='none'))
 ax.set(xlim=(-3.5,3.5),ylim=(-4,5.5),zlim=(0,6));ax.set_box_aspect((7,9.5,6),zoom=1.75);ax.view_init(15,-53);ax.set_axis_off();fig.subplots_adjust(0,0,1,1);fig.savefig(OUT/'previews'/(name+'.png'),dpi=160,transparent=True);plt.close(fig)

def build():
 icon_extra()
 components={
 'popup-panel':((650,440),'#315e6e','#182f40',24),
 'collection-card':((196,286),'#37687a','#203e50',18),
 'button-primary':((208,56),'#a0ecc0','#55ad87',15),
 'button-gold':((208,56),'#ffe3a1','#c99a43',15),
 'button-danger':((208,56),'#ec8e83','#ab5057',15),
 'button-secondary':((208,56),'#54889b','#315563',15),
 'rarity-common':((168,36),'#91e7b4','#59a480',12),
 'rarity-rare':((168,36),'#a0d9fb','#4e91c0',12),
 'rarity-legendary':((168,36),'#ffe0a0','#c49548',12),
 }
 for name,(size,a,b,r) in components.items():component(name,size,a,b,r)
 logo=Image.new('RGBA',(800,200));d=ImageDraw.Draw(logo);d.text((400,85),'BE DINO!',font=font(104),anchor='mm',fill=CREAM,stroke_width=8,stroke_fill=NAVY);d.text((400,150),'GROW  •  COLLECT  •  EVOLVE',font=font(22),anchor='mm',fill=MINT);logo.save(OUT/'components/be-dino-logo.png')
 for species in ('compy','triceratops','tyrannosaurus'):mesh_portrait(species)
 # A design preview, explicitly not an in-game screenshot.
 bg=Image.open(OUT/'backgrounds/prehistoric-island.png').convert('RGBA').resize((1440,810));dark=Image.new('RGBA',bg.size,(10,26,36,140));bg=Image.alpha_composite(bg,dark)
 shell=panel((1050,650),'#315e6e','#182f40',30);bg.alpha_composite(shell,(195,80));d=ImageDraw.Draw(bg);d.text((240,124),'YOUR DINOSAURS',font=font(32),fill=CREAM);d.text((240,172),'Choose your dino. Collect copies to unlock Gold.',font=font(17,False),fill='#b8d2d6')
 for i,(name,label,rarity) in enumerate([('compy','Compy','COMMON'),('triceratops','Triceratops','RARE'),('tyrannosaurus','T-Rex','LEGENDARY')]):
  x=238+i*330;bg.alpha_composite(panel((308,450),'#37687a','#203e50',20),(x,220))
  icon=Image.open(OUT/'previews'/(name+'.png')).resize((300,300));bg.alpha_composite(icon,(x+4,223))
  d=ImageDraw.Draw(bg);d.text((x+154,246),rarity,font=font(14),anchor='mm',fill=(MINT,'#a0d9fb',GOLD)[i]);d.text((x+154,475),label,font=font(24),anchor='mm',fill=CREAM);d.text((x+154,511),('12 base   /   0 Gold','3 base   /   0 Gold','0 base   /   0 Gold')[i],font=font(15,False),anchor='mm',fill='#bad5d7')
  for y,text,a,b in [(542,'EQUIPPED' if i==0 else 'EQUIP' if i==1 else 'LOCKED','#a0ecc0','#55ad87'),(606,'MAKE GOLD','#ffe3a1','#c99a43')]:
   bg.alpha_composite(panel((276,48),a,b,12),(x+16,y));d=ImageDraw.Draw(bg);d.text((x+154,y+24),text,font=font(17),anchor='mm',fill=NAVY)
 d.text((720,766),'DESIGN PREVIEW  •  ORIGINAL ASSETS  •  NOT A STUDIO SCREENSHOT',font=font(14),anchor='mm',fill=CREAM);bg.save(OUT/'previews/collection-menu.png')
 sheet=Image.new('RGB',(1440,1030),'#122831');d=ImageDraw.Draw(sheet);d.text((44,35),'BE DINO  /  REUSABLE UI ASSETS',font=font(34),fill=CREAM)
 icons=sorted((OUT/'icons').glob('*.png'))
 for i,p in enumerate(icons):
  x=42+(i%7)*196;y=118+(i//7)*170;im=Image.open(p).resize((112,112));sheet.paste(im,(x+26,y),im);d.text((x+83,y+132),p.stem.upper(),font=font(13),anchor='mm',fill='#bad5d7')
 y=495
 for i,name in enumerate(components):
  x=45+(i%3)*465;yy=y+(i//3)*155;im=Image.open(OUT/'components'/(name+'.png'));im.thumbnail((390,104));sheet.paste(im,(x,yy),im);d.text((x,yy+110),name,font=font(14),fill=CREAM)
 sheet.save(OUT/'previews/asset-sheet.png')
 config={'palette':{'outline':NAVY,'panel':TEAL,'primary':MINT,'gold':GOLD,'text':CREAM},'nineSliceInset':24,'components':list(components),'icons':[p.stem for p in icons],'loadingBackground':'backgrounds/prehistoric-island.png','referencePatterns':'Collection card hierarchy, dimensional popup shells, large primary actions. Original artwork; no extracted game assets.'}
 (OUT/'design-system.json').write_text(json.dumps(config,indent=2)+'\n')
 # Raw icon pixels compressed into runs, consumed by EditableImage without uploaded IDs.
 rasters={}
 for p in icons:
  im=Image.open(p).convert('RGBA').resize((64,64),Image.Resampling.LANCZOS);runs=[];prev=None;count=0
  for rgba in im.getdata():
   value=sum(c<<(8*i) for i,c in enumerate(rgba))
   if value==prev:count+=1
   else:
    if count:runs.extend([count,prev])
    prev=value;count=1
  runs.extend([count,prev]);rasters[p.stem]=runs
 lua='--!strict\n-- Generated RGBA run data from resources/ui/icons PNG files.\nreturn {'+','.join('['+json.dumps(k)+']={'+','.join(map(str,v))+'}' for k,v in rasters.items())+'}\n'
 (ROOT/'src/shared/IconRaster.luau').write_text(lua)
if __name__=='__main__':build()
