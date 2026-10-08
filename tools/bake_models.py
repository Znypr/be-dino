"""Bake original triangle geometry to native Roblox wedge models, no asset permissions.
Each triangle becomes two fitted WedgeParts. MeshPart imports remain the optimized option.
"""
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np
from compile_resources import compile_geometry
from generate_resources import Mesh,dinosaur,environment
ROOT=Path(__file__).resolve().parents[1]
# Keep a deliberate low poly silhouette and bound instance cost.
ellipsoid=Mesh.ellipsoid; tube=Mesh.tube
Mesh.ellipsoid=lambda self,c,r,color,rings=4,sides=8:ellipsoid(self,c,r,color,min(rings,2),min(sides,5))
Mesh.tube=lambda self,p,r,color,sides=6:tube(self,p,r,color,min(sides,4))
original_environment=environment
def environment(name):
 if name != 'fern':return original_environment(name)
 m=Mesh()
 for i in range(7):
  a=i*2*np.pi/7
  tip=(2*np.cos(a),1.1,2*np.sin(a));side=(-.35*np.sin(a),0,.35*np.cos(a))
  start=len(m.v);m.v.extend([(0,.15,0),tip,(.8*np.cos(a)+side[0],1.15,.8*np.sin(a)+side[2]),(.8*np.cos(a)-side[0],1.0,.8*np.sin(a)-side[2])])
  mat='m4D997A';m.materials[mat]='#4D997A'
  for tri in ((1,2,3),(1,4,2),(1,3,4),(2,4,3)):m.faces.append((mat,tuple(start+j for j in tri)))
 return m.save(name)
Mesh.ellipsoid=lambda self,c,r,color,rings=3,sides=6:ellipsoid(self,c,r,color,min(rings,3),min(sides,6))
assets=[dinosaur(x) for x in ('compy','triceratops','tyrannosaurus','raptor','stegosaurus','ankylosaurus')]
Mesh.ellipsoid=lambda self,c,r,color,rings=2,sides=5:ellipsoid(self,c,r,color,min(rings,2),min(sides,5))
assets += [environment(x) for x in ('tree','rock','fern','egg','berry','fruit','amber')]
import json
manifest=json.loads((ROOT/'resources/manifest.json').read_text())
for a in assets:
 a['status']='native model packaged; OBJ available for optimized MeshPart import'
 manifest['assets']=[old for old in manifest['assets'] if old['logicalId']!=a['logicalId']]+[a]
manifest['runtimeIntegration']='Native triangle models packaged in ReplicatedStorage.Resources. No runtime Mesh/Image API required.'
(ROOT/'resources/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
geometry=compile_geometry()
def prop(props,kind,name,value):
 e=E.SubElement(props,kind,{'name':name});e.text=str(value);return e
def vector(props,kind,name,value):
 e=E.SubElement(props,kind,{'name':name})
 for k,v in zip('XYZ',value):E.SubElement(e,k).text=f'{v:.7f}'
for name,data in geometry.items():
 root=E.Element('roblox',{'version':'4'});model=E.SubElement(root,'Item',{'class':'Model','referent':'model'})
 props=E.SubElement(model,'Properties');prop(props,'string','Name',name)
 count=0
 for ia,ib,ic,color in data['faces']:
  a,b,c=[np.array(data['vertices'][i-1]) for i in (ia,ib,ic)]
  ab,ac,bc=b-a,c-a,c-b
  if np.dot(ab,ab)>max(np.dot(ac,ac),np.dot(bc,bc)):a,c=c,a
  elif np.dot(ac,ac)>max(np.dot(ab,ab),np.dot(bc,bc)):a,b=b,a
  ab,ac,bc=b-a,c-a,c-b
  right=np.cross(ac,ab);right/=np.linalg.norm(right)
  back=bc/np.linalg.norm(bc);up=np.cross(back,right)
  height=abs(np.dot(ab,up))
  for center,r,z,length in [((a+b)/2,right,back,abs(np.dot(ab,back))),((a+c)/2,-right,-back,abs(np.dot(ac,back)))]:
   if length<1e-6:continue
   count+=1;part=E.SubElement(model,'Item',{'class':'WedgePart','referent':f'{name}{count}'})
   p=E.SubElement(part,'Properties');prop(p,'string','Name',f'Surface{count}')
   vector(p,'Vector3','size',(.01,height,length))
   cf=E.SubElement(p,'CoordinateFrame',{'name':'CFrame'})
   for k,v in zip('XYZ',center):E.SubElement(cf,k).text=f'{v:.7f}'
   mat=np.column_stack((r,up,z))
   for i in range(3):
    for j in range(3):E.SubElement(cf,f'R{i}{j}').text=f'{mat[i,j]:.7f}'
   rgb=[round(v*255) for v in data['colors'][color-1]]
   prop(p,'Color3uint8','Color3uint8',(255<<24)|(rgb[0]<<16)|(rgb[1]<<8)|rgb[2])
   for k,val in [('Anchored','true'),('CanCollide','false'),('CanTouch','false'),('CanQuery','false'),('Massless','true'),('CastShadow','true')]:prop(p,'bool',k,val)
   prop(p,'token','Material',272)
 E.indent(root);(ROOT/'resources/roblox'/f'{name}.rbxmx').write_bytes(E.tostring(root,encoding='utf-8',xml_declaration=True))
 print(name,count,'native surfaces')
