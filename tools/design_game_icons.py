"""Original scalable icon geometry shared by Roblox GUI and SVG/PNG exports."""
from pathlib import Path
import json,cairosvg
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'resources/ui/v2/scalable';OUT.mkdir(parents=True,exist_ok=True)
D={};S=[]
def rect(x,y,w,h,c,r=0,rot=0):S.append(dict(x=x,y=y,w=w,h=h,color=c,radius=r,rotation=rot))
def circle(x,y,w,h,c):rect(x,y,w,h,c,min(w,h)/2)
def line(x,y,w,h,c,rot=0):rect(x,y,w,h,c,h/2,rot)
def start(k):
 global S;S=[];D[k]=S
gold='#FFC842';white='#FFF5DA';dark='#142035';green='#62EC70';blue='#50D6FF';purple='#B46AFF'
start('home');rect(21,41,60,47,dark,5);rect(25,43,52,41,gold,3);line(6,31,53,13,dark,-42);line(42,31,53,13,dark,42);line(9,30,50,8,'#FF8642',-42);line(42,30,50,8,'#FF8642',42);rect(34,59,15,28,dark,6);rect(59,53,16,18,dark,2);rect(62,56,10,12,blue,1);line(29,48,42,4,white);rect(72,17,9,22,dark,2)
start('trophy');circle(7,25,31,36,dark);circle(12,29,23,26,gold);circle(17,34,14,15,dark);circle(62,25,31,36,dark);circle(66,29,23,26,gold);circle(70,34,14,15,dark);rect(24,19,52,44,dark,10);rect(29,23,42,35,gold,12);rect(45,57,10,20,dark,2);rect(40,59,20,17,gold,3);rect(27,74,46,15,dark,3);rect(31,77,38,8,gold,2);circle(36,29,12,12,white);line(34,23,28,4,white)
start('egg');circle(22,9,56,84,dark);circle(27,14,46,74,white);circle(30,49,14,19,'#37B776');circle(49,23,13,17,'#37B776');circle(54,67,13,12,'#37B776');circle(37,20,9,15,'#FFFFFF')
start('amber');line(32,21,23,62,dark,-10);line(35,24,17,55,gold,-10);line(57,34,22,52,dark,18);line(60,37,16,46,'#FF9F32',18);line(17,48,20,37,dark,-25);line(20,51,14,30,gold,-25);line(38,28,5,45,white,-10);circle(68,15,7,7,white);line(6,28,16,5,white,45)
start('dinos');circle(18,30,65,44,dark);circle(22,33,56,37,green);rect(49,48,42,22,dark,8);rect(52,50,35,16,'#A8F588',6);circle(39,24,33,33,dark);circle(43,28,25,24,green);circle(50,32,13,15,white);circle(57,35,5,9,dark);rect(56,67,8,9,white,1);rect(70,66,8,9,white,1);line(17,30,12,11,'#28A77F',-25);line(19,57,12,11,'#28A77F',25)
start('fusion');circle(12,13,76,76,dark);circle(17,18,66,66,purple);circle(27,28,46,46,dark);circle(32,33,36,36,gold);line(41,39,18,8,white,-45);line(11,45,20,10,gold,-35);line(69,45,20,10,gold,35)
start('shield');rect(17,15,66,65,dark,19);rect(22,20,56,55,green,17);rect(28,25,44,43,blue,13);line(29,43,24,9,white,45);line(44,39,30,9,white,-45)
start('aura');circle(7,10,86,80,dark);circle(12,15,76,70,purple);circle(20,23,60,54,dark);circle(28,31,44,38,blue);circle(36,39,28,22,white);circle(73,5,12,12,gold);circle(7,74,10,10,gold)
start('leap');line(12,61,64,16,dark,-35);line(16,59,57,10,blue,-35);line(58,16,30,13,dark,45);line(60,19,25,8,blue,45);line(73,29,10,30,dark,0);line(74,30,6,25,blue,0);line(7,76,35,6,white,-35);line(3,61,22,5,white,-35)
for k in ('rain','thunder','blizzard','weather'):
 start(k);circle(10,30,40,35,dark);circle(31,17,42,46,dark);circle(57,30,32,35,dark);rect(17,44,64,20,dark,8);circle(15,34,32,26,white);circle(36,22,32,36,white);circle(61,35,23,23,white);rect(20,46,60,13,white,5)
 if k=='rain':
  for x in (24,46,68):line(x,68,7,20,blue,20)
 elif k=='thunder':line(42,58,12,23,gold,25);line(44,73,12,23,gold,25);line(38,72,23,9,gold)
 elif k=='blizzard':
  for a in (0,60,120):line(34,77,32,6,blue,a)
 else:rect(43,59,14,20,purple,5);circle(47,83,7,7,purple)
for k,c in [('potion',purple),('speed',blue),('growth',green)]:
 start(k);rect(36,7,28,13,dark,3);rect(40,9,20,8,gold,2);rect(38,18,24,24,dark,3);rect(43,20,14,23,white,2);circle(19,34,62,59,dark);circle(24,39,52,49,white);circle(27,49,46,36,c);circle(35,48,11,16,'#FFFFFF');circle(58,65,7,7,white)
start('clock');circle(9,9,82,82,dark);circle(15,15,70,70,gold);circle(22,22,56,56,white);line(47,30,7,27,dark);line(48,49,25,7,dark);circle(45,45,12,12,dark)
start('leaf');circle(17,18,65,61,dark);circle(22,22,55,51,green);line(27,45,51,8,white,-40);line(26,63,8,27,dark,20)
start('lock');circle(27,7,46,55,dark);circle(34,15,32,40,gold);circle(41,22,18,32,dark);rect(19,43,62,45,dark,7);rect(24,48,52,35,gold,5);circle(44,55,12,12,dark);rect(47,64,6,12,dark,2)
start('check');line(17,49,34,15,dark,45);line(39,42,51,15,dark,-45);line(20,50,29,9,green,45);line(41,42,46,9,green,-45)
(OUT/'geometry.json').write_text(json.dumps(D,indent=2)+'\n')
for k,shapes in D.items():
 body='<defs><linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="white" stop-opacity="0"/><stop offset="1" stop-color="#233454" stop-opacity=".23"/></linearGradient></defs>'
 for s in shapes:
  x,y,w,h=s['x'],s['y'],s['w'],s['h'];c=s['color'];r=s['radius'];a=s['rotation']
  element=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{c}" transform="rotate({a} {x+w/2} {y+h/2})"/>'
  body+=element
  if c!='#142035':body+=element.replace(f'fill="{c}"','fill="url(#sheen)"')
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{body}</svg>'
 (OUT/f'{k}.svg').write_text(svg)
 cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT/f'{k}.png'),output_width=512,output_height=512)
# Lua shape data uses normalized geometry and real GUI corners, not raster tiles.
def lua(v):
 if isinstance(v,dict):return '{'+','.join('['+json.dumps(k)+']='+lua(x) for k,x in v.items())+'}'
 if isinstance(v,list):return '{'+','.join(lua(x) for x in v)+'}'
 if isinstance(v,str):return json.dumps(v)
 return str(v)
(ROOT/'src/shared/IconVectors.luau').write_text('--!strict\n-- Generated by tools/design_game_icons.py; original scalable primitives.\nreturn '+lua(D)+'\n')
print(len(D),'scalable icons exported as individual 512px PNG/SVG assets')
