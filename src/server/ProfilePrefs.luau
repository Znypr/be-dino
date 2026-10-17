--!strict
-- ProfileRepository part (docs/150): player preference writes: reveal skip and settings (BD-264 / BD-358).
-- Moved unchanged out of ProfileRepository.luau, which installs it with the helpers it shares (store, retry, admit, adopt, ...);
-- tools/verify_profile_golden.py proves the stored profile is byte-identical to before the split.
return function(ProfileRepository: any, shared: any)
local Config = shared.Config
local SettingsModel = shared.SettingsModel
local admit = shared.admit
local adopt = shared.adopt
local coalesce = shared.coalesce
local coalesceWriters = shared.coalesceWriters
local coalesced = shared.coalesced
local handleLeaseLost = shared.handleLeaseLost
local isValidProfile = shared.isValidProfile
local keyFor = shared.keyFor
local ownSession = shared.ownSession
local prefSuperseded = shared.prefSuperseded
local profiles = shared.profiles
local retry = shared.retry
local store = shared.store
local syncAttributes = shared.syncAttributes
local takePrefSeq = shared.takePrefSeq

-- UI preference only (which species rarities the client auto-skips while revealing). Rewards
-- never depend on it; skipped eggs are still hatched and credited. Additive profile field.
function ProfileRepository.setRevealSkip(player: Player, selection: any): (boolean, string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return false, "profile_not_loaded" end
    if typeof(selection) ~= "table" or #selection > Config.SpeciesRarityScale then return false, "invalid_selection" end
    local seen, clean = {}, {}
    for _, rarity in selection do
        if typeof(rarity) ~= "number" or rarity % 1 ~= 0 or rarity < 1 or rarity > Config.SpeciesRarityScale or seen[rarity] then return false, "invalid_selection" end
        seen[rarity] = true
        table.insert(clean, rarity)
    end
    table.sort(clean)
    if not admit(player) then return coalesce(player, "revealSkip", clean) end
    if coalesced[player] then coalesced[player].revealSkip = nil end
    return ProfileRepository.writeRevealSkip(player, clean)
end

function ProfileRepository.writeRevealSkip(player: Player, clean: any): (boolean, string)
    local leaseLost = false
    local superseded = false
    local seq = takePrefSeq(player, "revealSkip")
    local now = os.time()
    local ok, updated = retry("reveal skip", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost = false
            superseded = false
            if prefSuperseded(player, "revealSkip", seq) then superseded = true return nil end
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            profileValue.revealSkip = table.clone(clean)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if superseded then return true, "saved" end -- a newer write of the same preference owns the stored value
        if leaseLost then handleLeaseLost(player) return false, "lease_lost" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "saved"
end

-- BD-264 settings v2: UI preferences only (sound levels, effects, weather, calm motion, jump size). Additive profile
-- field `settings`; the server normalizes whatever the client sends, so bad values become defaults.
function ProfileRepository.setSettings(player: Player, raw: any): (boolean, string)
    local cached = profiles[player]
    if not cached or player:GetAttribute("ProfileState") ~= "Loaded" then return false, "profile_not_loaded" end
    if typeof(raw) ~= "table" then return false, "invalid_settings" end
    local clean = SettingsModel.toStore(SettingsModel.fromStore(raw))
    if not admit(player) then return coalesce(player, "settings", clean) end
    if coalesced[player] then coalesced[player].settings = nil end
    return ProfileRepository.writeSettings(player, clean)
end

function ProfileRepository.writeSettings(player: Player, clean: any): (boolean, string)
    local leaseLost = false
    local superseded = false
    local seq = takePrefSeq(player, "settings")
    local now = os.time()
    local ok, updated = retry("settings", function()
        return store:UpdateAsync(keyFor(player), function(profileValue)
            leaseLost = false
            superseded = false
            if prefSuperseded(player, "settings", seq) then superseded = true return nil end
            if not isValidProfile(profileValue) then return nil end
            if not ownSession(profileValue) then leaseLost = true return nil end
            profileValue.settings = table.clone(clean)
            profileValue.revision += 1
            profileValue.session.expiresAt = now + Config.ProfileLeaseSeconds
            return profileValue
        end)
    end)
    if not ok or updated == nil then
        if superseded then return true, "saved" end -- a newer write of the same preference owns the stored value
        if leaseLost then handleLeaseLost(player) return false, "lease_lost" end
        player:SetAttribute("ProfileState", "SaveFailed")
        return false, "save_failed"
    end
    adopt(player, updated)
    if profiles[player] then syncAttributes(player, profiles[player]) end
    return true, "saved"
end

coalesceWriters.settings = function(player, value) return ProfileRepository.writeSettings(player, value) end
coalesceWriters.revealSkip = function(player, value) return ProfileRepository.writeRevealSkip(player, value) end
end
