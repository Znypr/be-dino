"""Original, deterministic low-poly mesh and UI source assets; no external packages."""
from pathlib import Path
import json, math
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'resources'
class Mesh:
    def __init__(self): self.v=[]; self.faces=[]; self.materials={}
    def ellipsoid(self, center, radius, color, rings=6, sides=12):
        start=len(self.v); name='m'+color.replace('#',''); self.materials[name]=color
        # One vertex at each pole, avoiding degenerate triangles.
        self.v.append((center[0],center[1]+radius[1],center[2]))
        for r in range(1,rings):
            a=math.pi*r/rings
            for j in range(sides):
                b=2*math.pi*j/sides
                self.v.append(tuple(center[k]+radius[k]*q for k,q in enumerate((math.sin(a)*math.cos(b),math.cos(a),math.sin(a)*math.sin(b)))))
        bottom=len(self.v); self.v.append((center[0],center[1]-radius[1],center[2]))
        def face(a,b,c): self.faces.append((name,(a+1,b+1,c+1)))
        for j in range(sides): face(start,start+1+(j+1)%sides,start+1+j)
        for r in range(rings-2):
            for j in range(sides):
                a=start+1+r*sides+j;b=start+1+r*sides+(j+1)%sides;c=a+sides;d=b+sides
                face(a,b,c);face(b,d,c)
        end=start+1+(rings-2)*sides
        for j in range(sides): face(end+j,end+(j+1)%sides,bottom)
    def tube(self, points, radii, color, sides=10):
        start=len(self.v); name='m'+color.replace('#','');self.materials[name]=color
        for i,p in enumerate(points):
            # Cross sections perpendicular to segment direction.
            q=points[min(i+1,len(points)-1)] if i<len(points)-1 else points[i-1]
            direction=[q[k]-p[k] for k in range(3)]
            if i==len(points)-1: direction=[-x for x in direction]
            norm=math.sqrt(sum(x*x for x in direction));d=[x/norm for x in direction]
            ref=(0,1,0) if abs(d[1])<0.9 else (1,0,0)
            cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
            u=cross(d,ref);n=math.sqrt(sum(x*x for x in u));u=[x/n for x in u];v=cross(d,u)
            for j in range(sides):
                a=2*math.pi*j/sides;self.v.append(tuple(p[k]+radii[i]*(u[k]*math.cos(a)+v[k]*math.sin(a)) for k in range(3)))
        def face(a,b,c):self.faces.append((name,(a+1,b+1,c+1)))
        for i in range(len(points)-1):
            for j in range(sides):
                a=start+i*sides+j;b=start+i*sides+(j+1)%sides;c=a+sides;e=b+sides
                face(a,b,c);face(b,e,c)
        for j in range(1,sides-1):
            face(start,start+j+1,start+j)
            end=start+(len(points)-1)*sides;face(end,end+j,end+j+1)
    def save(self,name):
        folder=OUT/'models';folder.mkdir(parents=True,exist_ok=True)
        lines=[f'mtllib {name}.mtl',f'o {name}']+[f'v {x:.5f} {y:.5f} {z:.5f}' for x,y,z in self.v]
        current=None
        for mat,face in self.faces:
            if mat!=current:lines.append('usemtl '+mat);current=mat
            lines.append('f '+' '.join(map(str,face)))
        (folder/(name+'.obj')).write_text('\n'.join(lines)+'\n')
        mtls=[]
        for mat,color in self.materials.items():
            rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
            mtls.extend([f'newmtl {mat}','Kd '+' '.join(f'{x:.5f}' for x in rgb),'Ka 0.15 0.15 0.15','Ks 0.05 0.05 0.05','Ns 16',''])
        (folder/(name+'.mtl')).write_text('\n'.join(mtls))
        return {'logicalId':name,'source':f'models/{name}.obj','triangles':len(self.faces),'bounds':[[min(v[i] for v in self.v) for i in range(3)],[max(v[i] for v in self.v) for i in range(3)]],'robloxAssetId':None,'status':'source-ready; Studio import required'}

