-- end of run: totals and the machine-readable report (appended last by tools/verify_remote_fuzz.py)
local failed = 0
for _, c in CHECKS do if not c.ok then failed += 1 end end
print("DONE|" .. #CHECKS .. "|" .. failed)
for _, line in REPORT do print("REPORT|" .. line) end
for _, c in CHECKS do print("CHECK|" .. (if c.ok then "PASS" else "FAIL") .. "|" .. c.name .. "|" .. c.detail) end
for name, seconds in TIMES do print(string.format("TIME|%s|%.2f", name, seconds)) end
