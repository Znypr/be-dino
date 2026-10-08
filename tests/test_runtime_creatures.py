"""Validate delivered geometry, rig weights, masks and Studio source limits."""
import json,math,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RuntimeCreatureTests(unittest.TestCase):
    def test_geometry_and_skinning(self):
        files=[p for p in (ROOT/'resources/creatures').glob('*.json') if '-genes' not in p.stem]
        self.assertEqual(len(files),17)
        for path in files:
            data=json.loads(path.read_text())
            self.assertLessEqual(data['triangles'],2100)
            self.assertEqual(data['triangles'],len(data['faces']))
            self.assertEqual(len(data['uvs']),3*len(data['faces']))
            self.assertEqual(len(data['normals']),len(data['uvs']))
            for face in data['faces']:
                self.assertEqual(len(set(face)),3)
                self.assertTrue(all(1<=v<=len(data['vertices']) for v in face))
            for weights in data['weights']:
                self.assertLessEqual(len(weights),4)
                if weights:self.assertAlmostEqual(sum(w for _,w in weights),1,places=5)
            if path.stem!='egg':
                self.assertGreaterEqual(len(data['bones']),10)
                self.assertEqual(set(data['animations']),{'Idle','Move'})
                for clip in data['animations'].values():
                    self.assertEqual(len(clip),5)
                    self.assertTrue(all(len(pose)==len(data['bones']) for pose in clip))
            for p in data['vertices']:self.assertTrue(all(math.isfinite(v) for v in p))
    def test_eight_masks_and_fixed_faces(self):
        for path in (ROOT/'resources/creatures').glob('*-genes.json'):
            data=json.loads(path.read_text())
            self.assertEqual(data['size'],128)
            self.assertEqual(len(data['patterns']),8)
            fixed=None
            for mask in data['patterns'].values():
                values=bytes.fromhex(mask)
                self.assertEqual(len(values),128*128)
                self.assertGreater(sum(v<254 for v in values),100)
                faces={i for i,v in enumerate(values) if v==254}
                if fixed is None:fixed=faces
                self.assertEqual(fixed,faces)
            if path.stem!='egg-genes':self.assertGreater(len(fixed),0)
    def test_packaged_sources_roundtrip_below_studio_limit(self):
        for folder in ['CreatureData','CreatureGenes']:
            for path in (ROOT/'src/shared'/folder).rglob('*.luau'):
                self.assertLess(len(path.read_text()),200000)
            for path in (ROOT/'src/shared'/folder).glob('*.luau'):
                chunks=sorted((path.parent/'Chunks').glob(path.stem+'_*.luau'),key=lambda p:int(p.stem.rsplit('_',1)[1]))
                raw=''.join(p.read_text().removeprefix('return [==[').removesuffix(']==]\n') for p in chunks)
                source=ROOT/'resources/creatures'/(path.stem+('-genes' if folder=='CreatureGenes' else '')+'.json')
                self.assertEqual(raw,source.read_text())
if __name__=='__main__':unittest.main()
