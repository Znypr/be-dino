-- Studio MCP execute_luau, CLIENT datamodel, Play mode. Reads what the weather draws; writes no game state.
-- Used with the admin remote: AdminAction:InvokeServer("startWeather", id, seconds) / ("stopWeather").
local L = game:GetService("Lighting")
shared.S1wx = function(label)
  local n, rate = 0, 0
  for _, d in workspace:GetDescendants() do
    if d:IsA("ParticleEmitter") and d.Name == "WeatherParticles" and d.Enabled and d.Rate > 0 then n += 1; rate += d.Rate end
  end
  local beams = 0
  local fx = workspace:FindFirstChild("LocalWeatherFX")
  if fx then for _, d in fx:GetDescendants() do if d:IsA("Beam") and d.Enabled then beams += 1 end end end
  local g, b, r, h = L:FindFirstChild("WeatherGrade"), L:FindFirstChild("WeatherBloom"), L:FindFirstChild("WeatherRays"), L:FindFirstChild("WorldHaze")
  return string.format("%s | weather=%s | emittersOn=%d rateSum=%.0f beamsOn=%d | bright=%.2f expo=%.2f fogEnd=%.0f | haze dens=%.2f | grade sat=%.2f | bloom=%.2f | rays=%.2f",
    label, tostring(workspace:GetAttribute("WeatherId")), n, rate, beams, L.Brightness, L.ExposureCompensation, L.FogEnd, h.Density, g.Saturation, b.Intensity, r.Intensity)
end