def dinosaur(species):
    m=Mesh();quad=species in ('triceratops','stegosaurus','ankylosaurus');rex=species=='tyrannosaurus'
    main,light,dark=('#4EA68F','#B2DFC2','#286D69') if species=='compy' else (('#568FC0','#B3D5E5','#375E88') if quad else ('#D17C50','#F2C68D','#814B41'))
    if species=='raptor':main,light,dark='#BA6899','#EFC0D4','#6A3661'
    elif species=='stegosaurus':main,light,dark='#83A74A','#D0E397','#486B38'
    elif species=='ankylosaurus':main,light,dark='#94734E','#DDC28E','#584538'
    m.ellipsoid((0,2.4,0.3),(1.6 if quad else 1.2,1.05,1.9 if quad else 1.5),main)
    m.ellipsoid((0,2.05,-.2),(.95,.65,1.25),light)
    m.tube([(0,2.5,-.9),(0,3.15,-1.5),(0,3.55,-1.9)],[.8,.72,.65],main)
    m.ellipsoid((0,3.6,-2.0),(1.15 if rex else .95,.85,1.1),main)
    m.ellipsoid((0,3.35,-2.8),(1 if rex else .8,.42,.8),light)
    m.ellipsoid((0,3.0,-2.65),(.9 if rex else .7,.2,.85),dark)
    m.tube([(0,2.4,1.4),(0,2.25,2.7),(0,2.7,4.1),(0,3.0,5.0)],[.7,.5,.25,.025],main)
    for s in (-1,1):
        legs=[-.95,1.2] if quad else [.6]
        for z in legs:
            m.ellipsoid((s*.85,1.6,z),(.5,.9,.6),dark)
            m.tube([(s*.85,1.4,z),(s*.85,.45,z-.3)],[.32,.24],main)
            m.ellipsoid((s*.85,.27,z-.5),(.4,.23,.65),main)
            for toe in (-1,0,1):m.tube([(s*.85+toe*.16,.23,z-.8),(s*.85+toe*.16,.16,z-1.08)],[.09,.025],'#F0E3BF',6)
        if not quad:m.tube([(s*1,2.7,-.7),(s*1.35,2.1,-1.15),(s*1.25,2.05,-1.5)],[.18,.13,.09],main)
        m.ellipsoid((s*.85,3.9,-2.5),(.15,.29,.33),'#FCF4D9',4,8)
        m.ellipsoid((s*.97,3.92,-2.62),(.06,.16,.14),'#142E35',4,8)
        m.ellipsoid((s*.98,3.99,-2.68),(.025,.05,.04),'#FFFFFF',3,6)
        m.ellipsoid((s*.39,3.63,-3.46),(.07,.065,.035),dark,3,6)
        if species=='triceratops':m.tube([(s*.55,4.1,-2.2),(s*.62,4.6,-3),(s*.6,4.75,-3.5)],[.22,.14,.015],'#F0E3BF')
    if species=='triceratops':
        m.ellipsoid((0,3.9,-1.25),(1.55,1.35,.28),dark)
        for i in range(7):
            a=math.pi*i/6;m.ellipsoid((1.45*math.cos(a),3.9+1.25*math.sin(a),-1.32),(.22,.24,.2),'#F0E3BF',4,8)
        m.tube([(0,3.6,-3.1),(0,4.05,-3.5)],[.18,.01],'#F0E3BF')
    else:
        for i in range(5):m.ellipsoid((0,3.34-i*.13,.3+i*.48),(.15,.25,.23),dark,4,8)
    if species=='stegosaurus':
        # Tall, alternating plates and four tail spikes.
        for i in range(7):
            z=-.7+i*.5
            m.tube([((-.22 if i%2 else .22),3.1,z),((-.3 if i%2 else .3),4.7-abs(i-3)*.22,z)],[.48,.015],'#EFA959',4)
        for side in (-1,1):
            for z in (3.4,4.1):m.tube([(side*.18,2.6,z),(side*.85,3.2,z+.4)],[.16,.01],'#F0E3BF',4)
    elif species=='ankylosaurus':
        # Armored dome, side spikes and a club at the tail tip.
        m.ellipsoid((0,3,.4),(1.75,.85,1.9),dark)
        for x in (-.8,0,.8):
            for z in (-.6,.3,1.2):m.ellipsoid((x,3.7,z),(.42,.3,.45),light,3,6)
        for side in (-1,1):
            for z in (-.5,.4,1.3):m.tube([(side*1.4,2.9,z),(side*2.15,3.2,z)],[.22,.01],light,4)
        m.ellipsoid((0,3,4.85),(.85,.6,.75),dark)
    elif species=='raptor':
        # Narrow runner proportions, feathered arms and raised sickle claws.
        for side in (-1,1):
            for i in range(3):m.tube([(side*1.25,2.2,-1),(side*(1.75+i*.12),2.3,-.7+i*.35)],[.15,.01],dark,4)
            m.tube([(side*.85,.4,-.4),(side*.85,.75,-.8),(side*.85,.65,-1.05)],[.15,.1,.01],'#F0E3BF',4)
        m.v=[(x*.8,y*.9,z*1.08) for x,y,z in m.v]
    return m.save(species)

