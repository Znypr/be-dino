# Latest Studio mesh access verification

2026-10-08, BD-043. Owner accepts the current hatching effects for now.

In user-selected BeDino-Latest.rbxlx (GameId/PlaceId 0), all six imported
species load their mesh and texture dependencies successfully: Compy, Raptor,
Triceratops, Tyrannosaurus, Stegosaurus and Ankylosaurus. Compy has seven mesh
parts; Raptor three; each remaining species seven. The six-preview audit used
disposable client UI, without a reward grant or profile mutation.

Latest Studio still contained the older DinosaurPreview preload of MeshId
strings. Changed that single call to preload actual MeshPart instances, matching
the fix already committed in the repository and UI PR. All six previews then
had no PreviewFallback attribute or ModelThumbnailFallback image.

Important tooling distinction: Roblox MCP screen_capture omitted rendered
ViewportFrame geometry, including a plain test cube and its background changes.
The native Studio window showed the actual six 3D dinosaurs. The archived native
window capture is docs/evidence/2026-10-08-mesh-access/native-six-species.jpg.
Do not infer missing mesh permission from an empty MCP viewport screenshot alone.

No asset privacy or sharing settings were changed, and no game was published.
The temporary audit script and UI were removed after verification. Owner Studio
access is verified; published non-owner asset permission remains a separate check
in the actual experience. This pass does not certify the newer genetics texture
bindings in the older Latest file or physical-phone performance.
