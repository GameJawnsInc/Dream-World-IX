<#
  Dream World IX / ff9mapkit -- uv bootstrap.

  Install path (default):
    1. ensure `uv` is present (a single self-contained binary; NO system Python needed)
    2. provision a managed CPython (its own step, so a fresh uv's first download is isolated)
    3. `uv tool install ff9mapkit[gui,assets,save]` (with one retry) -> uv fetches every wheel from
       PyPI and puts two launchers on PATH:
          ff9mapkit            (CLI)
          ff9mapkit-workspace  (the PySide6 Workspace GUI, console-less)

  Why this design is license-clean: every dependency is fetched FROM PyPI onto THIS machine by the
  user's own uv -- the project (and this installer) redistribute nothing but their own MIT code. So
  Qt's LGPL relink/source-offer duties and the proprietary FMOD binaries pulled transitively by UnityPy
  never attach to the distribution.

  Robustness notes (lessons from a real failed run):
    * We do NOT set $ErrorActionPreference='Stop'. uv's install script emits benign non-terminating
      errors; under Stop those throw and abort the bootstrap right after uv installs but BEFORE the
      tool install -- a SILENT failure (uv present, no ff9mapkit). We check exit codes explicitly.
    * The tool install is retried once, and we verify ff9mapkit.exe actually exists afterward.
    * On any failure we print a clear message and PAUSE so the window doesn't close before you read it.

  Uninstall path (-Uninstall): `uv tool uninstall ff9mapkit`. uv itself and any managed CPython are
  left in place (they may be shared by other tools).

  Note: uv's managed CPython needs the Microsoft Visual C++ runtime (vcruntime140.dll), present on
  essentially all current Windows 10/11. If a launch ever fails with a missing-vcruntime error, install
  "Microsoft Visual C++ Redistributable (x64)".
#>
#requires -version 5
param(
  [switch] $Uninstall,
  [string] $PythonVersion = "3.12",
  [string] $Spec = "ff9mapkit[gui,assets,save]"
)

function Fail($msg) {
  Write-Host ""
  Write-Host "====================================================================" -ForegroundColor Red
  Write-Host " Dream World IX setup did NOT complete:" -ForegroundColor Red
  Write-Host "   $msg" -ForegroundColor Red
  Write-Host " The messages above show what went wrong. Re-running the installer" -ForegroundColor Red
  Write-Host " usually fixes a transient download failure; otherwise report it at" -ForegroundColor Red
  Write-Host " https://github.com/GameJawnsInc/Dream-World-IX/issues" -ForegroundColor Red
  Write-Host "====================================================================" -ForegroundColor Red
  [void](Read-Host "Press Enter to close")
  exit 1
}

function Find-Uv {
  $cmd = Get-Command uv -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $candidate = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
  if (Test-Path $candidate) { return $candidate }
  return $null
}

if ($Uninstall) {
  $uv = Find-Uv
  if ($uv) {
    Write-Host "Removing the ff9mapkit tool..."
    & $uv tool uninstall ff9mapkit
  } else {
    Write-Host "uv not found; nothing to uninstall."
  }
  exit 0
}

# --- 1. Ensure uv is present -------------------------------------------------
$uv = Find-Uv
if (-not $uv) {
  Write-Host "Installing uv (the Python toolchain manager)..."
  # Run uv's bootstrap with a NON-strict error preference so its benign non-terminating errors
  # cannot abort us (this was the silent-failure bug). We verify success by locating uv.exe.
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
  } catch {
    Write-Host "uv bootstrap reported: $($_.Exception.Message)"
  } finally {
    $ErrorActionPreference = $prev
  }
  $uv = Find-Uv
  if (-not $uv) { Fail "could not install uv (no uv.exe found after the bootstrap)." }
}
Write-Host "Using uv at: $uv"

# --- 2. Provision the managed CPython (isolated step) ------------------------
Write-Host "Provisioning Python $PythonVersion (the first run downloads it)..."
& $uv python install $PythonVersion

# --- 3. Install ff9mapkit + its launchers (with one retry) -------------------
function Install-Tool {
  Write-Host "Installing $Spec"
  Write-Host "(fetching all dependencies from PyPI -- ~150 MB the first time)..."
  & $uv tool install --python $PythonVersion --force $Spec
  return $LASTEXITCODE
}
$code = Install-Tool
if ($code -ne 0) {
  Write-Host "First attempt failed (exit $code). Retrying once in 3s..."
  Start-Sleep -Seconds 3
  $code = Install-Tool
}
if ($code -ne 0) { Fail "uv tool install failed (exit code $code)." }

# Put uv's tool bin dir on PATH for future shells (CLI: `ff9mapkit`).
& $uv tool update-shell

# Verify the launchers actually landed -- never report success on a partial install.
$bin = (& $uv tool dir --bin).Trim()
if (-not (Test-Path (Join-Path $bin "ff9mapkit.exe"))) {
  Fail "install reported success but ff9mapkit.exe is missing from $bin."
}

Write-Host ""
Write-Host "===================================================================="
Write-Host " Dream World IX installed."
Write-Host "   GUI:  $bin\ff9mapkit-workspace.exe   (Start Menu shortcut created)"
Write-Host "   CLI:  ff9mapkit   (open a NEW terminal so PATH refreshes, then 'ff9mapkit doctor')"
Write-Host ""
Write-Host " Next: point the kit at your legally-owned FF9 install + extract base assets:"
Write-Host "   ff9mapkit doctor"
Write-Host "   ff9mapkit extract-templates"
Write-Host "===================================================================="
exit 0
