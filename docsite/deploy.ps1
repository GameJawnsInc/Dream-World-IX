# deploy.ps1 -- publish the Dream World IX Manual to https://jawnston.com/ff9docs/
#
# Builds the site fresh (the build FAILS on a broken link/anchor/command, so a red build never
# deploys), tars it, uploads one archive, and swaps it into place near-atomically with a
# one-version rollback kept on the server:
#
#   /var/www/jawnston/ff9docs        <- live
#   /var/www/jawnston/ff9docs.old    <- the previous deploy (rollback: swap the two back)
#
# No Caddyfile change is involved: jawnston.com's root file_server serves the subdirectory
# as-is (the site is built on document-relative paths, so it works under any prefix).
# Mirrors the conventions of C:\gd\JawnRPG\webpage\deploy-site.ps1.
#
# Usage:
#   .\deploy.ps1               # build + deploy
#   .\deploy.ps1 -SkipBuild    # deploy whatever docsite/_site already holds

param(
    [string]$SshHost = "mygame",
    [string]$RemoteRoot = "/var/www/jawnston",
    [string]$SiteName = "ff9docs",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$siteDir   = Join-Path $scriptDir "_site"

$startTime = Get-Date

# --- 1. Build (the gates are the pre-deploy check) ---
if ($SkipBuild) {
    Write-Host "[1/4] Skipping build (-SkipBuild) - deploying existing _site." -ForegroundColor DarkGray
} else {
    Write-Host "[1/4] Building the site (link/anchor/command gates run here)..." -ForegroundColor Yellow
    Push-Location $repoRoot
    try {
        py docsite/build.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Build failed (exit $LASTEXITCODE) - nothing deployed." -ForegroundColor Red
            exit 1
        }
    } finally {
        Pop-Location
    }
}
if (-not (Test-Path (Join-Path $siteDir "index.html"))) {
    Write-Host "No built site at $siteDir (missing index.html)." -ForegroundColor Red
    exit 1
}

# --- 2. Pack ---
Write-Host "[2/4] Packing _site..." -ForegroundColor Yellow
$archive = Join-Path $env:TEMP "ff9docs-site.tar.gz"
if (Test-Path $archive) { Remove-Item $archive -Force }
tar -czf $archive -C $siteDir .
if ($LASTEXITCODE -ne 0) {
    Write-Host "tar failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
$sizeMb = [math]::Round((Get-Item $archive).Length / 1MB, 2)
Write-Host "      $sizeMb MB" -ForegroundColor DarkGray

# --- 3. Upload ---
Write-Host "[3/4] Uploading archive..." -ForegroundColor Yellow
scp $archive "${SshHost}:/tmp/ff9docs-site.tar.gz"
if ($LASTEXITCODE -ne 0) {
    Write-Host "scp failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

# --- 4. Extract to a staging dir, swap live, keep one rollback ---
Write-Host "[4/4] Swapping into place on the server..." -ForegroundColor Yellow
$remoteScript = @'
set -e
ROOT=/var/www/jawnston
NAME=ff9docs
rm -rf "$ROOT/$NAME.new"
mkdir -p "$ROOT/$NAME.new"
tar -xzf /tmp/ff9docs-site.tar.gz -C "$ROOT/$NAME.new"
test -f "$ROOT/$NAME.new/index.html"
chown -R caddy:caddy "$ROOT/$NAME.new"
rm -rf "$ROOT/$NAME.old"
if [ -d "$ROOT/$NAME" ]; then mv "$ROOT/$NAME" "$ROOT/$NAME.old"; fi
mv "$ROOT/$NAME.new" "$ROOT/$NAME"
rm -f /tmp/ff9docs-site.tar.gz
echo "Swapped. Previous deploy kept at $ROOT/$NAME.old"
'@
ssh $SshHost $remoteScript
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Remote swap failed - the live site was NOT touched unless the swap itself" -ForegroundColor Red
    Write-Host "errored mid-move (in that case: ssh $SshHost and inspect $RemoteRoot)." -ForegroundColor Red
    exit 1
}
Remove-Item $archive -Force

# --- Done ---
$elapsed = [math]::Round(((Get-Date) - $startTime).TotalSeconds, 1)
Write-Host ""
Write-Host "Deployed in ${elapsed}s" -ForegroundColor Green
Write-Host "Live at: https://jawnston.com/ff9docs/" -ForegroundColor Green
Write-Host "Rollback: ssh $SshHost, swap $RemoteRoot/$SiteName and $RemoteRoot/$SiteName.old" -ForegroundColor DarkGray
Write-Host ""
