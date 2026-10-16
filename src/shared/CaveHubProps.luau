--!strict
-- BD-284 (docs/104 s13): the published generate_mesh ids for the Cave hub props, and the pure placement rules. No Instances,
-- no Vector3, no Config require: tools/verify_cave_hub.py runs this module offline together with CaveHubLayout.
-- Every id below came from the owner's Studio generate_mesh runs on 2026-10-16 (hub-prop-ids.txt, docs/77 lists each one);
-- never write an id that is not a real upload. Each id is a Model ("Roblox Generated Object") holding ONE MeshPart, loaded
-- with InsertService:LoadAsset like WorldGeneratedMeshes (ImportedResources.loadGeneratedWorld). A failed load skips that prop.
--   id     = published asset id (numeric string)
--   native = size the asset loads at (studs, x y z), where known; nil = measure at runtime
--   final  = target size in studs after the uniform scale the owner/lead chose in Studio (equals CaveHubLayout.Kinds w, h, d)
--   note   = what the owner saw / how it is used
local Props = {}
Props.Version = 1

Props.Assets = {
    hub_stall_potion = {id = "98505427497881", note = "potion stall; size measured at runtime"},
    hub_cauldron = {id = "81536679437657", note = "cauldron; size measured at runtime"},
    hub_forge_altar = {id = "88576386735486", note = "forge altar; size measured at runtime"},
    hub_forge_ring = {id = "122312499375339", note = "regenerated 2026-10-16 (the first 116251053976984 was 0.5 studs wide and is unused)"},
    hub_crystal_s = {id = "95856679662296", note = "small crystal cluster"},
    hub_crystal_l = {id = "76296772134575", note = "big crystal cluster"},
    hub_counter_stone = {id = "110696396541252", native = {4.39, 3.5, 2.25}, final = {8.78, 7.0, 4.51}, note = "shop counter, x2"},
    hub_gem_chest = {id = "83123866209241", note = "open chest with gems"},
    hub_pedestal = {id = "79843377019012", note = "round pedestal"},
    hub_lectern_book = {id = "79082701256480", note = "lectern with book"},
    hub_bench_stone = {id = "105287844230946", note = "stone bench"},
    hub_crate = {id = "96129065956100", note = "wooden crate"},
    hub_lantern_hang = {id = "122897102088665", note = "hanging lantern: NOT placed (nothing to hang from in the hall); standing lanterns use hub_lantern_post"},
    hub_sign_arrow = {id = "129968732010527", note = "arrow signpost"},
    hub_sign_stone = {id = "117452112929711", native = {2.76, 2.76, 1}, final = {6.89, 6.9, 2.5}, note = "station sign board, x2.5; text is a SurfaceGui (BD-292)"},
    hub_table_wood = {id = "129469433227750", note = "extra key, not in docs/104 s13"},
    hub_statue_triceratops = {id = "105273504274472", native = {3.39, 4.6, 5.0}, note = "index statue"},
    hub_statue_trex = {id = "72433583459130", native = {3.56, 4.06, 4.0}, final = {6.76, 7.7, 7.6}, note = "index statue, x1.9"},
    hub_statue_brachiosaurus = {id = "137465469616227", native = {2.6, 3.66, 4.0}, final = {6.49, 9.15, 10}, note = "index statue, x2.5"},
    cave_rock_round = {id = "130521972633547", native = {5.08, 2.45, 5.0}, final = {5.08, 2.45, 5.0}, note = "round boulder"},
    cave_stalagmite_s = {id = "97873641239255", native = {3, 3.74, 2.95}, final = {4.5, 5.6, 4.4}, note = "x1.5"},
    cave_stalagmite_l = {id = "88054312401708", native = {7, 9.93, 6.9}, final = {7, 9.93, 6.9}, note = "big stalagmite"},
    cave_rock_flat = {id = "102304285005689", native = {5.99, 1.49, 6.0}, final = {5.99, 1.49, 6.0}, note = "flat slab"},
    cave_moss_patch = {id = "101810121069576", native = {2.68, 0.8, 2.67}, final = {4.8, 1.44, 4.8}, note = "x1.8"},
    cave_stalactite = {id = "130326241213512", native = {3, 8.34, 2.98}, final = {3, 8.34, 2.98}, note = "hangs from the ceiling"},
    cave_moss_hang = {id = "120656688611591", native = {4, 4.31, 0.79}, final = {4, 4.31, 0.79}, note = "hangs on the wall rim"},
    hub_barrel = {id = "81905342774801", native = {2.6, 3.5, 2.6}, final = {2.6, 3.5, 2.6}, note = "barrel"},
    hub_lantern_post = {id = "77903635465292", native = {2.0, 7.2, 2.0}, final = {2.0, 7.2, 2.0}, note = "standing lantern"},
    hub_banner = {id = "100217572989345", native = {3.0, 3.1, 0.4}, final = {5.4, 5.5, 0.8}, note = "x1.8, stands on the floor (no ceiling to hang from)"},
    hub_gong = {id = "82701218884460", native = {4.2, 4.1, 1.5}, final = {6.1, 6.0, 2.2}, note = "gong"},
    hub_cushion_moss = {id = "84347902360493", native = {1.2, 1.2, 1.2}, final = {2.6, 2.6, 2.6}, note = "x2.2"},
    hub_wall_frame = {id = "106938322985132", native = {2.5, 3.0, 0.5}, final = {3.8, 4.5, 0.7}, note = "x1.5, stands on the floor"},
    hub_gate_arch = {id = "90142774443313", native = {11, 11, 4}, final = {16, 15.9, 5.8}, note = "open arch, near-square; scaled up to the gate mouth (CaveHubLayout Kinds)"},
    hub_straw_mat = {id = "124268197129005", native = {1.7, 0.6, 2.9}, final = {2.3, 0.8, 4.0}, note = "nest mat"},
    hub_nest_ledge = {id = "87976992587442", native = {2.5, 2.5, 1.3}, final = {6.0, 6.0, 3.2}, note = "chunky ledge, used x2 bigger as the nests backdrop"},
    cave_lava_fall = {id = "117913129539593", native = {2.4, 3.9, 4.0}, final = {15, 24, 24.5}, note = "came out as a chunky block, NOT a sheet: not placed; the waterfall is FX (BD-285)"},
    cave_lava_rim_rock = {id = "139871400645311", native = {6.0, 2.3, 4.3}, final = {6.0, 2.3, 4.3}, note = "rim rock around the basin"},
    cave_stepping_stone = {id = "81807707687141", native = {4, 1, 4}, final = {6, 1.4, 6}, note = "x1.5, sits in the basin"},
    cave_wall_boulder_l = {id = "123764903718508", native = {10.2, 8.1, 10}, final = {14, 11.1, 13.7}, note = "x1.37, large rim rock, collides"},
    cave_wall_pillar = {id = "125763307295030", native = {6, 16.6, 6}, final = {6, 16.6, 6}, note = "rim pillar, collides"},
    cave_wall_arch_small = {id = "94844835940597", native = {10, 5.6, 3.5}, final = {10, 5.6, 3.5}, note = "small rim arch, collides"},
    cave_stalagmite_cluster = {id = "127029162299522", native = {8, 8.8, 6.3}, final = {8, 8.8, 6.3}, note = "stalagmite cluster"},
}