def environment(name):
    m=Mesh()
    if name=='rock':
        m.ellipsoid((0,1.6,0),(2.8,1.8,2.3),'#71888C',4,7)
        m.ellipsoid((1.5,.6,.7),(1.2,.8,1.3),'#526D76',3,6)
    elif name=='tree':
        m.tube([(0,0,0),(.3,3.5,0),(-.2,7,.3),(.7,10,0)],[.8,.65,.42,.15],'#785445',9)
        for s in (-1,1):
            m.tube([(0,6,0),(s*2,8,.5),(s*3,10,.2)],[.42,.25,.09],'#785445',8)
        for x,y,z,sz in [(0,10,0,3),(2.4,10,.5,2.4),(-2.2,10,.4,2.7),(0,12,.3,2.4)]:m.ellipsoid((x,y,z),(sz,sz*.65,sz),'#3C8F75' if y<12 else '#65B18A',4,9)
    elif name=='fern':
        for i in range(7):
            a=i*2*math.pi/7
            p=[(0,0,0),(.6*math.cos(a),1.6,.6*math.sin(a)),(2*math.cos(a),1.1,2*math.sin(a))]
            m.tube(p,[.11,.17,.015],'#77BD8A',6)
            for j in range(1,4):
                t=j/4;x=t*1.6*math.cos(a);z=t*1.6*math.sin(a)
                m.ellipsoid((x,1.3,z),(.35,.10,.65),'#4D997A',3,6)
    elif name=='egg':
        m.ellipsoid((0,1.2,0),(.85,1.2,.85),'#FAE7B1',8,12)
        for x,y,z in [(.55,1.5,.52),(-.45,.9,.65),(.3,2,.4),(-.62,1.65,.3)]:m.ellipsoid((x,y,z),(.18,.22,.08),'#6AA894',4,8)
    elif name=='berry':
        m.ellipsoid((0,.25,0),(.24,.25,.24),'#DF6575',5,9)
        m.tube([(0,.45,0),(.09,.61,0)],[.035,.015],'#508969',6)
    elif name=='fruit':
        m.ellipsoid((0,.45,0),(.44,.44,.44),'#F4BA57',6,10)
        m.ellipsoid((.13,.92,0),(.25,.04,.12),'#4D997A',3,6)
    elif name=='amber':
        m.ellipsoid((0,.65,0),(.5,.65,.5),'#FFC875',3,5)
    return m.save(name)

def generate():
    OUT.mkdir(exist_ok=True)
    assets=[dinosaur(x) for x in ('compy','triceratops','tyrannosaurus','raptor','stegosaurus','ankylosaurus')]+[environment(x) for x in ('tree','rock','fern','egg','berry','fruit','amber')]
    icons={
        'dinos':'<path d="M30 78V53Q30 36 49 36H66L72 22L83 28L79 50L95 58V76H74L66 66H55V94H39V78Z" fill="#77cba6"/><circle cx="74" cy="42" r="3" fill="#173c42"/>',
        'egg':'<path d="M64 18C43 18 26 56 26 78C26 107 102 107 102 78C102 56 85 18 64 18Z" fill="#ffe9b9"/><path d="M28 76L47 63L61 77L80 61L101 74" fill="none" stroke="#74bfa5" stroke-width="10"/>',
        'home':'<path d="M20 57L64 21L108 57L99 67L91 61V106H71V78H56V106H36V61L28 67Z" fill="#77cba6"/>',
        'leaf':'<path d="M27 102C8 31 63 19 108 22C105 74 76 114 27 102Z" fill="#77cba6"/><path d="M27 102L83 45" stroke="#efffd6" stroke-width="7" fill="none"/>',
        'amber':'<path d="M45 17H84L109 58L83 109H43L19 58Z" fill="#ffcc6e"/><path d="M45 17L39 58L64 109L88 58L84 17M19 58H109" stroke="#ffecc3" stroke-width="5" fill="none"/>',
        'close':'<path d="M37 37L91 91M91 37L37 91" stroke="#fff7e6" stroke-width="15" stroke-linecap="round"/>',
    }
    iconfolder=OUT/'ui/icons';iconfolder.mkdir(parents=True,exist_ok=True)
    for name,body in icons.items():
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 128 128"><g stroke="#173c42" stroke-width="5" stroke-linejoin="round">{body}</g></svg>'
        (iconfolder/(name+'.svg')).write_text(svg)
        try:
            import cairosvg
            cairosvg.svg2png(bytestring=svg.encode(),write_to=str(iconfolder/(name+'.png')))
        except ImportError:pass
        assets.append({'logicalId':'icon_'+name,'source':'ui/icons/'+name+'.svg','robloxAssetId':None,'status':'original vector; image upload required'})
    existing=json.loads((OUT/'manifest.json').read_text()) if (OUT/'manifest.json').exists() else {'assets':[]}
    generated_ids={a['logicalId'] for a in assets}
    assets += [a for a in existing['assets'] if a['logicalId'] not in generated_ids]
    manifest={'version':1,'creator':'Be Dino / Znypr','rights':'Original project-generated geometry and vector artwork; no third-party source assets.','generator':'tools/generate_resources.py','units':'Roblox studs; Y up; front -Z; origin on ground','assets':assets}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Generated {len(assets)} resource assets')
if __name__=='__main__':generate()
