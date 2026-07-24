# FBX-PATHS — the summon-effect FBX/clip load-path spec (TRANSPLANT.md risk #7)

**Task:** pin the summon-effect FBX/clip load paths BEFORE `summons/deploy.py` is coded. Read-only
source recon (`C:/gd/FFIX/Memoria/Assembly-CSharp`, pinned build `6b8bb2d5`) + reconciliation against
the PROVEN rung-7 build (`studies/custom-summons/rung7-creature/`) and the live FLIGHT-era
`thomas_manifest.sfxmodel`/`build_thomas.py`. Every hop below is cited `file:line`. No stock bytes
were read or reproduced in this file — only engine C# control flow and this study's own committed
text/JSON.

---

## 1. The complete path-resolution chain, hop by hop

### Hop 0 — which effect folder, and the container files inside it

`SFXData.LoadSFX(effNum, ...)` computes one folder per effect id, then reads exactly two files from
it, unconditionally, every time that effect is loaded:

```
defaultFolder = DataResources.PureDataDirectory + $"SpecialEffects/ef{(Int32)effNum:D3}/"
              = "Data/SpecialEffects/ef227/"          (for Bahamut__Full, id 227)
sfxInfo  = AssetManager.LoadString(defaultFolder + "FileList.txt", true)     // optional -- null is fine
           LoadSequenceFromFile(defaultFolder + "Sequence.seq")              // ALWAYS attempted
```
— `SFXData.cs:170-174` (`LoadSFX`), identically in `LoadEventSFX` at `SFXData.cs:206-210`.
`DataResources.PureDataDirectory = "Data/"` — `DataResources.cs:11`. `INFORMATION_FILE =
"FileList.txt"`, `SEQUENCE_FILE = "Sequence.seq"`, `PLAYER_SEQUENCE_FILE = "PlayerSequence.seq"` (the
`.seq` DSL file a `LoadSFX`/battle command actually authors against — a separate concern from this
task) — `UnifiedBattleSequencer.cs:1656-1662`.