-- Props that already exist as published generated meshes (WorldGeneratedMeshes / docs/77); same ids, not new uploads.
Props.Existing = {
    rock_mossy_boulder = "135107793396569",
    rock_crystal = "84690157197711",
    rock_pebbles = "125187345067740",
    nest = "102765517629578",
    landmark_dino_statue = "82545380144820",
}

-- BD-296 dressing pass (owner 2026-10-16, handbook "ground props connect assets to the terrain" and "a few distinct plant families"): small
-- plants, rocks and glowing accents that grow out of the cave wall base. Two kinds of layout key, neither a new upload:
--   Props.Kit = kit meshes already published for the island (WorldKitMeshAssets; real extents in WorldKitData). The server clones the kit
--     MeshPart (vertex colours, no texture). `tone` multiplies the vertex colours, a little darker so island greens sit in the dim cave.
--   Props.Slots = a logical prop with an ORDERED source list: the first source that exists wins. A source is a Props.Assets key (published model),
--     a WorldGeneratedMeshes.Props key that has a non-empty assetId (the BD-464 Blender ground props, upload pending: ids empty today), or a kit
--     key. The layout row always carries the slot key and the target size, so uploading a BD-464 mesh later only means pasting its id in
--     WorldGeneratedMeshes.Props: the slot then prefers it and fitFactor scales it to the same box. A slot with no source at all places nothing.
Props.Kit = {
    world_fern_a = {tone = {0.84, 0.92, 0.80}}, world_fern_b = {tone = {0.84, 0.92, 0.80}},
    world_horsetail_a = {tone = {0.86, 0.92, 0.80}}, world_bush_a = {tone = {0.84, 0.90, 0.78}}, world_bush_b = {tone = {0.84, 0.90, 0.78}},
    world_mushrooms_a = {tone = {1, 1, 1}}, world_boulder_mossy_s = {tone = {0.9, 0.92, 0.88}}, world_boulder_bare_s = {tone = {0.95, 0.9, 0.85}},
    world_boulder_mossy_m = {tone = {0.9, 0.92, 0.88}},
}
Props.Slots = {
    dress_rock_small = {"ground_rock_small_v3", "world_boulder_bare_s"},
    dress_rock_mossy = {"ground_rock_mossy_v3", "world_boulder_mossy_s"},
    dress_rock_medium = {"ground_rock_medium_v3", "world_boulder_mossy_m"},
    dress_mushrooms = {"ground_mushrooms_v3", "world_mushrooms_a"},
    dress_bush = {"ground_bush_round_v3", "world_bush_a"},
    dress_log = {"ground_log_fallen_v3"}, -- no kit stand-in: placed only once the owner uploads it (docs/120)
    dress_stump = {"ground_stump_roots_v3"}, -- same
    dress_crystal = {"hub_crystal_s"}, -- the published amber stopgap crystal, used as a small lamp-side glow accent
}
-- Glowing accents (no lights: lights are capped at CaveHubLayout.MaxLights): the mesh is shown with this material and a colour multiplier. Neon with
-- the vertex colours kept (mushrooms) or the flat amber of the shop crystals. To turn a glow off set material = "SmoothPlastic".
Props.Glow = {
    dress_mushrooms = {material = "Neon", color = {205, 200, 185}},
    dress_crystal = {material = "Neon", color = {235, 170, 60}},
}
-- Ground props sink this fraction of their height into the floor (instead of the flat SINK) so they read as grown into the terrain, not set on it.
Props.SinkFrac = {
    dress_rock_small = 0.3, dress_rock_mossy = 0.25, dress_rock_medium = 0.25, dress_log = 0.2, dress_stump = 0.12,
    dress_mushrooms = 0.12, dress_bush = 0.12, world_fern_a = 0.1, world_fern_b = 0.1, world_horsetail_a = 0.06, dress_crystal = 0.15,
}
-- cave_moss_hang placed on a wall jamb (a Rim piece): drapes from this many studs over the floor, facing the wall's own inward direction
Props.HangBottom = 4.5

