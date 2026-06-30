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
;
; Engine patches: copy the engine bundle in as installer\dwix-engine.zip BEFORE compiling
; (cp C:\gd\dwix-custom-memoria-<ver>.zip installer\dwix-engine.zip). If present it's bundled and the
; "engine patches" task runs `ff9mapkit setup --install-engine` (backed up, version-aware, graceful if
; Memoria is absent). If you DON'T copy it, the task is harmless -- no zip ships, no engine install runs.

#define MyAppName "Dream World IX"
#define MyAppVersion "1.0.0b9"
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
; The Setup .exe + wizard icon. Canonical art lives in the package (it's also the Qt window icon,
; shipped as wheel data) so there's ONE committed .ico; the installer references it by relative path.
; Regenerate from installer\icon\*.png -- see installer\icon\README.md.
SetupIconFile=..\ff9mapkit\ff9mapkit\workspace\dreamworldix.ico
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SolidCompression=yes
Compression=lzma2

[Messages]
; The Finished-page text is set DYNAMICALLY in [Code] CurPageChanged, keyed on whether the "engine patches"
; task was ticked -- when it was, the installer already applied the patches, so the page should SAY so rather
; than tell the user to do it manually (the b8 confusion). These static values are a fallback only.
FinishedLabelNoIcons=Dream World IX is installed.
FinishedLabel=Dream World IX is installed.

[Tasks]
; Opt-in engine-patch install. Default CHECKED: playing FORKED real fields (the headline feature) needs
; the patched Memoria build, and the install is fully reversible -- it BACKS UP the originals, is version-
; aware (skips if our build is already in place), and degrades to a no-op-with-instructions if Memoria
; isn't installed yet. Power users who only build NOVEL fields (which run on stock Memoria) can untick it.
; The actual work is done by `ff9mapkit setup --install-engine` via bootstrap.ps1 (see {code:EngineArg}).
Name: "engine"; Description: "Install the Memoria engine patches (needed to PLAY forked real fields)"; GroupDescription: "Engine patches:"

[Files]
Source: "bootstrap.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ff9mapkit\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
; Bundled only if you generated it before compiling (see header).
Source: "THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; The engine bundle (3 patched managed DLLs). Bundled only if you copied it in as dwix-engine.zip
; (see header); the "engine" task + bootstrap only act on it when it's actually present.
Source: "dwix-engine.zip"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; The app icon for the Start-Menu shortcut (same .ico as SetupIconFile + the Qt window icon).
Source: "..\ff9mapkit\ff9mapkit\workspace\dreamworldix.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; uv's default tool bin dir is %USERPROFILE%\.local\bin. The launcher exists after the [Run] step below;
; the shortcut is created pointing at it (Windows resolves it once the target appears). IconFilename
; gives the shortcut our icon directly (the console-less launcher carries no embedded icon of its own).
Name: "{autoprograms}\{#MyAppName} (Workspace)"; Filename: "{%USERPROFILE}\.local\bin\ff9mapkit-workspace.exe"; IconFilename: "{app}\dreamworldix.ico"; Comment: "Open the Dream World IX Workspace GUI"
Name: "{autoprograms}\{#MyAppName} on GitHub"; Filename: "{#MyAppURL}"

[Run]
; {code:EngineArg} appends ` -EngineZip "{app}\dwix-engine.zip"` IFF the engine task is ticked AND the
; zip actually shipped -- so the single bootstrap call folds the (backed-up, version-aware) engine
; install into its one `ff9mapkit setup` run. Empty otherwise => plain setup.
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\bootstrap.ps1""{code:EngineArg}"; \
  StatusMsg: "Installing the Python toolchain and Dream World IX (downloads ~150 MB on first run)..."; \
  Flags: waituntilterminated
; Finished-page checkbox: launch the Workspace GUI. Check: only shown if the launcher actually exists
; (i.e. the tool install succeeded). nowait so the wizard closes without waiting on the GUI.
Filename: "{%USERPROFILE}\.local\bin\ff9mapkit-workspace.exe"; Description: "Open Dream World IX (Workspace)"; Flags: postinstall nowait skipifsilent; Check: WorkspaceExists

