> Current build: food-growth-004. Size pads have been replaced with berries. Follow [the current checklist](12-food-growth-test.md); movement-only instructions below describe the previous milestone.

# Open the first movement prototype

This is a movement test, not the complete game. It contains one original placeholder dinosaur, a walled arena, obstacles, a slope, camera/HUD and 1×/2×/4× visual-size pads. No food, combat, inventory, chests or saving yet.

## Fastest route: no plugin or Python needed
1. Download [BeDino-Prototype.rbxlx](../build/BeDino-Prototype.rbxlx) using GitHub's **Download raw file** button. Keep the .rbxlx extension.
2. In Roblox Studio, choose **File → Open from File** and open it as a separate place.
3. Press **Play** (F5). The arena is generated when play starts; a mostly empty edit view is expected.
4. Move with WASD, rotate the camera with the right mouse button, and walk onto all three size pads.
5. Stop the test. Follow the multiplayer checks below before considering the movement milestone accepted.

If Windows saves .txt or opens XML in a browser, use Save As with the .rbxlx filename, then open that file from Studio.
No external assets, HTTP requests, API services or data store access are required by this prototype.
Do not publish over an existing experience. A new private test experience under Znypr's account can be created after the local test works; record its place/universe IDs in the decision log.

## What to check
- A green dinosaur appears instead of the visible Roblox avatar.
- Ground movement, turning, walls, slope and obstacle edges feel usable.
- 1×, 2× and 4× pads change the dinosaur for both clients.
- Camera remains useful at every size; check feet against the floor.
- Reset character: the dinosaur returns and controls/camera still work.
- Studio multiplayer test with two clients: both see and move as dinosaurs.
- Use touch emulation to inspect controls/HUD, then test on a real phone before release.
- Open Studio Output and capture any red error together with what you were doing.

The cosmetic dinosaur grows, but the underlying standard Humanoid collider remains fixed. Large models may clip into obstacles. This is an explicit experiment to evaluate, not a finished collision solution. Models are currently static; walking animation is deferred until movement is accepted.

Send one gameplay screenshot and any Output errors after the first run. Useful feedback: avatar visible?, camera okay?, feet on floor?, movement stuck?, which size?

## Rebuild from source
Install Python 3.10+ only if you want to rebuild locally. The checked-in build already contains all source scripts.
From the repository root:

```sh
python tools/build.py
python -m unittest discover -s tests -v
```

On Windows, use `py -3` in place of `python` if necessary.
Output: build/BeDino-Prototype.rbxlx and its source-hash manifest.
The small dependency-free packager supports only this project's folder/script mapping. It fails on unsupported mappings rather than ignoring them. It is not a general Roblox serializer.

## Optional later: Rojo
default.project.json also defines a standard Rojo source mapping. Rojo integration and version pinning remain pending; they are not prerequisites for opening this build.
Use a separate private place for any sync experiment. Do not live-sync over hand-edited production content.

## References checked during implementation
- [Roblox Humanoid reference](https://create.roblox.com/docs/reference/engine/classes/Humanoid): standard movement and camera subject.
- [Player reference](https://create.roblox.com/docs/reference/engine/classes/Player): character and appearance handling.
- [Rojo project format](https://rojo.space/docs/v7/project-format/): filesystem mapping.
- [Studio testing modes](https://create.roblox.com/docs/studio/testing-modes): multiplayer verification.

## Verification boundary
Local packaging/source-roundtrip tests can validate file structure; they cannot prove Roblox loads or executes this build correctly.
Studio execution, real-client replication, phone performance and publication have not been tested from this environment. BD-004/BD-006 remain unaccepted until these checks have actual evidence.
