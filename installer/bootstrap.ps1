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

# --- 1c. Self-heal a DANGLING managed-Python minor-version junction ----------
# uv links `cpython-<minor>-...` -> `cpython-<patch>-...` with a Windows JUNCTION. A run previously
# blocked by RedirectionGuard (Inno < this fix) can leave that junction dangling, and uv's --reinstall
# will NOT replace it (astral-sh/uv#19622). Clear ONLY a dangling one (target unreachable), and delete
# the REPARSE POINT ONLY -- never Remove-Item -Recurse, which can follow the link into the real patch dir.
function Clear-DanglingPythonLink {
  param([string] $Ver)
  $roots = @("$env:APPDATA\uv\python", "$env:LOCALAPPDATA\uv\python")
  if ($env:UV_PYTHON_INSTALL_DIR) { $roots = ,"$env:UV_PYTHON_INSTALL_DIR" + $roots }
  foreach ($root in ($roots | Select-Object -Unique)) {
    $link = Join-Path $root "cpython-$Ver-windows-x86_64-none"
    if (Test-Path -LiteralPath $link) {
      $it = Get-Item -LiteralPath $link -Force
      $isLink = [bool]($it.Attributes -band [IO.FileAttributes]::ReparsePoint)
      if ($isLink -and -not (Test-Path -LiteralPath (Join-Path $link "python.exe"))) {
        Write-Host "Clearing a dangling Python minor-version junction: $link"
        try { [System.IO.Directory]::Delete($link, $false) } catch {}
      }
    }
  }
}
Clear-DanglingPythonLink -Ver $PythonVersion

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

# --- 4. First-time setup: detect FF9, remember it, extract base assets, report Memoria ----------
# `ff9mapkit setup` does the whole bring-your-own-install step in one shot. Non-fatal: if FF9 isn't
# auto-detected it just exits non-zero and we tell the user how to point it at their install.
$ff9 = Join-Path $bin "ff9mapkit.exe"
Write-Host ""
Write-Host "Running first-time setup (detecting your FINAL FANTASY IX install)..."
& $ff9 setup
$setupRc = $LASTEXITCODE

Write-Host ""
Write-Host "===================================================================="
Write-Host " Dream World IX installed."
Write-Host "   GUI:  $bin\ff9mapkit-workspace.exe   (Start Menu shortcut created)"
Write-Host "   CLI:  ff9mapkit   (open a NEW terminal so PATH refreshes)"
if ($setupRc -eq 0) {
  Write-Host ""
  Write-Host " You're set up. To play FORKED real fields, install the engine bundle (optional):"
  Write-Host "     ff9mapkit setup --install-engine <dwix-custom-memoria.zip>"
} else {
  Write-Host ""
  Write-Host " Setup couldn't finish automatically (FF9 not found, or UnityPy/extract issue)."
  Write-Host " Open a NEW terminal and run:"
  Write-Host "     ff9mapkit setup --game `"<path to your FINAL FANTASY IX folder>`""
}
Write-Host "===================================================================="
exit 0
