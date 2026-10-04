"""Checks that the permission-free delivery actually contains geometry and usable art."""
from pathlib import Path
import unittest,xml.etree.ElementTree as ET
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class DeliveryTests(unittest.TestCase):
 def test_ten_native_models_packaged_with_colours_and_noncolliding_geometry(self):
  root=ET.parse(ROOT/'build/BeDino-Build016.rbxlx').getroot()
  resources=next(i for i in root.iter('Item') if i.find("Properties/string[@name='Name']") is not None and i.find("Properties/string[@name='Name']").text=='Resources')
  models=resources.findall('Item');self.assertEqual(len(models),10)
  for model in models:
   self.assertEqual(model.attrib['class'],'Model')
   parts=model.findall('Item');self.assertGreater(len(parts),10)
   for part in parts:
    self.assertEqual(part.attrib['class'],'WedgePart')
    self.assertIsNotNone(part.find("Properties/Color3uint8[@name='Color3uint8']"))
    self.assertEqual(part.find("Properties/bool[@name='CanCollide']").text,'false')
    size=part.find("Properties/Vector3[@name='size']")
    self.assertTrue(all(float(v.text)>0 for v in size))
 def test_individual_icons_have_real_alpha_and_references_are_not_game_assets(self):
  icons=list((ROOT/'resources/ui/v2/icons').glob('*.png'));self.assertEqual(len(icons),7)
  for icon in icons:
   im=Image.open(icon);self.assertEqual(im.mode,'RGBA')
   self.assertEqual(im.getchannel('A').getextrema(),(0,255))
  self.assertEqual(len(list((ROOT/'resources/references/steal-an-egg').glob('*.png'))),13)
  project=(ROOT/'default.project.json').read_text();self.assertNotIn('references',project)
if __name__=='__main__':unittest.main()
