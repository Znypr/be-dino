# Owner feedback P0 (BD-386..390), 2026-10-16

Studio: own temp copy of the playtest build (`BeDino-Build020-playtest.rbxlx`, unpublished), Play mode, screen_capture of that window only. The window was closed afterwards.

* after-text-welcome.jpg (BD-390): white fill + 3 px dark stroke on the welcome title, steps and buttons. Rating: clearly readable.
* after-food-and-compy.jpg, after-walking-drumstick.jpg (BD-387/388): Compy while standing and walking, drumsticks (red with a bone) and fruit among the berries. Rating: food reads well up close; from far away it depends on the existing halos (not measured). The walking pose shows body, head and eye staying together; the 0.4 stud peck is subtle in a still.
* BD-389 was verified by numbers: before the fix `LocalMeshVisual` was nil with 7 legacy shell parts visible after `LoadCharacter()`; after the fix it exists within 4 s.
* No true "before" stills exist for BD-387/388/390 (the older build was not re-run); the before values are in docs/90 section 6 and the kanban rows.
