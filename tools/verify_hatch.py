"""Execute fragment coverage/budget checks in Luau; Studio validates presentation."""
from pathlib import Path
import argparse
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def script():
    source = (ROOT / 'src/shared/HatchFragments.luau').read_text()
    return 'local F=(function()\n' + source + '\nend)()\n' + '''
assert(#F.Polygons==7)
local crops=0
for y=109,385,4 do
    local spans={}
    for _,polygon in F.Polygons do
        for _,span in F.spans(polygon,y) do table.insert(spans,span) crops+=1 end
    end
    table.sort(spans,function(a,b) return a[1]<b[1] end)
    assert(spans[1][1]==140,"left shell edge lost")
    local edge=140
    for _,span in spans do
        assert(span[1]<=edge,"shell gap")
        assert(edge-span[1]<=2,"excessive fragment overlap")
        edge=math.max(edge,span[2])
    end
    assert(edge==372,"right shell edge lost")
end
assert(crops<=240,"fragment crop budget exceeded")
print("Hatch geometry: seven jagged fragments cover shell without gaps; crops",crops)
'''

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--runner',required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'hatch.luau'
        path.write_text(script())
        subprocess.run([args.runner,str(path)],check=True)
