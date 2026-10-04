"""Raster exports of original SVG icons and inspectable renders of the actual mesh sources."""
from pathlib import Path
import re, xml.etree.ElementTree as ET
import numpy as np
from PIL import Image, ImageDraw
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT=Path(__file__).resolve().parents[1]

def svg_icon(path):
    root=ET.parse(path).getroot();image=Image.new('RGBA',(1024,1024));draw=ImageDraw.Draw(image)
    def scaled(points):return [(x*8,y*8) for x,y in points]
    for e in root.iter():
        tag=e.tag.split('}')[-1]
        if tag=='circle':
            x,y,r=[float(e.attrib[k]) for k in ('cx','cy','r')]
            draw.ellipse(((x-r)*8,(y-r)*8,(x+r)*8,(y+r)*8),fill=e.attrib.get('fill','#173c42'));continue
        if tag!='path':continue
        tokens=re.findall(r'[A-Za-z]|-?\d+(?:\.\d+)?',e.attrib['d']);i=0;command=None;point=(0,0);paths=[];points=[]
        def num():
            nonlocal i
            v=float(tokens[i]);i+=1;return v
        while i<len(tokens):
            if tokens[i].isalpha():command=tokens[i];i+=1
            if command=='Z':
                points.append(points[0]);paths.append(points);points=[];command=None;continue
            if command=='M':
                if points:paths.append(points)
                point=(num(),num());points=[point];command='L'
            elif command=='L':point=(num(),num());points.append(point)
            elif command=='H':point=(num(),point[1]);points.append(point)
            elif command=='V':point=(point[0],num());points.append(point)
            elif command in ('Q','C'):
                start=point;a=(num(),num());b=(num(),num());c=(num(),num()) if command=='C' else None
                for t in np.linspace(0,1,25)[1:]:
                    if c:point=tuple((1-t)**3*start[k]+3*(1-t)**2*t*a[k]+3*(1-t)*t*t*b[k]+t**3*c[k] for k in (0,1))
                    else:point=tuple((1-t)**2*start[k]+2*(1-t)*t*a[k]+t*t*b[k] for k in (0,1))
                    points.append(point)
            else:raise ValueError(command)
        if points:paths.append(points)
        for points in paths:
            pts=scaled(points);fill=e.attrib.get('fill','#173c42');stroke=e.attrib.get('stroke','#173c42');width=int(float(e.attrib.get('stroke-width',5))*8)
            if fill!='none':draw.polygon(pts,fill=fill)
            if stroke!='none':draw.line(pts,fill=stroke,width=width,joint='curve')
            if e.attrib.get('stroke-linecap')=='round':
                for x,y in (pts[0],pts[-1]):draw.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=stroke)
    image.resize((256,256),Image.Resampling.LANCZOS).save(path.with_suffix('.png'))

def read_mesh(name):
    folder=ROOT/'resources/models';colors={};material=None
    for line in (folder/(name+'.mtl')).read_text().splitlines():
        if line.startswith('newmtl '):material=line.split()[1]
        if line.startswith('Kd '):colors[material]=tuple(map(float,line.split()[1:]))
    vertices=[];faces=[];facecolors=[]
    for line in (folder/(name+'.obj')).read_text().splitlines():
        if line.startswith('v '):vertices.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('usemtl '):material=line.split()[1]
        elif line.startswith('f '):faces.append([int(x)-1 for x in line.split()[1:]]);facecolors.append(colors[material])
    v=np.array(vertices);polys=v[np.array(faces)]
    normals=np.cross(polys[:,1]-polys[:,0],polys[:,2]-polys[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
    light=np.array([.4,.8,-.6]);light/=np.linalg.norm(light)
    colors=np.array(facecolors)*(.55+.45*np.clip(normals@light,0,1)[:,None])
    return polys[:,:,[0,2,1]],colors

def render():
    for p in (ROOT/'resources/ui/icons').glob('*.svg'):svg_icon(p)
    folder=ROOT/'resources/concepts';folder.mkdir(exist_ok=True)
    fig=plt.figure(figsize=(15,5),facecolor='#122831')
    for index,name in enumerate(('compy','triceratops','tyrannosaurus')):
        ax=fig.add_subplot(1,3,index+1,projection='3d');polys,colors=read_mesh(name)
        ax.add_collection3d(Poly3DCollection(polys,facecolors=colors,edgecolors='none'))
        ax.set(xlim=(-4.3,4.3),ylim=(-4.3,5.6),zlim=(0,7));ax.set_box_aspect((8.6,9.9,7));ax.view_init(18,-53);ax.set_axis_off();ax.set_facecolor('#122831')
        ax.set_title(name.upper(),color='#eff9e7',fontweight='bold',pad=-8)
    fig.suptitle('BE DINO  /  ORIGINAL MESH SOURCES',color='#80cda9',fontsize=20,fontweight='bold')
    fig.subplots_adjust(wspace=0,left=0,right=1,bottom=0,top=.9)
    fig.savefig(folder/'mesh-lineup.png',dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
if __name__=='__main__':render()
