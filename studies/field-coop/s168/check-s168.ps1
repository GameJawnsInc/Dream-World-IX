# check-s168.ps1 -- the s168 co-op package, step 0: a READ-ONLY compare of this machine's FF9 folder with the package.
#
# Run it on BOTH machines (the desktop and the laptop), with FF9 closed, from the package folder:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\check-s168.ps1
# If FF9 is not in the default Steam folder, name it:
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\check-s168.ps1 -Game "D:\SteamLibrary\steamapps\common\FINAL FANTASY IX"
#
# It changes nothing. Five parts:
#   0. the package itself: its dlls\ and dlls-s167\ files against HASHES.txt, and its two lists (a bad unzip or copy shows here)
#   1. this install's six DLLs against the package's dlls\ (the s168 build), and a line naming which engine it holds now
#   2. the three mod folders, file by file
#   3. the base game's world data
#   4. the three folders listed in Memoria.ini [Mod] FolderNames, and world-map files hiding in other mod folders
# The co-op version check and s167's world fingerprint both need the two machines to match, so every line below
# must say OK on BOTH machines. The last line sums it up. If this install holds the s167 engine (the fallback), part 1
# says DIFFERS by design and the summary says so.
param([string]$Game = 'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX')
$ErrorActionPreference = 'Stop'
$pkg = $PSScriptRoot
$script:bad = 0
# the s167 Assembly-CSharp.dll (used only when HASHES.txt has no dlls-s167 line to read it from)
$S167_FALLBACK = '12be3220520813a6dd4bc365b38a1f257eefe7819552b4f290bcefc9b0464096'
function Say([bool]$ok, [string]$text) {
    if ($ok) { Write-Output ('OK       ' + $text) } else { Write-Output ('DIFFERS  ' + $text); $script:bad++ }
}
function Sha([byte[]]$bytes) {
    $h = [System.Security.Cryptography.SHA256]::Create()
    return (-join ($h.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }))
}
function FileSha([string]$p) {
    return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()
}
if (-not (Test-Path -LiteralPath (Join-Path $Game 'x64\FF9_Data\Managed'))) {
    Write-Output ('No FF9 install at "' + $Game + '" -- pass -Game "<your FINAL FANTASY IX folder>"')
    exit 2
}
$Game = (Resolve-Path -LiteralPath $Game).ProviderPath
Write-Output ('Checking ' + $Game + ' against the package in ' + $pkg)

# read HASHES.txt once: every "<sha256> *<set>/<arch>/<name>" line, where <set> is dlls (s168) or dlls-s167 (the fallback)
$entries = @()
$hashesPath = Join-Path $pkg 'HASHES.txt'
if (Test-Path -LiteralPath $hashesPath) {
    foreach ($line in Get-Content -LiteralPath $hashesPath) {
        if ($line -notmatch '^([0-9a-f]{64}) \*(dlls|dlls-s167)/(x64|x86)/(.+)$') { continue }
        $entries += ,@($Matches[1], $Matches[2], $Matches[3], $Matches[4])
    }
}

