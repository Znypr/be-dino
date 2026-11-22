# Be Dino Desk install (docs/247, BD-1292): build the UI, smoke test, package, swap into %USERPROFILE%\Applications\Be Dino Desk,
# desktop + start-menu shortcut. Usage: powershell -ExecutionPolicy Bypass -File apps\be-dino-desk\build.ps1 [-SkipSmoke]
# First time on a machine: npm install here and in ui\ (or copy node_modules from the Footage Desk, same versions).
param([switch]$SkipSmoke)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$electron = Join-Path $root 'node_modules\electron\dist\electron.exe'
if (-not (Test-Path $electron)) { throw 'Run npm install (and node node_modules\electron\install.js) first.' }

Push-Location (Join-Path $root 'ui')
try { & npm run build; if ($LASTEXITCODE -ne 0) { throw 'UI build failed.' } } finally { Pop-Location }

if (-not $SkipSmoke) {
    $p = Start-Process -FilePath $electron -ArgumentList '.', '--smoke' -WorkingDirectory $root -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { throw "Smoke test failed (exit $($p.ExitCode))." }
    Write-Output 'Smoke test passed.'
}

$out = Join-Path $root 'release'
$app = Join-Path $out 'Be Dino Desk-win32-x64'
& node (Join-Path $root 'node_modules\@electron\packager\bin\electron-packager.mjs') $root 'Be Dino Desk' `
    --electron-version=44.9.0 --platform=win32 --arch=x64 "--icon=$(Join-Path $root 'build\icon.ico')" `
    --executable-name='Be Dino Desk' "--out=$out" --overwrite --asar `
    '--ignore=^/release' '--ignore=^/ui' '--ignore=^/build\.ps1' `
    --win32metadata.ProductName='Be Dino Desk' --win32metadata.FileDescription='Be Dino Desk'
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed.' }

$dest = Join-Path $env:USERPROFILE 'Applications\Be Dino Desk'
$exe = Join-Path $dest 'Be Dino Desk.exe'
if (Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith($dest + '\', [StringComparison]::OrdinalIgnoreCase) }) {
    throw 'Be Dino Desk is open. Close it, then run this again.'
}
$old = "$dest.old"
if (Test-Path $old) { Remove-Item -LiteralPath $old -Recurse -Force }
if (Test-Path $dest) { Rename-Item -LiteralPath $dest -NewName (Split-Path $old -Leaf) }
New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
Copy-Item -LiteralPath $app -Destination $dest -Recurse

$ws = New-Object -ComObject WScript.Shell
foreach ($dir in @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'))) {
    $lnk = $ws.CreateShortcut((Join-Path $dir 'Be Dino Desk.lnk'))
    $lnk.TargetPath = $exe
    $lnk.WorkingDirectory = $dest
    $lnk.IconLocation = "$exe,0"
    $lnk.Save()
}
if (Test-Path $old) { Remove-Item -LiteralPath $old -Recurse -Force }
# the repo the installed app shows: the main checkout (first entry of git worktree list), never a temporary worktree
$main = ((& git -C $root worktree list --porcelain) | Select-Object -First 1) -replace '^worktree ', ''
$cfg = Join-Path $env:APPDATA 'Be Dino Desk'
New-Item -ItemType Directory -Force $cfg | Out-Null
Set-Content -LiteralPath (Join-Path $cfg 'repo.txt') -Value ($main -replace '/', '\') -Encoding ASCII
Write-Output "Installed: $exe (shows $main)"
