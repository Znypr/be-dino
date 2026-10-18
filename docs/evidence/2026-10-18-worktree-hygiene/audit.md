# Worktree audit 2026-10-18 03:36

Read-only output of `python tools/worktree_hygiene.py audit` (docs/170). Nothing was removed or moved.

```text
     SIZE  STATE    PUSHED  LOCK   AGE  WHERE REMOVABLE?             BRANCH / PATH
   777 MB  clean    yes     -      13m  ok    no: recent (13m)       bd-playtest-newest
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-abe8bcf7936d989fa
   772 MB  clean    yes     -       1h  ok    no: recent (1h)        docs/156-integration-sweep
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-aecbba7fdcc3662de
   771 MB  clean    yes     -       4h  ok    no: recent (4h)        claude/switch-on-rehearsal
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-rehearsal
   771 MB  clean    yes     -       3h  ok    no: recent (3h)        secequip-merge
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-secequip
   767 MB  clean    yes     -       4h  LOOSE no: recent (4h)        claude/split-profile-repository
           C:/Users/znypr/Documents/be-dino-split
   767 MB  clean    yes     -       4h  ok    no: recent (4h)        claude/secret-species-equip
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-ss6
   767 MB  clean    yes+main -       4h  LOOSE no: recent (4h)        (detached)
           C:/Users/znypr/Documents/be-dino-base
   766 MB  clean    yes     -       4h  LOOSE no: recent (4h)        claude/bd456-dino-skins
           C:/Users/znypr/Documents/be-dino-wt-skins
   766 MB  clean    yes     -       4h  ok    no: recent (4h)        claude/secret-species-data
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-secret
   739 MB  clean    yes     yes     1h  ok    no: locked (claude age bd626
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a117bbcb7369c911d
   738 MB  clean    yes     -       3h  ok    no: recent (3h)        bd-627-weather-visuals-split
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a7b15968d4954dd9d
   738 MB  clean    yes     -       4h  LOOSE no: recent (4h)        claude/remote-audit-2026-10-17
           C:/Users/znypr/Documents/be-dino-wt-remote-audit
   738 MB  clean    yes     -       3h  LOOSE no: recent (3h)        claude/size-guard-audit
           C:/Users/znypr/Documents/be-dino-wt-sizeguard
   719 MB  UNSAVED  yes+main yes    32m  ok    no: locked (claude age worktree-agent-ab2d27c43f5f3ec82
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ab2d27c43f5f3ec82
             unsaved: ?? docs/evidence/2026-10-18-animation-and-model-checks/
             unsaved: ?? tests/test_animation_and_model_tools.py
             unsaved: ?? tools/animation_strip.py
             ... and 6 more
   718 MB  UNSAVED  yes+main yes     6m  ok    no: locked (claude age worktree-agent-a1cedc26655a8910a
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a1cedc26655a8910a
             unsaved:  M docs/00-documentation-guide.md
             unsaved:  M docs/07-kanban.md
             unsaved:  M docs/160-agent-brief.md
             ... and 4 more
   717 MB  clean    yes     -      21m  ok    no: recent (21m)       worktree-agent-aa28642b94959e32b
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-aa28642b94959e32b
   711 MB  clean    yes     -      13m  ok    no: recent (13m)       worktree-agent-a5995b6f87af6697b
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a5995b6f87af6697b
   711 MB  clean    yes     -       5m  ok    no: recent (5m)        (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt460
   711 MB  clean    yes     -      32m  ok    no: recent (32m)       bd-kidtext-screendiff
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-aa745615b21e39edc
   711 MB  clean    yes     -      32m  ok    no: recent (32m)       (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt458
   711 MB  clean    yes     -      34m  ok    no: recent (34m)       bd-637-audio-report
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a3d8cb13ebbc9f342
   708 MB  clean    yes     -      32m  ok    no: recent (32m)       bd-ref-playtest-tools
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a581452d2ccbbd13d
   708 MB  clean    yes     -      32m  ok    no: recent (32m)       worktree-agent-ab4b3a59a5bec9b1c
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ab4b3a59a5bec9b1c
   708 MB  clean    yes     -      19m  ok    no: recent (19m)       (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/tool461
   708 MB  clean    yes     -      24m  ok    no: recent (24m)       bd-646-merge-helper
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ad5ae2ae4881a9ce1
   708 MB  clean    yes     -      30m  ok    no: recent (30m)       retro-work-log
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a6ececc93212c4af1
   708 MB  clean    yes     -      31m  ok    no: recent (31m)       (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt457
   708 MB  clean    yes     -      45m  ok    no: recent (45m)       docs-158
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-aeb126fb0c4503d3f
   708 MB  clean    yes     -      45m  ok    no: recent (45m)       worktree-agent-aae4278f5a20a9632
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-aae4278f5a20a9632
   708 MB  clean    yes     -      56m  ok    no: recent (56m)       claude/cockatoo-turnaround-ref
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-cockatoo
   706 MB  clean    yes     yes     1h  ok    no: locked (claude age bd631-632
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a59fcbb2d1e57aa4d
   706 MB  clean    yes     -       2h  ok    no: recent (2h)        bd-docs145-status
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a69837541e0c75184
   706 MB  clean    yes     -       2h  ok    no: recent (2h)        bd-611-movement-window
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a29724e4bdaf554f5
   706 MB  clean    yes     -       2h  ok    no: recent (2h)        bd613
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a164a4460ebf9b946
   706 MB  clean    yes     -       2h  ok    no: recent (2h)        bd-614-fair-write-budget
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-af477b325d3bcf806
   705 MB  clean    yes     -       2h  ok    no: recent (2h)        fusion-stale-ladder-notes
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a3e51f863b328d192
   705 MB  clean    yes     -       2h  ok    no: recent (2h)        fusion-audit
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a9b15aba795b586a8
   705 MB  clean    yes     -       3h  ok    no: recent (3h)        claude/bd-618-615-v2
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a0ada02ffb15068a4
   705 MB  clean    yes     -       3h  ok    no: recent (3h)        (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt442
   705 MB  clean    yes     -       3h  ok    no: recent (3h)        claude/bd625-objective-batching
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ab3a1a24842c34582
   705 MB  UNSAVED  yes     -       3h  ok    no: unsaved files (46) (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt439
             unsaved: M  .github/workflows/build-generated-place.yml
             unsaved: M  docs/00-documentation-guide.md
             unsaved: UU docs/07-kanban.md
             ... and 43 more
   705 MB  UNSAVED  yes     -       3h  ok    no: unsaved files (61) (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt437
             unsaved: M  .github/workflows/build-generated-place.yml
             unsaved: M  docs/00-documentation-guide.md
             unsaved: UU docs/07-kanban.md
             ... and 58 more
   705 MB  clean    yes     -       3h  ok    no: recent (3h)        claude/eagle-special-bird
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-eagle
   705 MB  clean    yes     -       4h  ok    no: recent (4h)        claude/foxosaurus-v2
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-fox2
   701 MB  clean    yes     -       6h  ok    no: recent (6h)        claude/budgie-v2
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-budgie
   696 MB  clean    yes     -       5h  ok    no: recent (5h)        claude/fox-spec-change
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wtfox2
   695 MB  clean    yes     -       6h  ok    no: recent (6h)        claude/parakeet-special-bd
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt-parakeet
   695 MB  clean    yes     -       6h  LOOSE no: recent (6h)        claude/fox-secret-dino
           C:/Users/znypr/Documents/be-dino-wt/fox
   694 MB  clean    yes     -       6h  LOOSE yes                    claude/hover-measure-595
           C:/Users/znypr/Documents/be-dino-hovermeasure
   694 MB  clean    yes     -       6h  ok    no: recent (6h)        (detached)
           C:/Users/znypr/AppData/Local/Temp/claude/C--Users-znypr-Documents-be-dino/064afdc4-4241-455a-890c-9da6939f8bf2/scratchpad/wt428
   601 MB  UNSAVED  yes     -      25h  LOOSE no: unsaved files (1)  claude/batch-upload
           C:/Users/znypr/Documents/bd-batch-upload
             unsaved: ?? build/uploaded.json
   578 MB  UNSAVED  yes     -      25h  LOOSE no: unsaved files (1)  claude/vfx-lab-fire
           C:/Users/znypr/Documents/bd-vfx-lab
             unsaved: ?? tools/blender/vfx_lab_fire_v1.blend
   574 MB  UNSAVED  yes     -      22h  LOOSE no: unsaved files (1)  (detached)
           C:/Users/znypr/dtmp/wt-pr346
             unsaved: ?? build/uploaded.json
   569 MB  clean    yes     yes    32h  ok    no: locked (claude age worktree-agent-a26fcfb7cf9ee0456
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a26fcfb7cf9ee0456
   568 MB  clean    yes     yes    34h  ok    no: locked (claude age bd-403-400-401-cave-weather-amber-crystals
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ae1fcd1845de927dc
   568 MB  clean    yes     yes    34h  ok    no: locked (claude age claude/cave-food-v3
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ae705f1df8f9075d9
   567 MB  UNSAVED  yes     -      34h  ok    no: unsaved files (2)  bd352
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a7f8f7c069828146e
             unsaved:  M build/BeDino-Build020.manifest.json
             unsaved:  M build/BeDino-Build020.rbxlx
   567 MB  UNSAVED  yes     -      34h  ok    no: unsaved files (2)  bd292-cave-signs
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-acdf146ae3027631e
             unsaved:  M build/BeDino-Build020.manifest.json
             unsaved:  M build/BeDino-Build020.rbxlx
   567 MB  clean    yes     yes    34h  ok    no: locked (claude age worktree-agent-ad488794cf1b35291
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ad488794cf1b35291
   567 MB  clean    yes     yes    34h  ok    no: locked (claude age bd-095-effects-lod
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-ab6ee719c4c3a65ea
   567 MB  UNSAVED  yes     -      48h  ok    no: unsaved files (710 claude/sanctuary-polish
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-aab71075c6159d9f6
             unsaved: A  .github/pull_request_template.md
             unsaved: M  .github/workflows/build-generated-place.yml
             unsaved: M  .gitignore
             ... and 707 more
   565 MB  UNSAVED  yes     -      26h  LOOSE no: unsaved files (35) tier-pbr-maps
           C:/Users/znypr/Documents/bd-tier-pbr
             unsaved:  M docs/120-pending-owner-uploads-checklist.md
             unsaved:  M docs/77-asset-registry.md
             unsaved:  M src/shared/LowPolyTier.luau
             ... and 32 more
   536 MB  UNSAVED  yes     -      32h  LOOSE no: unsaved files (2)  (detached)
           C:/Users/znypr/dtmp/demo-trailer
             unsaved:  M src/shared/Config.luau
             unsaved:  M tools/release_profiles.py
   523 MB  UNSAVED  yes     -      30h  LOOSE no: unsaved files (1)  tier-art
           C:/Users/znypr/Documents/be-dino-tier
             unsaved: ?? assets/blender/creatures/lowpoly/
   480 MB  UNSAVED  yes+main -      40h  ok    no: unsaved files (1)  claude/cave-acceptance
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a050c6b0cdd3258ce
             unsaved: ?? docs/evidence/2026-10-16-cave-acceptance/
   441 MB  UNSAVED  yes     -      43h  ok    no: unsaved files (1)  claude/phone-budget-offline
           C:/Users/znypr/Documents/be-dino/.claude/worktrees/agent-a43a3fd1ef8771843
             unsaved:  M docs/07-kanban.md
        ?  main     -       -        ?  main  no: main checkout      claude/backlog-eggs-flow
           C:/Users/znypr/Documents/be-dino
```

Unregistered folders that contain a .git:

```text
  1.90 GB  C:/Users/znypr/Documents/Codex  (git folder)
  2.27 GB  C:/Users/znypr/Documents/Znypr-Studio  (git folder)
```

Totals:

- worktrees (not counting the main checkout): 66, total 43.80 GB
- safe to remove with `clean --go` (min age 6h): 1, 694 MB
- with unsaved files: 15; with unpushed commits: 0; locked: 9; folder missing: 0
- LOOSE (outside .claude/worktrees and the scratchpad): 13, 8.34 GB
- unregistered folders with a .git: 2, 4.17 GB