[UninstallRun]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\bootstrap.ps1"" -Uninstall"; \
  Flags: runhidden; RunOnceId: "UninstallFf9mapkitTool"

[Code]
function WorkspaceExists: Boolean;
begin
  Result := FileExists(ExpandConstant('{%USERPROFILE}\.local\bin\ff9mapkit-workspace.exe'));
end;

// Appended to bootstrap.ps1's parameters: pass the bundled engine zip ONLY when the user ticked the
// "engine" task AND the zip actually shipped (a dev may compile without copying it in). The leading
// space matters -- it's concatenated right after the closing quote of the -File argument.
function EngineArg(Param: String): String;
begin
  if WizardIsTaskSelected('engine') and FileExists(ExpandConstant('{app}\dwix-engine.zip')) then
    Result := ' -EngineZip "' + ExpandConstant('{app}\dwix-engine.zip') + '"'
  else
    Result := '';
end;

// Set the Finished-page text to match what actually happened: if the "engine patches" task ran, the
// installer ALREADY applied them (when Memoria was present), so say that -- don't tell the user to do it
// manually. Otherwise point them at the command to add them. (Mirrors EngineArg's condition.)
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then begin
    if WizardIsTaskSelected('engine') and FileExists(ExpandConstant('{app}\dwix-engine.zip')) then
      WizardForm.FinishedLabel.Caption :=
        'Dream World IX is installed, with the Memoria engine patches — forked real fields are ready.' + #13#10 + #13#10 +
        '(Patches apply only when Memoria is already installed. If you add Memoria later, run' + #13#10 +
        '   ff9mapkit setup --install-engine   to apply them.)'
    else
      WizardForm.FinishedLabel.Caption :=
        'Dream World IX is installed.' + #13#10 + #13#10 +
        'To play FORKED real fields, add the Memoria engine patches:' + #13#10 +
        '   ff9mapkit setup --install-engine' + #13#10 +
        '(or re-run this installer and tick the engine option).';
  end;
end;

// Best-effort read of the saved FF9 path from ~/.ff9mapkit.toml (written by `ff9mapkit setup`), so the
// uninstall reminder can point at the exact engine-backup folder. Returns '' if it can't be read.
function ReadGamePath(): String;
var
  cfg: String;
  lines: TArrayOfString;
  i, p, q: Integer;
  line: String;
begin
  Result := '';
  cfg := ExpandConstant('{%USERPROFILE}\.ff9mapkit.toml');
  if not FileExists(cfg) then exit;
  if not LoadStringsFromFile(cfg, lines) then exit;
  for i := 0 to GetArrayLength(lines) - 1 do begin
    line := Trim(lines[i]);
    if Copy(line, 1, 9) = 'game_path' then begin
      p := Pos('"', line);
      if p > 0 then begin
        q := Pos('"', Copy(line, p + 1, Length(line)));
        if q > 0 then
          Result := Copy(line, p + 1, q - 1);
      end;
    end;
  end;
end;

// After uninstall, remind the user that their GAME wasn't changed -- the engine patches (if applied)
// are a separate Memoria mod, and their originals are backed up. Skipped on a silent uninstall.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  game, backups, msg: String;
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent()) then begin
    game := ReadGamePath();
    if game <> '' then
      backups := game + '/dwix-engine-backups/'
    else
      backups := 'your FINAL FANTASY IX folder, under  dwix-engine-backups/';
    msg :=
      'Dream World IX has been removed (the ff9mapkit tool was uninstalled via uv).' + #13#10 + #13#10 +
      'This did NOT change your game. If you installed the engine patches, your original Memoria DLLs' + #13#10 +
      'are backed up in:' + #13#10 + #13#10 +
      '    ' + backups + #13#10 + #13#10 +
      'To restore stock Memoria, copy the backed-up DLLs back over  x64/FF9_Data/Managed  and' + #13#10 +
      'x86/FF9_Data/Managed  (or just re-run the Memoria patcher).' + #13#10 + #13#10 +
      'Left in place: uv + its Python (shared), and your settings/extracted assets in' + #13#10 +
      '%LOCALAPPDATA%\ff9mapkit.';
    MsgBox(msg, mbInformation, MB_OK);
  end;
end;
