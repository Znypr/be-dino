"""Validate delivered geometry and resource manifest, not Roblox runtime behavior."""
import json
from pathlib import Path
import unittest
from collections import Counter
from math import sqrt
ROOT=Path(__file__).resolve().parents[1]
class ResourceTests(unittest.TestCase):
    def setUp(self):self.manifest=json.loads((ROOT/'resources/manifest.json').read_text())
    def test_sources_exist_and_logical_names_are_unique(self):
        ids=[a['logicalId'] for a in self.manifest['assets']]
        self.assertEqual(len(ids),len(set(ids)))
        for asset in self.manifest['assets']:self.assertTrue((ROOT/'resources'/asset['source']).is_file())
    def test_meshes_are_closed_nondegenerate_and_match_manifest(self):
        for asset in self.manifest['assets']:
            if 'triangles' not in asset:continue
            vertices=[];faces=[]
            for line in (ROOT/'resources'/asset['source']).read_text().splitlines():
                if line.startswith('v '):vertices.append(tuple(map(float,line.split()[1:])))
                elif line.startswith('f '):faces.append(tuple(int(x)-1 for x in line.split()[1:]))
            self.assertEqual(len(faces),asset['triangles'])
            edges=Counter()
            for face in faces:
                self.assertEqual(len(set(face)),3)
                self.assertTrue(all(0<=i<len(vertices) for i in face))
                a,b,c=[vertices[i] for i in face]
                u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
                cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
                self.assertGreater(sqrt(sum(x*x for x in cross)),1e-9)
                for x,y in zip(face,face[1:]+face[:1]):edges[tuple(sorted((x,y)))]+=1
            self.assertTrue(all(n==2 for n in edges.values()),asset['logicalId'])
            for axis in range(3):
                self.assertAlmostEqual(min(v[axis] for v in vertices),asset['bounds'][0][axis],places=4)
                self.assertAlmostEqual(max(v[axis] for v in vertices),asset['bounds'][1][axis],places=4)
    def test_all_material_references_exist(self):
        for obj in (ROOT/'resources/models').glob('*.obj'):
            mtl=obj.with_suffix('.mtl').read_text()
            known={line.split()[1] for line in mtl.splitlines() if line.startswith('newmtl ')}
            used={line.split()[1] for line in obj.read_text().splitlines() if line.startswith('usemtl ')}
            self.assertLessEqual(used,known)
    def test_no_unverified_roblox_ids(self):
        self.assertTrue(all(a['robloxAssetId'] is None for a in self.manifest['assets']))
    def test_generated_place_runs_loading_before_character(self):
        import xml.etree.ElementTree as ET
        root=ET.parse(ROOT/'build/BeDino-Build017.rbxlx').getroot()
        first=next(i for i in root.findall('Item') if i.attrib['class']=='ReplicatedFirst')
        scripts=list(first.iter('Item'))
        self.assertTrue(any(i.attrib['class']=='LocalScript' for i in scripts))
if __name__=='__main__':unittest.main()
