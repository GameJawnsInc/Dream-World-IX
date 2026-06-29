; Inno Setup script -- Dream World IX / ff9mapkit bootstrap installer.
;
; Produces a small DreamWorldIX-Setup.exe that installs `uv` and then runs `uv tool install
; ff9mapkit[gui,assets,save]`. The heavy lifting (fetching CPython + all wheels from PyPI) is done by uv
; on the user's machine, so this installer redistributes NOTHING but its own files -- the license-clean
; posture (see ..\docs and tools\gen_third_party_notices.py). Requires internet on first run.
;
; Build it:  install Inno Setup 6 (https://jrsoftware.org/isdl.php), then either open this file in the
;            Inno Setup Compiler and press F9, or run:  ISCC.exe installer\ff9mapkit.iss
; Output:    installer\Output\DreamWorldIX-Setup.exe
;
; Optional (recommended) before compiling: drop a generated THIRD-PARTY-NOTICES.txt next to this script
; (py tools\gen_third_party_notices.py -o installer\THIRD-PARTY-NOTICES.txt) -- it is bundled if present.

#define MyAppName "Dream World IX"
#define MyAppVersion "1.0.0b3"
#define MyAppPublisher "GameJawnsInc"
#define MyAppURL "https://github.com/GameJawnsInc/Dream-World-IX"

[Setup]
; Stable AppId -- do not change between versions (it identifies the app for upgrades/uninstall).
AppId={{8F3B2A14-2C9D-4E77-9B1A-7C0FF9F90001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
; uv installs the actual tool into the user profile; this dir just holds the bootstrap script + notices.
DefaultDirName={localappdata}\Dream World IX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; THE FIX for uv "os error 448 / untrusted mount point": Inno Setup 6.7.0+ enables Windows
; RedirectionGuard on the Setup process by default, and the child powershell -> uv inherits it via
; the process token. RedirectionGuard blocks traversal of NTFS junctions created by a non-admin user --
; and uv's managed-Python minor-version link IS such a junction, so `uv tool install` fails (works from
; a normal shell, fails only under the installer). For a PrivilegesRequired=lowest installer the
; mitigation buys ~nothing (the user owns both the junction and the target), so we turn it off.
; Refs: Inno Setup 6.7.0 what's-new; MSRC RedirectionGuard; astral-sh/uv#19622.
RedirectionGuard=no
OutputBaseFilename=DreamWorldIX-Setup
LicenseFile=..\ff9mapkit\LICENSE
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SolidCompression=yes
Compression=lzma2

[Files]
Source: "bootstrap.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ff9mapkit\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
; Bundled only if you generated it before compiling (see header).
Source: "THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; uv's default tool bin dir is %USERPROFILE%\.local\bin. The launcher exists after the [Run] step below;
; the shortcut is created pointing at it (Windows resolves it once the target appears).
Name: "{autoprograms}\{#MyAppName} (Workspace)"; Filename: "{%USERPROFILE}\.local\bin\ff9mapkit-workspace.exe"; Comment: "Open the Dream World IX Workspace GUI"
Name: "{autoprograms}\{#MyAppName} on GitHub"; Filename: "{#MyAppURL}"

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\bootstrap.ps1"""; \
  StatusMsg: "Installing the Python toolchain and Dream World IX (downloads ~150 MB on first run)..."; \
  Flags: waituntilterminated
Filename: "{#MyAppURL}#start-here"; Description: "Open the Setup guide in your browser"; Flags: postinstall shellexec nowait skipifsilent

[UninstallRun]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\bootstrap.ps1"" -Uninstall"; \
  Flags: runhidden; RunOnceId: "UninstallFf9mapkitTool"