-- Layout keys that are deliberately NOT placed as a generated mesh, with the reason (every layout key is either an asset,
-- an existing mesh, or listed here).
Props.NotMeshes = {
    cave_light_cone = "light shafts are FX (CaveLighting, BD-286)",
    cave_lava_fall = "the generated block is chunky, not a sheet: the waterfall is built as FX (CaveLavaFx, BD-285)",
    lava_pool_disc = "lava surface is FX (CaveLavaFx, BD-285)",
    potion_model = "the four potion models are loaded by PotionModels for the menus; placing them on the counter is a follow-up",
    hub_lantern_hang = "nothing to hang from in the hall: the layout uses hub_lantern_post",
}

-- Large pieces that need to stop players (walls and pillars at the rim); everything else is decoration (CanCollide false)
-- and gets an invisible collider from CaveHubLayout.colliders when it needs one.
Props.Solid = {cave_wall_boulder_l = true, cave_wall_pillar = true, cave_wall_arch_small = true}

-- Props put on the cave wall rim instead of the floor, facing the Heart.
Props.Rim = {cave_wall_boulder_l = true, cave_wall_pillar = true, cave_wall_arch_small = true, cave_moss_hang = true}

Props.MinScale, Props.MaxScale = 0.25, 6 -- sane bounds of the uniform scale applied to a loaded asset

-- Lava waterfall FX numbers (docs/104 s5, BD-285). Textures only from EffectAssets (flameSheet, smokeSheet, sparkSheet, swirl).
Props.Lava = {
    sheetOffsetDz = 5, -- sheet sits this far behind CaveHubLayout.Fall.z (inside the falls recess)
    sheetTransparency = 1, sheetColor = {255, 110, 30}, -- BD-385: the carrier part is INVISIBLE (emitter box only); the falls are soft particle strands (CaveLavaRules.Strands)
    discTransparency = 0.25, discColor = {255, 110, 35}, discSpinSeconds = 60, discDrop = 0.6,
    fxPartBudget = 5, -- BD-385: 1 invisible emitter carrier + 3 glow discs + the pool disc (the carrier and disc stand in for the cave_lava_fall and lava_pool_disc rows)
    -- emitter rates, the strands and the phone / Reduce Motion rules live in CaveLavaRules (25 per second desktop, 10 phone)
}

