"""BD-1244 life on the island and BD-1247 warm light: offline source checks (the Luau checks are tools/verify_island_life.py and
tools/verify_warm_light.py, in CI)."""
import importlib.util
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def profiles():
    spec = importlib.util.spec_from_file_location('release_profiles', ROOT / 'tools' / 'release_profiles.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IslandLifeTests(unittest.TestCase):
    def test_flags_ship_off_and_playtest_turns_them_on(self):
        config = read('src/shared/Config.luau')
        rp = profiles()
        playtest = rp.apply_profile(config, 'playtest')[0]
        rehearsal = [key for key, _ in rp.REHEARSAL_ON]
        for flag in ('IslandLifeEnabled', 'WarmLightEnabled'):
            self.assertIn('    %s = false,\n' % flag, config)
            self.assertIn('%s = true' % flag, playtest)
            self.assertIn(flag, rehearsal)

    def test_critters_have_registry_lines(self):
        items = re.findall(r'(life_\w+) = \{assetId = "(\d+)"', read('src/shared/IslandLife.luau'))
        self.assertEqual(len(items), 4)
        self.assertEqual(len({i for _, i in items}), 4)
        registry = read('docs/77-asset-registry.md')
        for key, aid in items:
            self.assertIn('| %s |' % key, registry)
            self.assertIn(aid, registry)

    def test_client_only_and_bootstrap_untouched(self):
        boot = read('src/client/Bootstrap.client.luau')
        self.assertNotIn('IslandLife', boot)
        self.assertNotIn('WarmLight', boot)
        life = read('src/client/IslandLife.client.luau')
        for bad in ('RemoteEvent', ':FireServer', 'NpcLowPoly', 'Instance.new("Humanoid")'):
            self.assertNotIn(bad, life)

    def test_babies_are_never_predators(self):
        predators = re.findall(r'"(\w+)"', re.search(r'Species = \{([^}]*)\}', read('src/shared/NpcPredatorRules.luau')).group(1))
        babies = re.search(r'IslandLife.Babies = \{(.*?)\n\}', read('src/shared/IslandLife.luau'), re.S).group(1)
        for species in re.findall(r'"(\w+)"', babies):
            self.assertNotIn(species, predators)


if __name__ == '__main__':
    unittest.main()
