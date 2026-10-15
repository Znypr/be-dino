# 93 Settings audio mixer, admin panel UX, toast fixes (2026-10-15)

Status: **Review / test**. Offline checks pass (`tools/verify_audio.py`, `verify_notify.py`, `verify_admin.py`); Studio play test done on the playtest build; phone test pending.

## Audio mixer (docs/87: calm and quiet)
- `src/shared/AudioMixer.luau`: SoundGroups `BeDinoMaster` with `BeDinoSfx` and `BeDinoAmbience` inside it, so master x channel always multiplies.
- Routed through the mixer: `Sfx.play` (Sfx group), `HatchPresentation` tap/crunch/chime (Sfx), `WeatherAudio` beds and accents (Ambience). `verify_audio.py` fails if any `Instance.new("Sound")` is added without `AudioMixer.attach`.
- Defaults: Everything 80%, Sounds 70%, Weather 60%. UI sounds are now heard at about 0.56 x the old level, which is intentionally quieter.
- Settings screen: three draggable bars (`src/client/VolumeSliders.luau`), the sound ON/OFF switch (still mutes everything) and RESET SOUND.
- **Levels are session-only.** Saving needs a profile field and a server remote; that was out of scope (no profile migration). They reset to the defaults on every join. Follow-up: store one additive `audio` table in the profile.
- Reduce motion: the existing "Visual effects ON/OFF" toggle already is the reduce-motion switch (`Theme.MotionEnabled`, honoured by dino motion, cosmetics, hatch and toasts). No second toggle was added.

## Admin panel (F2, owner only)
- Bigger text and buttons (20-28 px, 48 px buttons), grouped sections: **Weather**, **Run** (food, growth, speed), **Feel**, **Debug** (world parts readout).
- Weather: pick any of the 7 events, pick a length, then **Start now** / **Stop**.
- No grant eggs/crystals row exists (the server has no such action); none was added.
- Security unchanged: `AdminService.handle` still rejects anything not authorised by `Rules.isAdmin` on the server; the client panel only builds when the server sets `IsAdmin`.
- Toasts: the panel publishes `AdminPanelRight` on the player; `Bootstrap.client` slides the toast stack right so cards never sit under the panel.

## Notifications
- `NotifyQueue.clip`: titles are cut at 30 characters and second lines at 44, at a word boundary, so they fit the 440 px card. Still max 3 visible.
- Three long messages were shortened ("Fusion is coming soon", "Hatch eggs to find this dino", "Still growing. Hang tight!").
