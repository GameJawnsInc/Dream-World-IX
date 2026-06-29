<#
  Dream World IX / ff9mapkit -- uv bootstrap.

  Install path (default):
    1. ensure `uv` is present (a single self-contained binary; NO system Python needed)
    2. `uv tool install ff9mapkit[gui,assets,save]` -> uv fetches a managed CPython + every wheel from
       PyPI and puts two launchers on PATH:
          ff9mapkit            (CLI)
          ff9mapkit-workspace  (the PySide6 Workspace GUI, console-less)

  Why this design is license-clean: every dependency is fetched FROM PyPI onto THIS machine by the
  user's own uv -- the project (and this installer) redistribute nothing but their own MIT code. So
  Qt's LGPL relink/source-offer duties and the proprietary FMOD binaries pulled transitively by UnityPy
  never attach to the distribution. (A frozen .exe that baked the deps in WOULD trigger all of those.)

  Uninstall path (-Uninstall): `uv tool uninstall ff9mapkit`. uv itself and any managed CPython are
  left in place (they may be shared by other tools); remove them with `uv self uninstall` if desired.

  Note: uv's managed CPython needs the Microsoft Visual C++ runtime (vcruntime140.dll), which is present
  on essentially all current Windows 10/11 installs (UnityPy needs it too). If a launch ever fails with
  a missing-vcruntime error, install "Microsoft Visual C++ Redistributable (x64)".
#>
#requires -version 5
param(
  [switch] $Uninstall,
  [string] $PythonVersion = "3.12",
  [string] $Spec = "ff9mapkit[gui,assets,save]"
)
$ErrorActionPreference = "Stop"

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
    Write-Host "uv not found; nothing to uninstall (run 'uv tool uninstall ff9mapkit' manually if needed)."
  }
  exit 0
}

$uv = Find-Uv
if (-not $uv) {
  Write-Host "Installing uv (the Python toolchain manager)..."
  Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
  $uv = Find-Uv
  if (-not $uv) { throw "uv install did not produce uv.exe; aborting." }
}
Write-Host "Using uv at: $uv"

Write-Host "Installing $Spec"
Write-Host "(fetching a managed CPython $PythonVersion + all dependencies from PyPI -- ~150 MB first run)..."
& $uv tool install --python $PythonVersion --force $Spec
if ($LASTEXITCODE -ne 0) { throw "uv tool install failed (exit code $LASTEXITCODE)." }

# Put uv's tool bin dir on PATH for future shells (so `ff9mapkit` resolves in a new terminal).
& $uv tool update-shell | Out-Null

$bin = (& $uv tool dir --bin).Trim()
Write-Host ""
Write-Host "===================================================================="
Write-Host " Dream World IX installed."
Write-Host "   GUI:  $bin\ff9mapkit-workspace.exe   (Start Menu shortcut created)"
Write-Host "   CLI:  ff9mapkit   (open a NEW terminal so PATH refreshes, then run 'ff9mapkit doctor')"
Write-Host ""
Write-Host " Next: point the kit at your legally-owned FF9 install and run one-time asset extraction:"
Write-Host "   ff9mapkit doctor"
Write-Host "   ff9mapkit extract-templates"
Write-Host "===================================================================="
exit 0
