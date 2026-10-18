"""BD-320 offline rollback drill in pinned Luau (docs/111).

Runs the REAL current ProfileRepository and a frozen copy of the Build 020 reader
(tools/fixtures/build020, git a9edf8e) against ONE shared mocked DataStore, so profile data written by
one version is loaded by the other. Offline only: this proves transaction/validation logic, not a real
publish, DataStore versioning or Studio. The real owner drill stays open (BD-320).
"""
from pathlib import Path
import argparse
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import rehearsal_env  # noqa: E402
import verify_rewards  # noqa: E402  (reuses the mocked DataStore prefix)

FIXTURE = 'tools/fixtures/build020/'


sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile_sources  # noqa: E402


def module(path):
    return profile_sources.module(path)  # docs/150: ProfileRepository plus the parts it installs


BODY = (ROOT / 'tools' / 'fixtures' / 'rollback_body.luau').read_text(encoding='utf-8')


def script():
    prefix = verify_rewards.HARNESS.split('local function user(id)')[0]
    # The prefix ends with the default (identity off) repository; its token list is the rewards one.
    s = prefix
    for token, path in [
        ('@@PROGRESSION_CONFIG@@', 'src/shared/ProgressionConfig.luau'),
        ('@@GAME_CONFIG@@', 'src/shared/Config.luau'),
        ('@@FOOD_RULES@@', 'src/shared/FoodCatchRules.luau'),
        ('@@GENETICS@@', 'src/shared/EggGenetics.luau'),
        ('@@EGG_TRAITS@@', 'src/shared/EggTraits.luau'),
        ('@@RULES@@', 'src/shared/ProgressionRules.luau'),
        ('@@FUSION_ODDS@@', 'src/server/FusionOdds.luau'),
        ('@@REVEAL_SKIP@@', 'src/shared/RevealSkip.luau'),
        ('@@NEST_QUEUE@@', 'src/shared/NestQueue.luau'),
        ('@@FTUE_RULES@@', 'src/shared/FtueRules.luau'),
        ('@@SETTINGS_MODEL@@', 'src/shared/SettingsModel.luau'),
        ('@@PAID_RANDOM_GATE@@', 'src/shared/PaidRandomGate.luau'),
        ('@@REWARD_MATH@@', 'src/server/RewardMath.luau'),
        ('@@IDENTITY_FUSION_MODULE@@', 'src/server/IdentityFusion.luau'),
        ('@@IDENTITY_MODULE@@', 'src/server/DinosaurIdentity.luau'),
        ('@@COSMETIC_OWNERSHIP@@', 'src/server/CosmeticOwnership.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        s = s.replace(token, module(path))
    body = BODY
    for token, path in [
        ('@@OLD_CONFIG@@', FIXTURE + 'Config.luau'),
        ('@@OLD_PROGRESSION_CONFIG@@', FIXTURE + 'ProgressionConfig.luau'),
        ('@@OLD_GENETICS@@', FIXTURE + 'EggGenetics.luau'),
        ('@@OLD_RULES@@', FIXTURE + 'ProgressionRules.luau'),
        ('@@OLD_TRAITS@@', FIXTURE + 'EggTraits.luau'),
        ('@@OLD_REWARD_MATH@@', FIXTURE + 'RewardMath.luau'),
        ('@@OLD_REPO@@', FIXTURE + 'ProfileRepository.luau'),
        ('@@REPO_MODULE@@', 'src/server/ProfileRepository.luau'),
    ]:
        body = body.replace(token, module(path))
    # docs/152 BD-626: the drill is about a build with the identity flags OFF reading what a flags-ON build wrote. A repository chooses its
    # identity store wrapper from IdentityPersistentEnabled when its module is BUILT, so under the all-on rehearsal Config the two flags are
    # turned off in the harness Config before the prefix builds the default repository; the PlaytestConfig clone that plays the flags-ON
    # build sets them ON itself, and every other flag in this file stays at the all-on value.
    s = rehearsal_env.pin(s, 'mutableConfig.WriteBudgetEnabled=false',
                          'mutableConfig.IdentityPersistentEnabled=false mutableConfig.IdentityFusionPreviewEnabled=false mutableConfig.WriteBudgetEnabled=false',
                          label='rollback identity flags pin')
    return s + '\n' + body


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'rollback.luau'
        path.write_text(script(), encoding='utf-8')
        result = subprocess.run([args.runner, str(path)], capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        raise SystemExit(result.returncode)
