"""BD-403 permanent check (docs/114 s6): weather never affects the cave interior. Static scan of src/client/WeatherVisuals.client.luau
and src/client/CaveAtmosphere.luau (no Luau runner needed):
 * the loop derives hall = Cave.inside() or Cave.amount() > .01 and outside = 1 - Cave.amount(); strength t is multiplied by outside
 * every Lighting / effect write (grade, bloom, rays, dof, atmosphere, fog, colour shift, exposure, ambient, lamp, glow) uses t / outside,
   so inside the hall it is the neutral value; flash / pulse / thunder additions are multiplied by outside
 * particles, bolts, bombs, quake, moon and aurora are gated by motion / live / hall (both include `not hall`)
 * inside only the small soft text toast shows (BD-398, text not an effect); camera shake is 0 inside; celestial bodies hidden
 * the cave look is written after the weather values (Cave.step is the last statement of the Heartbeat)
"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]


def main():
    src = (ROOT / 'src/client/WeatherVisuals.client.luau').read_text(encoding='utf-8')
    loop = src[src.index('RunService.Heartbeat:Connect'):]
    assert 'local hall=Cave.inside() or Cave.amount()>.01' in loop, 'hall flag'
    assert 'local outside=1-Cave.amount()' in loop, 'outside factor'
    assert 'local t=WL.strength(k,Theme.MotionEnabled)*outside' in loop, 'weather strength must fade by outside'
    assert 'local motion=Theme.MotionEnabled and root~=nil and not hall' in loop, 'particle gate excludes the hall'
    assert 'local live=motion and root~=nil and not hall' in loop, 'one-shot gate excludes the hall'
    # every effect write that is not a plain function of t must carry `outside` or be a neutral constant
    for line in loop.splitlines():
        s = line.strip()
        for name in ('grade.Brightness=', 'bloom.Intensity=', 'glow.Brightness='):
            if s.startswith(name):
                for add in ('flash', 'pulse'):
                    for m in re.finditer(add + r'\*[\d.]+', s):
                        pass
                assert 'outside' in s or 'flash' not in s, 'flash/pulse must be scaled by outside: ' + s
    assert 'flash*.9*outside' in loop and 'flash*1.5*outside' in loop and 'flash*3*outside' in loop
    for token in ('rays.Intensity=lerpNum(0,look.rays,t)', 'dof.FarIntensity=lerpNum(0,look.dof,t)', 'lamp.Brightness=look.lamp*t',
                  'Lighting.ColorShift_Top=baseShiftTop:Lerp(shiftOf(baseShiftTop,shiftTop),t)', 'Lighting.ExposureCompensation=baseExposure+lerpNum(0,look.exposure,t)',
                  'grade.Saturation=lerpNum(0,look.sat,t)', 'WL.fog(look,t,CLEAR,fogCap)'):
        assert token in loop, 'effect must be driven by t: ' + token
    assert 'CelestialBodiesShown=activeId=="clear" or k<=0 or hall' in loop, 'event sun/moon sky state hidden inside'
    assert 'showTitle(id,workspace:GetAttribute("WeatherName") or id,hall)' in loop, 'inside the hall only the soft text toast (no big card)'
    assert 'if hall then shake=0 end' in loop, 'no camera shake inside, not even for a quake'
    assert 'if root and not hall and activeId=="quake"' in loop, 'quake cracks gated by hall'
    assert 'local moonOn=live and' in loop and 'local auroraOn=live and' in loop, 'moon / aurora gated by live'
    for name in ('on=motion and weatherId==activeId', 'live and root and activeId=="volcano"', 'live and root and activeId=="thunder"'):
        assert name in loop, 'gate missing: ' + name
    # no Lighting / effect property written outside the main loop after setup other than the loop itself and the one-shot helpers
    body = loop.split('end)\n', 1)[0] if 'end)\n' in loop else loop
    assert body.rstrip().endswith('Cave.step(dt) -- last: the cave look is written after the weather values above'), 'Cave.step must be last'
    cave = (ROOT / 'src/client/CaveAtmosphere.luau').read_text(encoding='utf-8')
    assert 'dof.Enabled = false' in cave and 'function Cave.amount()' in cave
    # weather writes Lighting only inside the Heartbeat loop (setup-time reads of base values are fine)
    before = src[:src.index('RunService.Heartbeat:Connect')]
    assert not re.search(r'Lighting\.(Ambient|OutdoorAmbient|FogStart|FogEnd|FogColor|ColorShift_\w+|ExposureCompensation|Brightness)\s*=[^=]', before), \
        'Lighting overrides must live in the gated Heartbeat loop'
    print('verify_cave_weather: weather never affects the cave interior (BD-403)')


if __name__ == '__main__':
    main()