**`ef{id:D3}` is always 3-digit zero-padded**, id = the `(Int32)SpecialEffect` enum value (matches the
probe log's own `effectId` column, PROBE.md §4).

### Hop 1 — `FileList.txt` grammar (the single-space rule)

`SFXData.LoadSFXFromInfo` (`SFXData.cs:244-279`):

```csharp
String[] sfxInfoLines = sfxInfo.Split('\n');
foreach (String linent in sfxInfoLines) {
    String line = linent.Trim();
    String[] arguments = line.Split(' ');                 // <-- splits on EVERY literal space
    if (arguments[0] == "Model" && arguments.Length >= 2) {
        String meshPath = AssetManager.UsePathWithDefaultFolder(defaultFolder, arguments[1]);
        SFXDataMesh.ModelSequence modelJSON = SFXDataMesh.ModelSequence.Load(meshPath);
        if (modelJSON == null) continue;
        if (mesh == null) mesh = new SFXDataMesh.JSON();
        (mesh as SFXDataMesh.JSON).model.Add(modelJSON);
        firstMeshFrame = 0;
    }
    if (arguments[0] == "Camera" && arguments.Length >= 2 && useCamera) { ... }   // same grammar, "Camera <path>"
}
```
(`SFXData.cs:250-272`)

Grammar consequences (all derived directly from `Split(' ')` + exact-string equality on `arguments[0]`):
- **Exactly one line, `Model <filename>`, exactly one literal ASCII space between the two tokens.**
- **A tab instead of a space breaks the whole line silently** — `"Model\tfoo.sfxmodel"` is ONE token
  (`arguments[0] == "Model\tfoo.sfxmodel"`), never equals `"Model"`, the line is ignored, `mesh` stays
  null.
- **A double space breaks the ARGUMENT, not the match** — `"Model  foo.sfxmodel"` splits to
  `["Model", "", "foo.sfxmodel"]`; `arguments[0]=="Model"` still matches, `arguments.Length>=2`
  still passes, but `arguments[1]==""` — `UsePathWithDefaultFolder(defaultFolder, "")` resolves to
  `defaultFolder` itself (a directory), `ModelSequence.Load` fails to read it as a file, returns null,
  and the `Model` line is silently dropped (`modelJSON == null → continue`).
- `arguments[1]` (only) is used — trailing tokens on the line are ignored (harmless, but don't rely on
  them).
- Trailing/leading whitespace on the whole line is `.Trim()`-forgiving; the space between `Model` and
  the filename is not.

This exactly matches `rung7-creature/FileList.txt`'s own committed header comment ("exactly one
literal space, no tab, no double space" — file line 6) — this study's own committed artifact already
encodes the rule correctly; the trace above is the proof, not a new discovery.

### Hop 2 — the filename resolves relative to the SAME `ef{id:D3}/` folder

`AssetManager.UsePathWithDefaultFolder` (`AssetManager.cs:865-870`):
```csharp
public static String UsePathWithDefaultFolder(String defaultFolder, String path) {
    if (!path.Contains("/"))
        path = Path.Combine(defaultFolder, path);
    return path;
}
```
A bare filename (no `/`) — the only form ever used in this study or by rung 7 — resolves to
`Data/SpecialEffects/ef{id:D3}/{filename}`. A path containing `/` is used **verbatim**, letting a
`.sfxmodel` live outside its own effect folder if ever wanted (not exercised anywhere in this study).

### Hop 3 — `.sfxmodel` is loaded as a `Data/`-rooted disc string, then parsed as JSON

`SFXDataMesh.ModelSequence.Load(path)` (`SFXDataMesh.cs:936-974`):
```csharp
String fileStr = AssetManager.LoadString(path);        // path = "Data/SpecialEffects/ef227/creature_manifest.sfxmodel"
JSONNode rootNode = JSONNode.Parse(fileStr);
modelSeq.defaultFolder = Path.GetDirectoryName(path);   // = "Data/SpecialEffects/ef227"
if (rootNode["FBX"] != null) LoadFBX(modelSeq, rootNode["FBX"] as JSONArray);
```
`AssetManager.LoadString(name)` → `LoadStringMultiple(name).FirstOrDefault()` (`AssetManager.cs:650-656,
487-539`). Because `name` starts with `"Data/"`, `AssetManagerUtil.IsMemoriaAssets(name)` is true
(`AssetManagerUtil.cs:417-421`, a literal `"Data/"` prefix compare) and the **whole mod-folder stack**
is walked directly on disc (Hop 6 below) — the `.sfxmodel` file itself must physically exist at
```
<modFolder>/StreamingAssets/Data/SpecialEffects/ef{id:D3}/{manifest}.sfxmodel
```
for every mod folder in priority order, first hit wins (`AssetManager.cs:497-503`).

### Hop 4 — the `FBX[].Path` token grammar (the same folder-prefix rule, applied per-entry)

`ModelSequence.LoadFBX` (`SFXDataMesh.cs:976-1030`):
```csharp
fbx.fbxPath = objectNode["Path"].Value;
if (!fbx.fbxPath.Contains("/"))
    fbx.fbxPath = modelSeq.defaultFolder + "/" + fbx.fbxPath;      // bare name -> folder-prefixed
else if (fbx.fbxPath.StartsWith("./"))
    fbx.fbxPath = modelSeq.defaultFolder + fbx.fbxPath.Substring(1);
```
So `"Path": "GEO_MON_B0_M200"` (no `/`) becomes the string
`"Data/SpecialEffects/ef227/GEO_MON_B0_M200"` before it is ever handed to `ModelFactory.CreateModel` —
**this directory prefix is then discarded** by Hop 5 below (a load-bearing, easy-to-miss step).
`Animations[].Path` entries follow the identical rule (`SFXDataMesh.cs:1017-1023`) — see Hop 8.

### Hop 5 — `ModelFactory.CreateModel` resolves the FBX by NAME, not by the folder it was found in

`ModelFactory.CreateModel(path, isBattle=false, checkTextureOnDisc=true, filtermode)` (`ModelFactory.cs:50-202`):
```csharp
String modelNameId = path;                                  // the ORIGINAL "Data/.../GEO_MON_B0_M200"
path = ModelFactory.CheckUpscale(path);                     // mangles the path -- see below
String renameModelPath = ModelFactory.GetRenameModelPath(path);
String externalPath = AssetManager.SearchAssetOnDisc(renameModelPath + ".fbx", true, false);
if (!String.IsNullOrEmpty(externalPath))
    model = ModelImporter.CreateCustomModelFromFbx(externalPath);      // <-- the loose-FBX importer
else
    model = AssetManager.Load<GameObject>(renameModelPath, false);     // archived/bundle fallback
```
(`ModelFactory.cs:50-74`)

**`CheckUpscale` (`ModelFactory.cs:244-273`) branches on whether the ORIGINAL raw path
`StartsWith("GEO_")`.** Because Hop 4 already folder-prefixed a bare name to `"Data/SpecialEffects/
ef227/GEO_MON_B0_M200"`, this string does **NOT** start with `"GEO_"` (it starts with `"Data/"`), so
`CheckUpscale` always takes its **non-GEO branch**:
```csharp
text2 = Path.GetDirectoryName(Path.GetDirectoryName(path));   // two levels up from the given path
```
For `"Data/SpecialEffects/ef227/GEO_MON_B0_M200"` this yields `text2 = "Data/SpecialEffects"` — the
effect-folder structure is discarded here, one level deeper than it looks (`ef227` itself is stripped
too). `CheckUpscale` returns `text2 + "/" + text + "/" + text` where `text` = the bare filename
(no extension in the proven case, so no double-dot artifact — see §3 below for what happens if an
extension IS present).

**`GetRenameModelPath` (`ModelFactory.cs:15-35`) then discards `CheckUpscale`'s directory entirely**:
```csharp
String text = Path.GetFileNameWithoutExtension(upscalePath);   // <-- FILENAME COMPONENT ONLY
...
Int32 geoId = ModelFactory.GetGEOID(text);                     // reverse lookup: NAME -> id
if (geoId == -1) return upscalePath;                           // unresolved name: give up on the mangled path
modelType = ModelFactory.GetModelType(upscalePath);             // derives type from the GROUP token (GEO_<GRP>_..)
return String.Format("Models/{0}/{1}/{1}", (Int32)modelType, geoId);
```
`Path.GetFileNameWithoutExtension` only looks at the LAST path segment — this is the actual mechanism
of "discards the directory entirely" (rung7 README's own phrase, independently re-derived here).
`GetGEOID` (`ModelFactory.cs:391-401`) is `FF9BattleDB.GEO.TryGetKey(modelName, out Int32 id)` — a
**reverse (name→id) lookup** into the same two-way dictionary a `3DModel <id> <name>` DictionaryPatch
directive populates (`Memoria/Configuration/DataPatchers.cs:591-614`, confirmed by grep — see §4).
`GetModelType` (`ModelFactory.cs:403-411`) parses the GROUP token out of the (still directory-prefixed)
string via `IndexOf('_')` positions — this happens to work only because the underscores that matter
all live inside the trailing `GEO_<GRP>_<FORM>_<TOKEN>` segment, regardless of what directory prefix
precedes it. `ModelType` enum (`Global/Model/ModelType.cs:3-12`): `none=0, acc=1, main=2, mon=3,
npc=4, sub=5, battle_weapon=6`.

**Net result for a registered GEO name:** `renameModelPath = "Models/{typeInt}/{geoId}/{geoId}"` —
completely independent of which `ef###/` folder the `.sfxmodel` lived in. This IS the reason rung 7's
`ef084/` folder never needed to contain the FBX at all.

### Hop 6 — `SearchAssetOnDisc` walks the mod-folder stack, high to low, on disc

`AssetManager.SearchAssetOnDisc(name, includeAssetPath=true, includeAssetExtension=false)`
(`AssetManager.cs:790-815`), called with `name = "Models/{typeInt}/{geoId}/{geoId}.fbx"`:
```csharp
String belongingBundleFilename = AssetManagerUtil.GetBelongingBundleFilename(name);   // "Models/" prefix -> non-empty
if (!String.IsNullOrEmpty(belongingBundleFilename)) {
    String streamingPath = "StreamingAssets/";
    String nameInBundle  = "Assets/Resources/" + name;      // GetResourcesBasePath() == "Assets/Resources/"
    foreach (AssetFolder modfold in FolderHighToLow)
        if (modfold.TryFindAssetInModOnDisc(nameInBundle, out fullPath, streamingPath))
            return fullPath;
}
```
(`AssetManager.cs:800-807`; `GetBelongingBundleFilename`/`CheckModuleBundleFromName`/
`GetModuleStartPath` chain: `AssetManagerUtil.cs:366-370, 372-408, 87-118` — `"Models/"` maps to
`ModuleBundle.Models`.) `GetResourcesBasePath() == "Assets/Resources/"` (`AssetManagerUtil.cs:33-36`).

`AssetFolder.TryFindAssetInModOnDisc(assetPath, out pathOnDisc, prefix)` (`AssetManager.cs:971-977`):
```csharp
pathOnDisc = this.FolderPath + assetPathPrefix + assetPath;
if (AssetList.Count == 0) return File.Exists(pathOnDisc);     // no ModFileList.txt cache -> plain File.Exists
```
**Full resolved disc path for a mod folder with no `ModFileList.txt`:**
```
<modFolder>/StreamingAssets/Assets/Resources/Models/{typeInt}/{geoId}/{geoId}.fbx
```
`FolderHighToLow` iterates mod folders in `Configuration.Mod.FolderNames` order (highest priority
first), then the base game install last (`FolderPath == ""`) — `AssetManager.cs:50-60`. **First hit
across the whole stack wins** — this IS "does the mod-folder stack apply", answered yes, for both the
model and (Hop 8) the animation clip.

This exactly reproduces rung 7's own verified deployed path: `FF9CustomMap/StreamingAssets/Assets/
Resources/Models/2/6100/6100.fbx` (`rung7-creature/README.md` line 36 — `typeInt=2` = `main`, matching
`GEO_MAIN_B0_M100`'s `MAIN` group token).

### Hop 7 — `ModelImporter.CreateCustomModelFromFbx` + `CreateCustomModel` (the bone hierarchy)

`ModelImporter.CreateCustomModelFromFbx(completePath)` (`Memoria/Assets/3DModel/ModelImporter.cs:48-140`)
parses the FBX (`FbxIO.ReadFlexible`), pulls geometry/materials/skeleton, resolves each material's
texture path via `AssetManager.UsePathWithDefaultFolder(folderPath, materials[i].TexturePath)`
(`:125` — textures resolve relative to the FBX's OWN folder, i.e. the same `Models/{typeInt}/{geoId}/`
directory), then calls the private `CreateCustomModel(baseMesh, texture, anim, extra)` (`:131`).

`CreateCustomModel` (`ModelImporter.cs:323-401`) builds the bone hierarchy:
```csharp
for (Int32 i = 0; i < boneCount; i++)
    bones[i] = new GameObject($"bone{anim.boneId[i]:D3}").transform;          // ModelImporter.cs:338
for (Int32 i = 0; i < boneCount; i++) {
    if (anim.boneParentId[i] < 0) { bones[i].parent = baseObject.transform; continue; }
    Int32 parentIndex = Array.FindIndex(anim.boneId, id => id == anim.boneParentId[i]);
    if (parentIndex < 0) throw new IndexOutOfRangeException(...);             // ModelImporter.cs:346-348
    bones[i].parent = bones[parentIndex];                                     // ModelImporter.cs:349
}
```
— **`bone{NNN:D3}` naming, by the FBX's own bone id, zero-parent bones attach to the model root, every
other bone finds its parent BY ID (not by array index)** — this is the exact convention TRANSPLANT.md
§2.2/§3.4 depends on for "same node correspondence" and "the retarget just works" (Unity `AnimationClip`
binds by hierarchy PATH, and `bone{NNN}` names are reproduced identically by the kit's own
`models/fbx_skin.py` per CLAUDE.md/`project-ff9-custom-models`). `go.AddComponent<Animation>()` is
added unconditionally at the end of `CreateCustomModelFromFbx` (`:132`) — every model loaded through
this loose-FBX path gets a real `Animation` component for free, which is what `SFXDataMesh.JSON.Begin()`
(Hop 8) and the s54 hybrid's "Animation component disabled" plan both depend on existing.

### Hop 8 — animation clip resolution for a `.sfxmodel`-loaded FBX (the DIRECT lane)

`SFXDataMesh.JSON.Begin()` (`SFXDataMesh.cs:763-800`):
```csharp
tok.unityObject = ModelFactory.CreateModel(tok.fbxPath, false, true, Configuration.Graphics.SFXSmoothTexture);   // :769
Animation component = tok.unityObject.GetComponent<Animation>();
for (Int32 i = 0; i < tok.animPath.Count; i++) {
    String anim = tok.animPath[i].Key;
    String animName = Path.GetFileNameWithoutExtension(anim);
    AnimationClip clip = component.GetClip(animName);
    if (clip == null) {
        clip = AssetManager.Load<AnimationClip>(anim, false);       // :781 -- THE clip load
        if (clip != null) component.AddClip(clip, animName);
    }
    ...
}
```
`tok.animPath[i].Key` is the literal string from the JSON `Animations[].Path`, folder-prefixed by the
SAME bare-name rule as the FBX path (`LoadFBX`, `SFXDataMesh.cs:1017-1023`) — i.e. `"Animations/6100/
1010000"` (already contains `/`, so used **verbatim, unprefixed**) or a bare name like `"clip0"` (would
folder-prefix to `Data/SpecialEffects/ef.../clip0`).

**This is a genuinely separate, simpler lane than the standard playable-model animation system**
(`AnimationFactory.AddAnimToGameObject`/`AddAnimWithAnimatioName`, which resolves by ANH-name tokens
through `FF9DBAll.AnimationDB`/`3DModelAnimation` directives — `Global/AnimationFactory.cs:54-122`).
The `.sfxmodel`'s own `Animations[].Path` is handed straight to `AssetManager.Load<AnimationClip>
(anim, false)` → `LoadMultiple<AnimationClip>(anim).FirstOrDefault()` (`AssetManager.cs:630-638,
429-484`). Tracing `"Animations/6100/1010000"` through `LoadMultiple<T>`:
- Doesn't start with `"Data/"` → skip the `IsMemoriaAssets` branch.
- `UseBundles` is true and it's not `"EmbeddedAsset/"` → skip the non-bundle branch.
- `GetBelongingBundleFilename("Animations/6100/1010000")` → `CheckModuleBundleFromName(Animations,
  ...)` matches the `"Animations/"` prefix (`AssetManagerUtil.GetModuleStartPath` → `"Animations/"`,
  `AssetManagerUtil.cs:104-106`) → non-empty (`"data5"`).
- `nameInBundle = "Assets/Resources/" + name + GetAssetExtension<AnimationClip>(name)` =
  `"Assets/Resources/Animations/6100/1010000.anim"` (`GetAssetExtension<T>` for `T=AnimationClip`
  returns `".anim"` unconditionally — `AssetManagerUtil.cs:438-439`).
- For each `modfold` in `FolderHighToLow`: `TryFindAssetInModOnDisc(nameInBundle, out fullPath,
  "StreamingAssets/")` → checks `File.Exists(modFolder + "StreamingAssets/Assets/Resources/
  Animations/6100/1010000.anim")` — **first hit across the mod-folder stack wins**
  (`AssetManager.cs:462-466`).
- On a hit: `LoadFromDisc<AnimationClip>(fullPath, nameInBundle)` → `AnimationClipReader.
  ReadAnimationClipFromDisc(fullPath)` (`AssetManager.cs:420-424`; the reader itself,
  `Memoria/Assets/3DModel/AnimationClipReader.cs:15-20`, was not opened this round — its own byte
  format is out of this task's scope, but its call site + path resolution are now pinned).
- On a miss everywhere: falls through to the non-bundle disc check (`"FF9_Data/"` prefix, no
  extension — never matches a `.anim`) then `Resources.Load<T>(name)` (the stock archive — never has a
  mint-band id's animation) → `null`.

**So the animation clip, exactly like the model, must be a loose file on disc under a mod folder's
`StreamingAssets/Assets/Resources/Animations/{id}/{clipName}.anim` — the SAME parallel convention as
`Models/{typeInt}/{id}/{id}.fbx`, and it is resolved purely by the LITERAL path string given in the
`.sfxmodel`'s own `Animations[].Path` — no `3DModelAnimation` DictionaryPatch line, no `AnimationDB`
entry, and no ANH-name convention are required for this lane.** (They ARE required for the OTHER lane
— a model played as an ordinary NPC/PC/enemy via `AnimationFactory` — but a `.sfxmodel`'s own
`Animations[]` array bypasses that machinery entirely. Confirmed independently by rung 7's own
manifest, which references `"Animations/6100/1010000"` — an id/clip-number path with **no**
`3DModelAnimation` line anywhere in that rung's build script.)

### Hop 9 — mod-folder search order, generally (the `Data/` lane vs the bundle-fallback lane)

Two distinct resolution lanes exist in `AssetManager`, both already exercised above:

1. **`Data/`-rooted strings** (`.sfxmodel` files, `FileList.txt`, `Sequence.seq`) — `IsMemoriaAssets`
   true → `LoadStringMultiple`/`LoadBytesMultiple`'s `Data/` branch (`AssetManager.cs:497-503,
   555-567`): `TryFindAssetInModOnDisc(name, ..., "StreamingAssets/")` over every `FolderHighToLow`
   entry, **yielding every match found** (not just the first) — callers take `.FirstOrDefault()`, so
   in practice only the highest-priority hit is used, but the underlying enumerable does walk the
   whole stack.
2. **Bundle-typed asset strings** (`Models/...`, `Animations/...`) — resolved through the
   `GetBelongingBundleFilename` branch (Hop 6/8 above): disc-first (`StreamingAssets/Assets/
   Resources/...`), archived-bundle-second (`modfold.IsAssetInModInBundle`), stock-`Resources.Load`
   last.

Both lanes are **mod-folder-stack aware and disc-first** — a loose file placed by `summons/deploy.py`
in the highest-priority mod folder always wins over the base game (trivially true for anything under
a mint id, since the base game has no file there at all) and over any lower-priority mod folder.

---

## 2. Reconciliation with the PROVEN rung-7 build

Everything in §1 reproduces, hop-for-hop, what `rung7-creature/` actually shipped and what the earlier
FLIGHT-era `thomas_manifest.sfxmodel` (this same study directory) independently also used:

| artifact | convention used | matches §1 hop |
|---|---|---|
| `rung7-creature/FileList.txt` | `Model creature_manifest.sfxmodel` (bare name, one space) | Hop 1/2 |
| `rung7-creature/creature_manifest.sfxmodel` | `"FBX"[0]."Path" == "GEO_MAIN_B0_M100"` (bare GEO name, no extension) | Hop 4/5 |
| `rung7-creature/README.md` §3 | "discards that directory entirely... landing on `Models/2/6100/6100.fbx`" | Hop 5 (independently re-derived here from raw source, byte-for-byte the same conclusion) |
| deployed asset (README.md line 36) | `FF9CustomMap/StreamingAssets/Assets/Resources/Models/2/6100/6100.fbx` | Hop 6 |
| `creature_manifest.sfxmodel`'s `Animations[].Path` | `"Animations/6100/1010000"` (id/clip-number path, verbatim) | Hop 8 |
| `thomas_manifest.sfxmodel` (this dir, FLIGHT era) | `"FBX"[0]."Path" == "GEO_MON_B0_M200"` — same bare-GEO-name convention | Hop 4/5 |
| `build_thomas.py` (`DONOR_EF_ID=227`, `FRESH_EF_ID=84`) | the donor's OWN folder (`ef227/`) NEVER gets a `FileList.txt`; `ef084/` (private, reused across rungs 3/7) is the ONLY folder that ever does | see §3 below |

**No contradiction found.** Every hop in §1 was independently derivable from source alone; rung 7 and
the FLIGHT manifest are both instances of the SAME resolved chain, not a different mechanism.

---

## 3. The COEXISTENCE finding — never put `FileList.txt` in the donor's own folder

This is the one genuinely load-bearing discovery this recon surfaced beyond a literal restatement of
the cited files (high confidence, static-derivation-only — flagged for a cheap confirmation cast at
the end of this section rather than as a genuine open question).

`SFXData.LoadSFX` (`SFXData.cs:156-181`):
```csharp
mesh = null;
...
if (sfxInfo != null) LoadSFXFromInfo(sfxInfo, defaultFolder);     // sets `mesh = new SFXDataMesh.JSON()` iff a Model line loaded
LoadSequenceFromFile(defaultFolder + SEQUENCE_FILE);
if (mesh != null) { loadHasEnded = true; return; }                // <-- EARLY RETURN, native path never touched
loadingQueue.Enqueue(this);                                       // <-- only reached if mesh is STILL null
```
**If ANY mod folder's `ef{donorId:D3}/FileList.txt` has a `Model` line, `mesh` becomes a
`SFXDataMesh.JSON` instance and `LoadSFX` returns before `loadingQueue.Enqueue(this)` ever runs.**
`loadingQueue` is what eventually drives the effect through `SFXDataMesh.Runtime` — the class that
actually talks to `FF9SpecialEffectPlugin.dll` (`SFXDataMesh.cs:599-609`: `Runtime.Begin()` sets
`SFXDataCamera.currentCameraEngine = SFX_PLUGIN`; `Runtime.Render()` is where `SFX.SFX_Update`/
`SFXRender.Update()`/the s52/s53 probe hooks all live, `SFXDataMesh.cs:610-682`). **Adding a
`FileList.txt` to a real summon's own donor folder (e.g. `ef227/` for Bahamut) would silently replace
the ENTIRE native cast with our own JSON mesh for that `SFXData` instance — no bones, no camera, no
geometry, no MIPS program ever runs.** That is fatal to the hybrid (TRANSPLANT.md §1/§2.1), which
depends on the native engine actually running so `*(SummonData+0x38)` has real per-frame data to read.

**This is exactly why rung 7 and the FLIGHT-era build both use a SEPARATE, PRIVATE effect id** (`ef084`
— `rung7-creature/README.md` §"Ladder position"; `build_thomas.py`'s `DONOR_EF_ID=227` /
`FRESH_EF_ID=84`, and its own committed comment "Route A: two `SFXData` entries can sit COEXISTING" —
`build_thomas.py` lines 13, 126-127) — never the donor's own folder. The two `SFXData` instances run
**concurrently**, each independently ticking through `UnifiedBattleSequencer`'s `sfxList`
(`BattleActionCode.cs` `LoadSFX`/`PlaySFX` ops each append/index into `sfxList`,
`UnifiedBattleSequencer.cs:340-379`): one `LoadSFX: SFX=Bahamut__Full` (no `ef227/FileList.txt` exists
anywhere → `mesh` stays null → native `Runtime` engine runs, unmodified) plus one `LoadSFX: SFX=84`
(reads `ef084/FileList.txt` → `mesh` becomes `SFXDataMesh.JSON` → our own FBX renders through
`ModelFactory.CreateModel`). `build_thomas.py` patches this second `LoadSFX: SFX=84` op directly into
the donor's OWN **`.seq`** (`PlayerSequence.seq`/`Sequence.seq`, a DIFFERENT file from `FileList.txt`)
— editing the `.seq` choreography is fine; the `.seq` file has no bearing on which `SFXDataMesh`
subclass gets instantiated. **Only `FileList.txt`'s presence controls that**, and it is per-effect-id,
so the rule reduces to: *`summons/deploy.py` may freely edit a donor's `.seq`/`Sequence.seq` to insert
a second `LoadSFX`/`PlaySFX` pair, but must NEVER write `FileList.txt` (or a `Model` line inside one)
into the donor's own `ef{donorId:D3}/` folder.*

**Confirmation path (cheap, not gating):** this is a pure control-flow derivation from an unconditional
`if (mesh != null) return;` — no runtime ambiguity should exist. A 1-cast confirmation would simply be:
arm the s53 probe, cast a summon whose `ef###/` folder has been (deliberately, as a negative test)
given a trivial `FileList.txt` pointing at an empty/no-op `.sfxmodel`, and confirm the `PSXCAM`/`MODEL`/
`BONES`/`ROOT` rows **stop appearing** for that cast (proving the native engine never ran) while a
`MESH` row for the JSON mesh's own (probably invisible/empty) content appears instead. Not needed
before `summons/deploy.py` is coded — the private-folder design (§4 below) sidesteps the question
entirely by construction, exactly as rung 7 and `build_thomas.py` already do.

---

## 4. What `summons/deploy.py` must emit

Given §1-3, the lowest-risk, fully-precedented design mints a NEW private effect id (reusing `ef084`
per this study's own convention, or any other id clear of the 24 creature-bearing donor ids) and
NEVER touches the real donor's `FileList.txt`. Four artifacts, four destinations:

| # | artifact | destination (relative to the mod folder root) | mechanism |
|---|---|---|---|
| 1 | **The user's retargeted FBX** (+ any texture PNGs the FBX's materials reference) | `StreamingAssets/Assets/Resources/Models/{typeInt}/{mintId}/{mintId}.fbx` (+ `{texName}.png` alongside — `ModelImporter.cs:125` resolves textures relative to the FBX's own folder) | Mint a NEW GEO id via the kit's existing `models/mint.py` (`MINT_BAND_START=6000`, `derive_mint_name`/`validate_mint_name` — reuse this machinery rather than inventing a second one). `typeInt` is whatever `type_int_of_name`/`GetModelType` derives from the minted name's GROUP token (`GEO_<GRP>_<FORM>_<TOKEN>`) — pick a `GRP` matching the creature's silhouette family (e.g. `MON` for a monster-shaped rig) so `ModelType.mon` (3) is used, matching the existing `models/mint.py` docstring's own worked examples. |
| 1b | **`DictionaryPatch.txt` line** | mod folder root, `DictionaryPatch.txt` | `3DModel {mintId} {mintName}` — registers `FF9BattleDB.GEO[mintId] = mintName` (`DataPatchers.cs:591-613`), the reverse lookup Hop 5 needs. **Needs ONE relaunch** to take effect (ini/DictionaryPatch registration, not a hot-reloadable content file — same law as every other `3DModel`/`FieldScene` line in this codebase; PROBE.md §1 step 3 and `models/mint.py`'s own comment "a NEW id needs one relaunch to register" both already state this). |
| 2 | **The dragon-clip `.anim` set** (baked motion clips decoded offline from the LOCAL `C:/gd/SCRATCH/summon-transplant/ef227.bytes`, per TRANSPLANT.md §3/§5 provenance ledger) | `StreamingAssets/Assets/Resources/Animations/{mintId}/{clipName}.anim`, one file per clip, ANY `clipName` string (no `ANH_`/`3DModelAnimation` naming constraint — see Hop 8) | Written directly by `summons/motion.py`'s decoder + a `.anim` serializer (format not yet pinned this round — `AnimationClipReader.ReadAnimationClipFromDisc`'s own byte layout is out of THIS task's scope, flag as a follow-up read). **No DictionaryPatch line needed** for this lane — referenced purely by the literal path string in artifact #3's `Animations[].Path`. |
| 3 | **The `.sfxmodel` manifest** | `StreamingAssets/Data/SpecialEffects/ef{privateId:D3}/{manifestName}.sfxmodel` (private id — reuse `084` per this study's convention, or any id with no native `ef###.bytes` content of its own) | One `FBX` entry: `"Path": "{mintName}"` (bare GEO name, NO extension — Hop 4/5; a co-located raw filename with an extension is NOT safe, see §5 below). `"Animations"`: one entry per clip, `"Path": "Animations/{mintId}/{clipName}"` (verbatim, has `/` so NOT folder-prefixed — Hop 8), optionally with a `"Speed"` key for frame-rate retiming. `"Movement"/"Rotation"/"Scaling"` anchor curves — per rung 7's own documented risk, do NOT omit these (defaults to world-origin, "wrong place, not invisible"); for the s54 hybrid specifically these become moot once per-frame bone writes override the hierarchy, but SHOULD still be set to something sane (e.g. anchored near the donor's own `SummonData+0x40` anchor) so a mis-wired hybrid degrades to "visible but static" rather than "invisible at the origin". |
| 4 | **The `FileList.txt` line** | `StreamingAssets/Data/SpecialEffects/ef{privateId:D3}/FileList.txt` | Exactly one line: `Model {manifestName}.sfxmodel` — bare filename (no `/`, resolves via Hop 2 relative to the SAME `ef{privateId:D3}/` folder), one literal space, no tab, no trailing content needed (Hop 1). **NEVER write this file (or add a `Model` line to an existing one) under the DONOR's own `ef{donorId:D3}/` folder** (§3). |

**Also required, but not a NEW artifact class** (already proven, `deploy_field.py`/`.ff9deploy.toml`
conventions apply): if the design patches the donor's own `.seq`/`Sequence.seq`/`PlayerSequence.seq`
to insert the second `LoadSFX: SFX={privateId}` / `PlaySFX: SFX={privateId}` pair (Route A,
`build_thomas.py`'s own proven mechanism) — that is a `.seq` edit, a SEPARATE file from `FileList.txt`,
and is unaffected by everything in §3.

---

## 5. Ambiguous / unproven hops flagged for a 1-cast test

1. **A co-located raw filename (no GEO-name convention) for the FBX `Path` — TRACED AS BROKEN, not
   merely ambiguous, but never actually cast-tested.** If `"Path": "thomas.fbx"` were used instead of a
   minted GEO name: Hop 4 folder-prefixes it to `"Data/SpecialEffects/ef084/thomas.fbx"`; Hop 5's
   `CheckUpscale` (non-`GEO_`-prefixed branch) computes `text2 = Path.GetDirectoryName(Path.
   GetDirectoryName(path)) = "Data/SpecialEffects"` and, because `path` has a non-empty
   `Path.GetExtension` (`".fbx"`), appends it as `text + "." + extension` = `"thomas" + "." + ".fbx"`
   = **`"thomas..fbx"`** (a double-dot artifact — `extension` already carries its own leading dot, and
   `CheckUpscale` unconditionally prepends a second `.`). `GetRenameModelPath` then strips only the
   LAST extension (`Path.GetFileNameWithoutExtension("thomas..fbx") == "thomas."`, trailing dot kept),
   `GetGEOID("thomas.")`/`GetNameFromFF9DBALL` fail to resolve any real GEO id (`geoId == -1`), so
   `GetRenameModelPath` returns the mangled `upscalePath` unchanged, and `SearchAssetOnDisc` looks for
   `"Data/SpecialEffects/thomas..fbx/thomas..fbx.fbx"` — nowhere near where the file actually sits.
   **Conclusion: do not use a bare co-located filename for the FBX `Path`; always mint a GEO name.**
   This is a static trace, not a runtime measurement — flagging it here rather than asserting it as
   fully closed, because a 1-cast negative test (deploy exactly this broken form and confirm the
   creature fails to render, distinct from any OTHER failure mode) would be the cheap way to fully
   retire it. Not gating: the GEO-name route is already proven twice over (rung 7, FLIGHT), so there is
   no reason to ever exercise the broken route in the first place.
2. **`AnimationClipReader.ReadAnimationClipFromDisc`'s own `.anim` byte format** was not opened this
   round (out of this task's stated scope — "clip lookup," not "clip serialization"). `summons/
   motion.py`'s planned `.anim` emitter (TRANSPLANT.md §3.3 ledger) needs this format read before it can
   write a byte-valid file; Hop 8 pins WHERE the file must live and how it's found, not its internal
   layout. Flag as the next read, not a cast — this is a static-source question, not a runtime one.
3. **Whether a `Runtime`-mesh `SFXData` and a `JSON`-mesh `SFXData` genuinely coexist for a
   FULL cast, not just structurally (`sfxList` is a plain `List<SFXData>`, nothing in the traced code
   prevents two entries) but VISUALLY (do both render every frame without one's `Render()`/`camera.
   worldToCameraMatrix` save-restore dance in `SFXDataMesh.cs:636,678` and `SFXDataMesh.cs:309,352`
   stomp the other's camera state mid-frame?).** `build_thomas.py`'s own README/comments describe this
   as "Route A ... proven" via the rung 6/7 lineage, so this is very likely already exercised in-game
   by this study — re-confirm by reading the rung-6/7 in-game test logs (out of this task's file set)
   rather than re-deriving from source; not re-traced here since it would duplicate prior study work
   rather than pin a NEW path.

---

## 6. Summary table — every path template in one place

| what | template | resolved via |
|---|---|---|
| Effect folder | `Data/SpecialEffects/ef{id:D3}/` | `SFXData.cs:170` |
| `FileList.txt` | `{folder}/FileList.txt`, `Model {file}` (1 space) | `SFXData.cs:171,253-257` |
| `.sfxmodel` manifest | `{folder}/{file}` (bare) or verbatim (has `/`) | `UsePathWithDefaultFolder`, `AssetManager.cs:865` |
| Minted model FBX | `Assets/Resources/Models/{typeInt}/{geoId}/{geoId}.fbx` | `GetRenameModelPath` + `SearchAssetOnDisc`, `ModelFactory.cs:15-35`, `AssetManager.cs:790-815` |
| Minted model DictionaryPatch | `3DModel {id} {name}` | `DataPatchers.cs:591-613` |
| Baked clip `.anim` (direct `.sfxmodel` lane) | `Assets/Resources/Animations/{id}/{clipName}.anim` | `AssetManager.Load<AnimationClip>`, `AssetManager.cs:429-484` bundle-fallback branch |
| Bone naming | `bone{boneId:D3}`, parent-by-id | `ModelImporter.cs:338-349` |

All six rows are mod-folder-stack-aware (`FolderHighToLow`, disc-first) and all were exercised (rows
1-4, model+DictionaryPatch) or directly analogous to an exercised path (rows 5-6, animation+bones) in
the rung-7 build. No new engine behavior is assumed anywhere in this spec.