# 0. the package's own DLL files, against HASHES.txt
Write-Output '-- 0. the package itself (dlls and dlls-s167 against HASHES.txt)'
if (-not (Test-Path -LiteralPath $hashesPath)) {
    Say $false 'HASHES.txt is missing from the package folder'
}
$nMain = 0; $nOld = 0
foreach ($e in $entries) {
    if ($e[1] -eq 'dlls') { $nMain++ } else { $nOld++ }
    $p = Join-Path $pkg ($e[1] + '\' + $e[2] + '\' + $e[3])
    $ok = $false
    if (Test-Path -LiteralPath $p) { $ok = ((FileSha $p) -eq $e[0]) }
    Say $ok ('package ' + $e[1] + '\' + $e[2] + '\' + $e[3])
}
Say ($nMain -eq 6) ('HASHES.txt lists ' + $nMain + ' file(s) for dlls (6 expected)')
Say ($nOld -ge 2) ('HASHES.txt lists ' + $nOld + ' file(s) for dlls-s167 (at least the two Assembly-CSharp.dll expected)')
# parts 2 and 3 read these two lists; a package without them stops here, with a part-0 line, instead of a PowerShell error
$absent = @(@('FOLDERS-MANIFEST.txt', 'DATA-WORLD-HASHES.txt') | Where-Object { -not (Test-Path -LiteralPath (Join-Path $pkg $_)) })
foreach ($m in $absent) { Say $false ('package ' + $m + ' is missing') }
if ($absent.Count -gt 0) {
    Write-Output ([string]$script:bad + ' check(s) DIFFER: fix those lines before playing (see the README, step 0).')
    exit 1
}

# the two engines this package knows: the s168 build (dlls) and the s167 fallback (dlls-s167)
$s168 = ''; $s167 = $S167_FALLBACK
foreach ($e in $entries) {
    if ($e[2] -eq 'x64' -and $e[3] -eq 'Assembly-CSharp.dll') {
        if ($e[1] -eq 'dlls') { $s168 = $e[0] } else { $s167 = $e[0] }
    }
}
# the s166 Assembly-CSharp.dll (the engine before s167): named so a copy that did not land, or the s166 rollback, reads by name
$S166_SHA = 'b24e0123ac93960c78a841a12cb30587756c422e2f0b4fc406dd3bd51fc128e7'
function EngineName([string]$sha) {
    if ($sha -eq '') { return 'other (no Assembly-CSharp.dll)' }
    if ($s168 -ne '' -and $sha -eq $s168) { return 's168 (the package)' }
    if ($sha -eq $s167) { return 's167 (the fallback)' }
    if ($sha -eq $S166_SHA) { return 's166 (the old engine)' }
    return ('other ' + $sha.Substring(0, 16))
}

# 1. the six DLLs (HASHES.txt, the dlls set), then which engine this install holds
Write-Output '-- 1. the DLLs'
foreach ($e in $entries) {
    if ($e[1] -ne 'dlls') { continue }
    $p = Join-Path $Game ($e[2] + '\FF9_Data\Managed\' + $e[3])
    $ok = $false
    if (Test-Path -LiteralPath $p) { $ok = ((FileSha $p) -eq $e[0]) }
    Say $ok ($e[2] + '\' + $e[3])
}
$cur = @{}
foreach ($arch in @('x64', 'x86')) {
    $p = Join-Path $Game ($arch + '\FF9_Data\Managed\Assembly-CSharp.dll')
    $cur[$arch] = ''
    if (Test-Path -LiteralPath $p) { $cur[$arch] = FileSha $p }
}
$engine = EngineName $cur['x64']
Write-Output ('         engine in this install now: ' + $engine)
Say ($cur['x64'] -eq $cur['x86']) ('x64 and x86 hold the same Assembly-CSharp.dll (x64 ' + (EngineName $cur['x64']) + ', x86 ' + (EngineName $cur['x86']) + ')')
$onS167 = ($engine -like 's167*') -and ((EngineName $cur['x86']) -like 's167*')

# 2. the three mod folders, file by file (FOLDERS-MANIFEST.txt); tool backups (.bak-) and .lock files are ignored
Write-Output '-- 2. FF9CustomMap-world, FF9CustomMap-schema, FF9CustomMap-msgs'
$want = @{}
foreach ($line in Get-Content -LiteralPath (Join-Path $pkg 'FOLDERS-MANIFEST.txt') -Encoding UTF8) {
    $i = $line.IndexOf(' *')
    if ($i -lt 0) { continue }
    $want[$line.Substring($i + 2)] = $line.Substring(0, $i)
}
$folders = @('FF9CustomMap-world', 'FF9CustomMap-schema', 'FF9CustomMap-msgs')
foreach ($f in $folders) {
    $root = Join-Path $Game $f
    $missing = 0; $differ = 0; $extra = 0; $n = 0; $shown = @()
    foreach ($rel in @($want.Keys | Where-Object { $_.StartsWith($f + '/') })) {
        $n++
        $p = Join-Path $Game ($rel.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $p)) { $missing++; if ($shown.Count -lt 3) { $shown += ('missing ' + $rel) }; continue }
        if ((FileSha $p) -ne $want[$rel]) {
            $differ++; if ($shown.Count -lt 3) { $shown += ('differs ' + $rel) }
        }
    }
    if (Test-Path -LiteralPath $root) {
        foreach ($file in @(Get-ChildItem -LiteralPath $root -Recurse -File -Force)) {
            if ($file.Name -like '*.bak-*' -or $file.Name -like '*.lock') { continue }
            $rel = $f + '/' + $file.FullName.Substring($root.Length + 1).Replace('\', '/')
            if (-not $want.ContainsKey($rel)) { $extra++; if ($shown.Count -lt 3) { $shown += ('extra ' + $rel) } }
        }
    }
    Say (($missing + $differ + $extra) -eq 0) ($f + ': ' + $n + ' files, ' + $missing + ' missing, ' + $differ + ' differ, ' + $extra + ' extra')
    foreach ($s in $shown) { Write-Output ('           e.g. ' + $s) }
}

# 3. the base world data the fingerprint reads (DATA-WORLD-HASHES.txt; compared with every CR removed, as the fingerprint does)
Write-Output '-- 3. StreamingAssets\Data\World (the base game data)'
foreach ($line in Get-Content -LiteralPath (Join-Path $pkg 'DATA-WORLD-HASHES.txt')) {
    if ($line -notmatch '^([0-9a-f]{64}) ([0-9a-f]{64}) \*(.+)$') { continue }
    $wantNoCr = $Matches[2]; $rel = $Matches[3]
    $p = Join-Path $Game ($rel.Replace('/', '\'))
    $ok = $false
    if (Test-Path -LiteralPath $p) {
        $b = [System.IO.File]::ReadAllBytes($p)
        $keep = New-Object 'System.Collections.Generic.List[byte]' ($b.Length)
        foreach ($x in $b) { if ($x -ne 13) { $keep.Add($x) } }
        $ok = ((Sha $keep.ToArray()) -eq $wantNoCr)
    }
    Say $ok $rel
}

# 4. no OTHER mod folder may hold a world-map file: the engine would read it before or after the package's, and the two
#    machines' world maps would differ (FF9CustomMap outranks FF9CustomMap-world)
Write-Output '-- 4. Memoria.ini [Mod] FolderNames: the three package folders listed, and world-map files in the other mod folders'
$ini = Join-Path $Game 'Memoria.ini'
$fl = ''
if (Test-Path -LiteralPath $ini) {
    $m = Select-String -LiteralPath $ini -Pattern '^\s*FolderNames\s*=' | Select-Object -First 1
    if ($m) { $fl = $m.Line.Trim() }
}
Write-Output ('         Memoria.ini: ' + $fl)
$names = @([regex]::Matches($fl, '"([^"]+)"') | ForEach-Object { $_.Groups[1].Value })
# the three package folders must be in the list: the Memoria launcher rewrites it, and a folder left out is never read
foreach ($f in $folders) { Say ($names -contains $f) ($f + ' is listed in [Mod] FolderNames') }
foreach ($name in $names) {
    if ($folders -contains $name) { continue }
    $root = Join-Path $Game $name
    $stray = @()
    foreach ($sub in @('FF9_Data\WorldMap', 'StreamingAssets\Data\World',
                       'StreamingAssets\assets\resources\commonasset\eventengine\eventbinary\world')) {
        $d = Join-Path $root $sub
        if (Test-Path -LiteralPath $d) {
            foreach ($file in @(Get-ChildItem -LiteralPath $d -Recurse -File -Force)) {
                if ($file.Name -like '*.bak-*' -or $file.Name -like '*.lock') { continue }
                $stray += $file.FullName
            }
        }
    }
    Say ($stray.Count -eq 0) ($name + ': ' + $stray.Count + ' world-map file(s)')
    foreach ($s in @($stray | Select-Object -First 3)) { Write-Output ('           e.g. ' + $s) }
}

if ($script:bad -eq 0) {
    Write-Output 'ALL OK: this machine matches the s168 package.'
    exit 0
}
Write-Output ([string]$script:bad + ' check(s) DIFFER: fix those lines before playing (see the README, step 0).')
if ($onS167) {
    Write-Output 'NOTE: this install runs the s167 engine (the fallback), so the two Assembly-CSharp.dll lines in part 1 differ from the s168 package by design.'
    Write-Output '      That is expected only where the README puts s167 on this machine (the version check, B25, or a rollback). Any other DIFFERS line above still needs fixing.'
}
exit 1