-- BD-285 QA: the generated lava rim rocks and stepping stones came out blue / pink and clash with the warm cave. They keep their
-- mesh but lose the SurfaceAppearance and take a flat warm basalt Color and a matte material (decided from the Studio screenshots,
-- docs/evidence/2026-10-16-cave-lava). Nothing is re-baked and no new asset id is involved.
Props.Warm = {
    cave_lava_rim_rock = {color = {118, 74, 58}, material = "Slate"},
    cave_stepping_stone = {color = {138, 88, 66}, material = "Slate"},
    -- BD-411 / BD-400 STOPGAP (handbook 5.3, owner 2026-10-16: currency/shop crystals are AMBER): the blue-purple generated crystals take a
    -- flat amber Color until the owner regenerates amber meshes (BD-400). Same mechanism as the two rows above; no new asset id.
    hub_crystal_s = {color = {255, 190, 60}, material = "Plastic"},
    hub_crystal_l = {color = {255, 190, 60}, material = "Plastic"},
}

-- BD-292: the sign meshes that carry station text (a SurfaceGui built from HubSignCopy, front face only). `face` is the mesh's
-- front face name; `inset` shrinks the text box (fraction of the face) so words stay on the board.
Props.SignText = {
    hub_sign_stone = {face = "Front", back = "Back", inset = 0.12},
    hub_sign_arrow = {face = "Front", back = "Back", inset = 0.18},
}
Props.SignLightInfluence = 0 -- self-lit: lamp light does not dim the word (BD-292)
Props.SignBrightness = 2 -- SurfaceGui brightness boost so cream text stays readable in the dim cave
-- OWNER 2026-10-16: signs read from every angle: a second SurfaceGui on the Back face plus one small lamp-lit BillboardGui word above
-- the sign (always faces the player, fades out past MaxDistance, never AlwaysOnTop so walls hide it).
Props.SignBillboard = {width = 120, height = 36, lift = 1.2, maxDistance = 90, brightness = 2}
Props.MaxSignGuis = 12 -- SurfaceGuis are not Parts, but they cost render time: never more than this many sign texts

-- Uniform factor that scales a loaded asset of size `mesh` to the target box `target` (both {x, y, z}): the axis with the
-- largest target dimension decides, so a proportion mismatch stays inside the box on the other axes only if the asset was
-- generated close to the target (the verifier checks the factor stays within MinScale..MaxScale for every known asset).
function Props.fitFactor(mesh: {number}, target: {number}): number
    local axis = 1
    for i = 2, 3 do
        if target[i] > target[axis] then axis = i end
    end
    local m = mesh[axis]
    if m <= 0 then return 1 end
    return math.clamp(target[axis] / m, Props.MinScale, Props.MaxScale)
end

-- Published asset id (numeric string) for a layout key, or nil when the key is not a mesh.
function Props.assetId(key: string): string?
    local a = (Props.Assets :: any)[key]
    if a and not (Props.NotMeshes :: any)[key] then return a.id end
    if (Props.NotMeshes :: any)[key] then return nil end
    return (Props.Existing :: any)[key]
end

-- Pure source resolution for a layout key (the server passes in what it has): {kind = "asset" | "generated" | "kit", key, id?} or nil.
-- `generatedIds` = WorldGeneratedMeshes.Props (key -> {assetId}); `kitKeys` = set of kit keys that have a mesh binding (WorldKitMeshAssets).
function Props.sourceFor(key: string, generatedIds: any, kitKeys: any): any
    local slot = (Props.Slots :: any)[key]
    if not slot then
        if (Props.Kit :: any)[key] then
            if kitKeys[key] then return {kind = "kit", key = key} end
            return nil
        end
        local id = Props.assetId(key)
        if id then return {kind = "asset", key = key, id = id} end
        return nil
    end
    for _, src in slot do
        local a = (Props.Assets :: any)[src]
        if a then return {kind = "asset", key = src, id = a.id} end
        local g = generatedIds[src]
        if g and g.assetId ~= "" then return {kind = "generated", key = src, id = g.assetId} end
        if (Props.Kit :: any)[src] and kitKeys[src] then return {kind = "kit", key = src} end
    end
    return nil
end

return Props
