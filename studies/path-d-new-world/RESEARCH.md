# Path D research record -- raw agent findings (2026-07-29)

Six parallel Sonnet research passes, first-principles investigation of the Memoria WM engine
and ff9mapkit for minting a genuinely new (third) overworld world. Read PLAN.md for the
synthesized, adversarially-reviewed execution plan -- this file is the raw backing record.

## R1 -- Grid size + world-selector decoupling

```json
{
  "findings": [
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMConstants.cs:15-21",
      "quote": "public const Int32 WorldBlockFigureX = 24;\n    public const Int32 WorldBlockFigureZ = 20;\n    public const Int32 WorldCellFigureX = 48;\n    public const Int32 WorldCellFigureZ = 40;",
      "claim": "Compile-time consts. VERIFIED via whole-tree grep: these four names have ZERO usages anywhere in Assembly-CSharp outside their own declaration. They are dead/decorative -- nothing reads them.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:1673-1690",
      "quote": "public static WMBlock[,] BuildBlockArray(Transform worldDisc)\n    {\n        WMBlock[,] array = new WMBlock[24, 20];\n        for (Int32 i = 0; i < 24; i++)\n        {\n            for (Int32 j = 0; j < 20; j++)",
      "claim": "The live block-array allocation uses raw literals 24/20, NOT WMConstants.WorldBlockFigureX/Z. This is the actual grid-size source of truth at runtime, and it is disconnected from the named constants.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorldPrefabMaker.cs:291-296",
      "quote": "public static WMBlockPrefab[,] BuildBlockArray(Transform worldDisc)\n    {\n        WMBlockPrefab[,] array = new WMBlockPrefab[24, 20];\n        for (Int32 i = 0; i < 24; i++)\n            for (Int32 j = 0; j < 20; j++)",
      "claim": "The editor-time twin of BuildBlockArray independently re-hardcodes 24/20 again (also not via WMConstants). Same fact, third independent copy after the two WMWorld.cs list items above.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:450-457, 1178-1197, 1211-1213, 1635-1657",
      "quote": "for (Int32 i = 0; i < 20; i++) { for (Int32 j = 0; j < 24; j++) { ... } }  (OnInitialize, LoadBlocks, CheckIfLoadingBlocksIsFinished, ResetBlockForms, SetBlockForms)",
      "claim": "Five more independent 24/20 (or 20/24) loop-bound literal sites across WMWorld.cs, none referencing WMConstants. CheckIfLoadingBlocksIsFinished additionally hardcodes the product: `if (this.ActiveBlockCount == 480)` at line 1222.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:294-311",
      "quote": "Int32 x = (Int32)(position.x / 64f);\n        Int32 z = (Int32)(Mathf.Abs(position.z) / 64f);\n        if (x >= 24) return null;\n        if (z >= 20) return null;",
      "claim": "GetAbsoluteBlock hardcodes the 24/20 bound check with raw literals, while the sibling function GetAbsolutePositionOf (lines 237-238, same file) does the equivalent bound using `this.Blocks.GetLength(0)`/`GetLength(1)` -- i.e. two functions doing the identical job, one hardcoded, one genuinely runtime-computed from the live array shape. Inconsistent, not systematically parameterized.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:1510-1584 and 1294-1454",
      "quote": "ShiftBlocks: `for (Int32 i = 0; i < 23; i++)` (Left) / `for (Int32 k = 23; k > 0; k--)` (Right) / `for (Int32 m = 0; m < 19; m++)` (Up) / `for (Int32 num = 19; num > 0; num--)` (Down), each paired with a second loop bounded 24 or 20, plus repeated `64f`/`1536f`/`1280f` wrap-distance literals. ShiftRightAllBlocks/ShiftLeftAllBlocks/ShiftDownAllBlocks/ShiftUpAllBlocks (4 separate functions) each re-loop `i<20` or `i<24` and independently re-hardcode the same 64f/1536f/1280f wrap arithmetic for the actor position AND for both kWorldPackEffectThunder1s/2s effect arrays.",
      "claim": "The torus-wrap block-shift machinery is entirely raw-literal, duplicated roughly 15 times across 5 functions (ShiftBlocks + 4 ShiftXAllBlocks variants). None of it references WMConstants.BlockDistance/WorldBlockFigureX/Z. This is the opposite of centralized -- it is the most copy-pasted hardcode in the file.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:362-373",
      "quote": "private void CaculateBoundsOfTranslatingObjects()\n    {\n        this.Width = 1536f;\n        this.Height = 1280f;\n        this.centerOfMesh.x = 800f;\n        this.centerOfMesh.z = -672f;\n        this.wrapWorldLeftBound = this.centerOfMesh.x - 32f; ... (+32/-32 for all 4 bounds)",
      "claim": "The torus wrap-seam center + bounds are raw literals, not computed from WMConstants. But they ARE mathematically consistent with a 24x20 grid at BlockDistance=64: 1536=24*64, 1280=20*64, 800=(24/2)*64+32, 672=(20/2)*64+32 (a half-block offset from true center). The code hardcodes the RESULT of that arithmetic rather than deriving it from WorldBlockFigureX/Z at runtime.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:1659-1671",
      "quote": "public void SetDisc(Int32 disc)\n    {\n        if (disc != 1 && disc != 4)\n        {\n            global::Debug.LogError(\"Only disc1 and dic4 are available.\");\n        }\n        if (disc != this.currentDisc) { ff9.w_frameDisc = (Byte)disc; this.currentDisc = disc; SceneDirector.Replace(\"WorldMapDebug\", ...); }",
      "claim": "The world/disc SELECTOR is explicitly gated to exactly {1,4} by a literal check. Note the guard is LOG-ONLY (LogError, not a return/throw) -- a disc value of e.g. 5 would still be accepted into currentDisc/w_frameDisc and proceed, it just logs a warning. The real block on a 3rd value is downstream (asset resolution), not this check.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Memoria\\World\\WorldConfiguration.cs:234-241",
      "quote": "public static Byte GetDisc()\n        {\n            if (_customDiscModifier.HasCondition)\n                return (Byte)(_customDiscModifier.IsActive ? 4 : 1);\n            return (Byte)(ff9.w_frameScenePtr >= 11090 ? 4 : 1);\n        }",
      "claim": "This is the true source of the disc value consumed by WMWorld (WMWorld.cs:136 `ff9.w_frameDisc = WorldConfiguration.GetDisc();`). It is a strictly BINARY ternary hardcoded to {1,4} in source. It IS partly data-driven: `_customDiscModifier` is a ConditionalModifier settable via a WorldEnvironmentPatch NCalc condition (WorldConfiguration.cs:372, `LoadWorldEnvironmentSimpleToken`) -- so the CONDITION for flipping 1->4 is already mod-authorable, but the two possible OUTPUT bytes are still hardcoded to 1 and 4 in source; a 3rd output value requires a source edit + DLL rebuild.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\UI\\UIKey\\Ff9mkDebugMenu.cs:1826-1836",
      "quote": "[ff9mapkit] REAL disc switch ... There is NO independent disc flag: disc 4 IS ScenarioCounter >= 11090. ScenarioCounter = gEventGlobal[0-1] (EventState.cs:16), and WMWorld RE-DERIVES the disc from it via GetDisc() on EVERY world load (WorldConfiguration.cs:240 `SC>=11090?4:1`, WMWorld.cs:136).",
      "claim": "This is the project's OWN prior verified finding (a comment in shipped code, not a memory-file claim), and I confirmed it against WorldConfiguration.cs:240 and WMWorld.cs:136 directly. It answers investigation point 2 precisely: 'disc' the story-progression flag and 'disc' the literal mesh-folder selector are the SAME byte (ff9.w_frameDisc / WMWorld.currentDisc), not two variables that happen to correlate -- there is only one variable serving both roles.",
      "kind": "runtime_computed"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:511-514, 856",
      "quote": "String name = String.Format(\"WorldMap/Prefabs/WorldDisc{0}/r{1}/{2}\", disc, initialY, arg);\n            GameObject blockObjectPrefab = AssetManager.Load<GameObject>(name, false);",
      "claim": "The per-block PREFAB lookup path is built by generic string formatting on the `disc` int parameter -- it will format 'WorldDisc5/...' just as readily as 'WorldDisc1/...' with zero code change. Whether that resolves to a real asset for disc=5 is an asset-existence question, not a code hardcode (see unknowns).",
      "kind": "runtime_computed"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:786-799, 834",
      "quote": "Mesh ff9Override = Memoria.World.WorldMeshOverride.TryLoad(String.Format(\"WorldMap/Disc{0}/0_1/r{1}/Block[{2}][{3}] {4}\", this.currentDisc, block.InitialY, block.InitialX, block.InitialY, transform.name));",
      "claim": "DWIX's own s34 loose-mesh-override hook (Memoria\\World\\WorldMeshOverride.cs) is keyed by the live `currentDisc` int with no hardcoded disc value -- it already generalizes to any disc N for OVERRIDING a mesh on a block that exists. Confirmed by reading WorldMeshOverride.cs (223 lines) in full and cross-checking against memoria-patches\\s34-worldmap-mesh-override.patch, which matches the live source exactly.",
      "kind": "data_driven"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorldPrefabMaker.cs:7-178, 168-170",
      "quote": "public static Transform LoadModelAsset(Int32 disc, Boolean fillEmptyBlock) { ... Mesh mesh = Resources.Load(assetPath) as Mesh; ... wmblockPrefab.IsSea = isSea; wmblockPrefab.HasSpecialObject = hasSpecialObject; wmblockPrefab.IsSwitchable = isSwitchable; ...}",
      "claim": "VERIFIED by whole-tree grep: `.IsSea =`, `.HasSpecialObject =`, `.IsSwitchable =` are assigned ONLY inside this one function in the entire Assembly-CSharp tree -- and a second grep found ZERO call sites for `WMWorldPrefabMaker.LoadModelAsset` anywhere in Assembly-CSharp. This is the ONLY place that decides which of the 480 cells are sea/land/special per disc, it reads from `Resources.Load` (a baked Unity asset path, not a mod-folder loose file), and nothing in the runtime DLL appears to call it -- strong evidence this is editor-only asset-baking tooling whose caller lives outside this decompiled assembly (or is vestigial).",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMWorld\\WMWorld.cs:2033, 2069-2074, 139-153",
      "quote": "public Transform WorldDisc;\" ... \"// DWIX Path D: ... WMWorld is a MonoBehaviour baked into the pre-built WorldDisc prefab; adding a SERIALIZED (public) field shifts its serialization layout, so the baked component deserializes corrupt...\" and Initialize(): `if (!this.WorldDisc) { Debug.LogError(\"WorldDisc can't be null. Please set it in the scene.\"); }`",
      "claim": "`WorldDisc` is never assigned anywhere in C# source (verified by grep across all of Assembly-CSharp) -- it is a SERIALIZED Unity scene/prefab reference, and per the project's own comment, WMWorld itself is baked as a component ON that same pre-built prefab. There is exactly ONE structural WorldDisc skeleton (480 WMBlock GameObjects with fixed InitialX/InitialY/IsSea/etc) shared by BOTH disc 1 and disc 4 at runtime; only the per-block VISUAL/RENDER content is swapped by `disc` via LoadBlock's prefab lookup, not the structural skeleton itself.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMBlock\\WMBlock.cs (whole file, 343 lines)",
      "quote": "(no 'disc' field anywhere in the file)",
      "claim": "Read the entire file: WMBlock has InitialX/InitialY/Number/CurrentX/CurrentY/IsSea/etc but carries NO disc identity of its own. `disc` only ever appears as a parameter passed into WMWorld.LoadBlock(Int32 disc, WMBlock block), always called with `this.currentDisc` -- the ONE global field on the WMWorld singleton (WMWorld.cs:2090, `private Int32 currentDisc = -1;`). Answers investigation point 5 directly: which disc's assets to load is decided ONCE GLOBALLY for the whole active WMWorld instance, never per-block.",
      "kind": "runtime_computed"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\WM\\WMBee\\WMBeeMenu.cs:29, 127-153",
      "quote": "if (ff9.w_frameDisc == 1) ... if (GUILayout.Button(\"Disc \" + ff9.w_frameDisc, ...)) { if (ff9.w_frameDisc == 1) ...; if (ff9.w_frameDisc == 4) ...; } if (ff9.w_frameDisc == 1 && GUILayout.Button(\"Object Form\"...)) ... if (ff9.w_frameDisc == 1 && GUILayout.Button(\"Jump To\", ...))",
      "claim": "A debug-only overworld authoring GUI hardcodes literal `== 1` / `== 4` checks in 5 places to decide which controls to show/what the disc-toggle button does next. A 3rd disc value would make several of these controls simply never activate until updated.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "C:\\gd\\FFIX\\Memoria\\Assembly-CSharp\\Global\\ff9\\ff9.cs:9358, 2429-2435, 4711-4714, 7102-7108, 9989",
      "quote": "public const Int32 kw_blockDistance = 16384;\" ... \"diff.x -= 1536f; ... diff.z -= 1280f;\" (wrap-diff) ... \"wx < 0f || wx >= 1536f || wz > 0f || wz <= -1280f\" (bounds test) ... \"sx = (x - num) / (1536f - num); sy = 1f - (-z - num2) / (1280f - num2);\" (screen projection) ... \"// [ff9mapkit] Known-safe overworld fallback spawn (Unity units, well inside the 24x20 / 1536x1280 grid).",
      "claim": "The 1536/1280/16384 grid-size facts are ALSO independently hardcoded, repeatedly, in the main global ff9.cs file (not just WMWorld.cs) -- in wrap-distance math, a bounds/quad test, and a screen-space sx/sy projection formula. `kw_blockDistance` is a THIRD independent named constant for the same 16384 value that WMConstants.OriginalBlockDistance already names (neither constant is referenced by the actual math, which uses raw literals). Even the project's own DWIX code comment at line 9989 re-asserts '24x20 / 1536x1280' as an assumption baked into a spawn-safety fallback.",
      "kind": "hardcoded_constant"
    },
    {
      "file_line": "prior memory claim vs verified source",
      "quote": "project memory (studies/ or similar) claimed: 'the 24x20=480 literals are DECOUPLED/repeated (WMConstants already names them WorldBlockFigureX/Z) so the grid refactor is mechanical'",
      "claim": "VERIFIED AND FOUND MISLEADING. 'Repeated' is correct (confirmed ~20+ independent raw-literal sites across WMWorld.cs, WMWorldPrefabMaker.cs, and ff9.cs). 'WMConstants already names them' is technically true but functionally irrelevant: WorldBlockFigureX/Z have ZERO readers anywhere -- they are not wired to any of the repeated literals, so nothing is actually 'decoupled' via those constants; a hypothetical developer bumping WMConstants.WorldBlockFigureX would change NOTHING at runtime. The practical conclusion ('mechanical' for a same-size 24x20 third world) happens to be correct, but for the opposite reason stated: it's mechanical because the literals ALREADY encode the right numbers for any 24x20 grid regardless of disc, not because of any real parameterization via WMConstants. For a DIFFERENT-size grid, 'mechanical' would be false -- roughly 20 independent literal sites across 3 files would need individual edits, several of them non-obviously derived (e.g. centerOfMesh 800/-672).",
      "kind": "hardcoded_constant"
    }
  ],
  "same_size_verdict": "If the new (third) world stays EXACTLY 24x20 blocks (480 cells, BlockDistance=64, Width=1536/Height=1280), the wrap/grid MATH in Memoria needs ZERO engine changes. Reasoning, grounded in source read this session:\n\n1. Every grid-shaped literal I found (WMWorld.cs: BuildBlockArray's `new WMBlock[24,20]`, OnInitialize's/LoadBlocks'/CheckIfLoadingBlocksIsFinished's/ResetBlockForms's/SetBlockForms's `i<24`/`j<20` loops, CheckIfLoadingBlocksIsFinished's `==480`, GetAbsoluteBlock's `x>=24`/`z>=20`, ShiftBlocks' and the four ShiftXAllBlocks' `23`/`19`/`24`/`20`/`64f`/`1536f`/`1280f` torus-wrap arithmetic, CaculateBoundsOfTranslatingObjects' `Width=1536f`/`Height=1280f`/`centerOfMesh=(800,0,-672)`/`±32f` wrap bounds, plus ff9.cs's independent `1536f`/`1280f`/`16384` copies in the wrap-diff, bounds-test and screen-projection functions) is NOT disc-specific. None of it branches on `currentDisc`/`disc`. It operates purely on `this.Blocks`/`this.InitialBlocks`, a single 24x20 array shape that disc 1 and disc 4 ALREADY share today without any wrap-math edit between them when the game flips `w_frameDisc`. A third same-size world reuses that identical array shape and identical wrap constants -- there is nothing in this layer that is \"world 1\" or \"world 4\" specific to begin with, so there is nothing to make \"world 3\" specific either.\n\n2. The only place grid-SIZE literally gates anything by value is `WMWorld.SetDisc`'s `if (disc != 1 && disc != 4) Debug.LogError(...)` (WMWorld.cs:1659-1671) and `WorldConfiguration.GetDisc()`'s binary ternary (`?4:1`, WorldConfiguration.cs:234-241) -- and both of those are about the DISC/WORLD-SELECTOR VALUE, not the grid dimensions. They would need a source edit (trivial: widen the ternary/switch to a third value) plus a Memoria DLL rebuild, but that is world-selector work, not grid-size/wrap-math work.\n\n3. The genuine open risk for a same-size third world is NOT the wrap math at all -- it is that `WMWorld.WorldDisc` (the structural 480-block skeleton: InitialX/InitialY/IsSea/HasSpecialObject/IsSwitchable per cell) is, per the project's own code comment (WMWorld.cs:2069-2074), \"baked into the pre-built WorldDisc prefab\" and never assigned anywhere in C# -- i.e. it is ONE serialized Unity asset shared by disc 1 and disc 4 (only the per-block CONTENT/mesh is swapped per disc via LoadBlock's `\"WorldMap/Prefabs/WorldDisc{disc}/...\"` lookup, confirmed generic/string-formatted and disc-agnostic). A third world that wants its OWN cell-type layout (which cells are sea vs land) rather than reusing disc-1/4's exact layout needs either a new baked structural prefab (WMWorldPrefabMaker's pipeline, whose caller I could not find anywhere in Assembly-CSharp -- likely Editor-only) or a NEW engine patch that constructs the 480 WMBlock GameObjects procedurally at runtime from kit-authored data instead of reading the baked prefab. That is real engine-code work -- but it is CONTENT/SELECTOR-LAYER work, not wrap/grid-math work, and it exists precisely BECAUSE the size stays 24x20 (reusing the existing skeleton) is the cheap path; going to a different size would ALSO require touching that same content layer PLUS the ~20 hardcoded-literal grid-math sites enumerated above.\n\nBottom line: same-size (24x20) -> wrap/grid math untouched; the real engineering is entirely in (a) extending GetDisc()/SetDisc() past their hardcoded {1,4}, and (b) sourcing a third world's per-cell structural data (IsSea/mesh content) without the existing baked-prefab dependency -- both are world-SELECTOR/content problems, not grid-math problems.",
  "unknowns": [
    "Whether WMWorldPrefabMaker.LoadModelAsset (the only place that ever assigns WMBlock.IsSea/HasSpecialObject/IsSwitchable) is invoked by any reachable code path at all -- grep found zero call sites anywhere in the decompiled Assembly-CSharp tree. Is it genuinely dead/vestigial in the shipped runtime DLL, called only from Unity-Editor-only tooling not included in this assembly, or invoked via some reflection/build-script path outside Assembly-CSharp entirely? This determines whether building a THIRD structural WorldDisc skeleton is even possible without direct Unity Editor access.",
    "Whether AssetManager.Load<GameObject>(\"WorldMap/Prefabs/WorldDisc{N}/...\") can resolve a brand-new asset name (N=5, etc.) if the modder supplies a matching Unity-format asset, or whether \"WorldMap/Prefabs/WorldDiscN\" entries are sealed inside a single AssetBundle baked at base-game build time that cannot be extended without Unity Editor access and an AssetBundle repack. I located AssetManager.cs/AssetManagerUtil.cs but did not read their resolution logic in full this session.",
    "Whether WMWorld.WorldDisc (the baked, never-C#-assigned Transform field) could safely be REPLACED at runtime by an engine patch (e.g. in Initialize()/OnInitialize()) with a kit-constructed Transform hierarchy of 480 fresh WMBlock GameObjects, without corrupting the MonoBehaviour's own Unity serialization layout -- the project's own s34 comments show this exact class of corruption ('different serialization layout ... expected N bytes' -> blackscreen) has already been hit once for OTHER fields on this same baked component, so the discipline required (NonSerialized attributes etc.) is proven necessary but reassigning WorldDisc itself specifically is unverified.",
    "Whether WMBlock.IsSea (read live every LoadBlock call at WMWorld.cs:495) could be intercepted/overridden by a new loose-data-file mechanism analogous to WorldMeshOverride, decoupling a third world's cell-type layout from the one baked skeleton's layout -- technically plausible from the read-site's structure but not attempted or evidenced anywhere in the current s34-lineage patches.",
    "What actually happens today if WorldConfiguration.GetDisc()/WMWorld.SetDisc() produce/receive a disc value outside {1,4} (e.g. 5) -- does AssetManager.Load return null causing an NRE in LoadBlock's `blockObjectPrefab.GetComponent<WMBlockPrefab>()` (WMWorld.cs:552), or does it fail more gracefully? Not verifiable from source alone; needs a cheap in-game debug-menu probe (temporarily call WMWorld.Instance.SetDisc(5) or set ff9.w_frameDisc=5 and reload) before committing engineering effort to the world-selector extension.",
    "Whether the Python kit's ff9mapkit/ff9mapkit/world/ package (25 files: extract.py, worldpack.py, discmirror.py, mesh.py, etc.) has its own independent 24x20/480 assumptions that would need parallel updates -- I only spot-checked extract.py and worldpack.py for obvious grid-size constants and found none directly relevant, but did not exhaustively read all 25 files, so this is not fully verified either way.",
    "Whether WorldConfiguration's `_customDiscModifier` (already moddable via a WorldEnvironmentPatch NCalc condition) could be extended to select a genuine 3rd byte value without a DLL rebuild if GetDisc()'s ternary were the ONLY hardcoded gate -- currently GetDisc() caps the return to exactly {1,4} regardless of the modifier's condition, so even the 'data-driven' half of disc-selection is capped by a hardcoded ternary today; unclear if there's any other undiscovered NCalc/CSV path that bypasses GetDisc() entirely for some other world-map consumer."
  ]
}
```

## R2 -- The WorldDisc prefab/scene: baked Unity asset or code-constructed?

```json
{
  "verdict": "uncertain_mixed",
  "evidence": [
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:2033",
      "quote": "public Transform WorldDisc;",
      "why_it_matters": "This is a plain (serialized, not [NonSerialized]) public field -- the single reference WMWorld uses for the whole block grid. No attribute marks it as runtime-only."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:139-143",
      "quote": "if (!this.WorldDisc) { global::Debug.LogError(\"WorldDisc can't be null. Please set it in the scene.\"); this.LoadState = WMWorldLoadState.Initializing; }",
      "why_it_matters": "Initialize() treats WorldDisc as a precondition that must ALREADY be wired -- the error message literally says 'set it in the scene,' i.e. via the Unity Inspector/scene serialization, not via code."
    },
    {
      "file_line": "whole-tree grep, no hits",
      "quote": "grep -rn \"WorldDisc\\s*=\" Assembly-CSharp --include=*.cs   (returns nothing outside the field declaration)",
      "why_it_matters": "WorldDisc is NEVER assigned by any C# code anywhere in the runtime assembly. Its only source is Unity's own deserialization of a baked scene/prefab -- there is categorically no live constructor for it today."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:2069-2074",
      "quote": "// DWIX Path D: plain-land donor prefab (host) for reclaimed ocean cells (s34). [NonSerialized] is CRITICAL -- WMWorld is a MonoBehaviour baked into the pre-built WorldDisc prefab; adding a SERIALIZED (public) field shifts its serialization layout, so the baked component deserializes corrupt (\"different serialization layout ... expected N bytes\") ... -> overworld blackscreen.",
      "why_it_matters": "This is the project's own, already field-tested finding (not my speculation): WMWorld itself is a MonoBehaviour baked directly INTO the WorldDisc prefab with a fixed binary serialization layout. They hit a real blackscreen bug from disturbing it. This is the strongest single piece of evidence that WorldDisc is a genuinely baked Unity asset, not a code container."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorldPrefabMaker.cs:7-178 (LoadModelAsset)",
      "quote": "String name = \"WorldDisc\" + disc; Transform transform = new GameObject(name).transform; ... WMBlockPrefab wmblockPrefab = transform2.gameObject.AddComponent<WMBlockPrefab>(); ... Mesh mesh = Resources.Load(assetPath) as Mesh; ...",
      "why_it_matters": "A COMPLETE runtime-construction algorithm for a 24x20 block grid exists in source -- proving the shape is codeable in principle. But it builds WMBlockPrefab-tagged objects (the per-block VISUAL TEMPLATE tier), not the WMBlock-tagged objects WMWorld.BuildBlockArray actually reads off WorldDisc (WMWorld.cs:1673-1690) -- it's the wrong tier for the container role, and see the next two rows for why it's also dead/non-functional as-is."
    },
    {
      "file_line": "whole-tree grep, no hits",
      "quote": "grep -rn \"WMWorldPrefabMaker\\.\" Assembly-CSharp --include=*.cs   (no caller of LoadModelAsset outside WMWorldPrefabMaker.cs itself)",
      "why_it_matters": "LoadModelAsset has ZERO runtime callers in the shipped assembly. It is dead/vestigial editor-time tooling, not a live code path."
    },
    {
      "file_line": "whole-tree grep, no hits",
      "quote": "grep -rn \"WMWorldPrefabMaker\\.(TerrainMaterial|ObjectMaterial|Sea1Material) =\" Assembly-CSharp --include=*.cs   (no assignment anywhere)",
      "why_it_matters": "Even if LoadModelAsset were called today, its required static Material fields are never populated by any code in this assembly -- everything it built would render with null materials. Further confirms it's a stripped editor-only tool, not revivable as-is."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:511-514",
      "quote": "String name = String.Format(\"WorldMap/Prefabs/WorldDisc{0}/r{1}/{2}\", disc, initialY, arg); GameObject blockObjectPrefab = AssetManager.Load<GameObject>(name, false); this.LoadBlock(blockObjectPrefab, block);",
      "why_it_matters": "The REAL, live per-block streaming path loads a GameObject-type prefab keyed by disc number string from AssetManager -- this is the actual runtime mechanism, and it depends on that named asset already existing (Resources/AssetBundle)."
    },
    {
      "file_line": "Assembly-CSharp/Global/Asset/AssetManager.cs:372-383,425-426",
      "quote": "* GameObject (Usually split into many pieces ; LoadAsync is used in WMWorld) - Can't be read from disc currently ... Log.Error(\"[AssetManager] Trying to load from disc the asset \" + name + \" of type \" + typeof(T).ToString() + \", which is not currently possible\"); return default(T);",
      "why_it_matters": "AssetManager.LoadFromDisc<T> -- the ONE function that lets a mod's loose files override an asset -- has explicitly NO case for GameObject. A per-block visual prefab can only ever come from Resources.Load (baked into p0dataN.bin) or a compiled .assetBundle; there is no loose-file path for it at all, unlike Mesh (see WorldMeshOverride below)."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:550-552",
      "quote": "private void LoadBlock(GameObject blockObjectPrefab, WMBlock block) { WMBlockPrefab prefab = blockObjectPrefab.GetComponent<WMBlockPrefab>();",
      "why_it_matters": "No null guard. If AssetManager.Load returned null (a disc id with no baked prefab), this throws a NullReferenceException immediately -- a hard crash, not a silent/graceful fallback."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:1659-1664",
      "quote": "public void SetDisc(Int32 disc) { if (disc != 1 && disc != 4) { global::Debug.LogError(\"Only disc1 and dic4 are available.\"); } if (disc != this.currentDisc) { ... SceneDirector.Replace(\"WorldMapDebug\", SceneTransition.FadeOutToBlack_FadeIn, true); } }",
      "why_it_matters": "A HARDCODED CONSTANT gate limiting the debug-menu disc switch to exactly {1,4} (it logs but doesn't actually block -- the crash would occur downstream in the per-block asset loads). Confirms only two disc identities are recognized anywhere I found in this pass."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:1161-1163",
      "quote": "String name = String.Format(\"WorldMap/Prefabs/WorldDisc{0}/r{1}/{2}\", 1, 0, arg); this.SeaBlockPrefab = AssetManager.Load<GameObject>(name, false);",
      "why_it_matters": "Verifies the 'block[12][0]f' empty-sea fallback from project docs: it's hardcoded to WorldDisc1 (literal 1, not the active disc) so it's shared/global across discs -- but it is STILL a baked prefab load, not a code construction."
    },
    {
      "file_line": "whole-tree grep, no hits",
      "quote": "grep -rn \"\\.IsSea\\s*=|\\.HasSpecialObject\\s*=|\\.IsSwitchable\\s*=\" Assembly-CSharp --include=*.cs (only hits are inside the dead WMWorldPrefabMaker.cs)",
      "why_it_matters": "WMBlock's per-cell state flags (IsSea etc., on the 480 children under WorldDisc) are never assigned by any LIVE code path -- they exist purely as deserialized baked values today. A new disc's grid would have zero state data unless a new patch supplies it."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:775-821 (RegisterBlockComponent)",
      "quote": "Transform copy = UnityEngine.Object.Instantiate<Transform>(transform); ... Mesh ff9Override = Memoria.World.WorldMeshOverride.TryLoad(...); if (ff9Override != null) { mesh = ff9Override; MeshFilter mf = copy.GetComponent<MeshFilter>(); if (mf != null) mf.sharedMesh = ff9Override; ... }",
      "why_it_matters": "This is the actual s34 hook. It ALWAYS starts by cloning an already-loaded, already-baked template Transform (with working MeshFilter/MeshRenderer/material) and only swaps .sharedMesh -- it never fabricates a renderer/material from nothing. It structurally requires a real donor prefab from an existing (baked) disc."
    },
    {
      "file_line": "Memoria/World/WorldMeshOverride.cs:10-23,158-221",
      "quote": "// Load a WORLD-MAP block terrain mesh from a LOOSE \".ff9mesh\" file ... AssetManager.LoadFromDisc<Mesh/GameObject> is unsupported -- there is no loose-mesh hook, only this one. ... private static Mesh ReadMesh(...) { ... Byte[] magic = r.ReadBytes(4); if (... magic != 'F9WM') throw ...",
      "why_it_matters": "Proves loose, zero-baked-asset MESH geometry is fully achievable (a hand-rolled binary format, parsed into a fresh Mesh object, no Unity asset serialization involved) -- this is the concrete precedent the 'pure code+data' hope for a third world rests on, but it only covers Mesh, not GameObject/prefab/container data."
    },
    {
      "file_line": "Memoria/World/WorldMeshOverride.cs:14 vs WMWorld.cs diff comment at s34 patch line ~79-81",
      "quote": "File header: \"Hooked from WMWorldPrefabMaker.LoadMesh, right after Resources.Load(assetPath) as Mesh.\"  vs.  in-diff comment: \"the RUNTIME block-stream path (the editor-only WMWorldPrefabMaker.LoadMesh never runs)\"",
      "why_it_matters": "The file's own top-of-file doc comment is factually stale/wrong about its own hook point (says WMWorldPrefabMaker.LoadMesh); the actual hook, confirmed by reading the diff and WMWorld.cs directly, is WMWorld.RegisterBlockComponent. This is a live example of exactly the 'don't trust a doc summary, verify against source' trap the task warned about -- caught inside the project's own file."
    },
    {
      "file_line": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:66,100,106; Global/WM/WMConstants.cs:75",
      "quote": "GameObject gameObject = GameObject.Find(\"WorldMapRoot\"); ... this.MainCamera = GameObject.Find(\"WorldCamera\").GetComponent<Camera>();  /  public const String WorldCameraName = \"WorldCamera\";",
      "why_it_matters": "The camera/effect-root scene skeleton is found by fixed, disc-agnostic name constants used identically for both discs -- suggesting (not proven) that this part of the scene is shared/generic rather than baked per-disc, which would narrow what a new disc actually needs to supply."
    }
  ],
  "break_points": [
    "WMWorld.WorldDisc (WMWorld.cs:2033) is populated exclusively by Unity scene/prefab deserialization; grep confirms zero runtime assignment anywhere in Assembly-CSharp. There is no live 'load or build a WorldDisc for disc N' constructor to redirect for a new disc id.",
    "Per-cell WMBlock state (IsSea, HasSpecialObject, IsSwitchable, InitialX/Y, Number) is likewise never assigned by any live code path -- only ever deserialized. A brand-new disc's 480 cells have zero state data unless a new patch invents a way to populate WMBlock components from loose data (e.g. a CSV) at Awake/Initialize time.",
    "AssetManager.LoadFromDisc<T> (AssetManager.cs:372-427) has no GameObject case -- the per-block VISUAL prefab (WorldMap/Prefabs/WorldDiscN/rY/Block[X][Y]) can only come from Resources (baked) or an .assetBundle. For a disc id outside {1,4}, AssetManager.Load<GameObject> returns null and WMWorld.cs:552 immediately NREs on blockObjectPrefab.GetComponent<WMBlockPrefab>() -- a hard crash, not a silent no-op.",
    "RegisterBlockComponent (the proven, shipping s34 hook) only ever clones-and-swaps-mesh on an ALREADY-LOADED baked template transform; it supplies no renderer/material from scratch. It cannot originate a cell's visuals ex nihilo -- which is why the existing 'DWIX Path D (new continent)' sea-reclaim code (WMWorld.cs:495-537) explicitly borrows donor prefabs from the real, already-baked disc1/disc4 block library rather than manufacturing new ones.",
    "The one function that DOES build an entire disc's grid from loose Resources.Load calls (WMWorldPrefabMaker.LoadModelAsset) has zero callers and its required static Material fields are never assigned anywhere in the runtime assembly -- it is dead editor-only code, not a usable path without material engineering work first.",
    "SetDisc (WMWorld.cs:1659-1664) hardcodes disc validity to {1,4}, and switching disc triggers a full scene reload (SceneDirector.Replace(\"WorldMapDebug\", ...)) rather than an in-place C# swap -- consistent with disc-specific content being selected at scene-load time, not synthesized by code."
  ],
  "unknowns": [
    "Whether the 'WorldMap' Unity scene contains ONE WorldDisc grid-container shared/reused across both discs (implying disc1 and disc4 share identical IsSea topology) or TWO separately-baked WorldDisc hierarchies with a reassignment mechanism not found anywhere in Assembly-CSharp -- unresolvable from C# source; requires opening the actual scene/AssetBundle (e.g. via UnityPy or the Unity Editor).",
    "Whether 'WorldMapRoot' and 'WorldCamera' (found via GameObject.Find, disc-agnostic names) are baked into the SAME prefab/scene asset as WorldDisc, or are a separate generic scene skeleton a new WorldDisc-equivalent could attach beneath with zero new baked content -- not verifiable from source alone; this is the single highest-value cheap probe to run before committing engineering effort.",
    "Whether the Terrain/Sea/Object materials that baked block prefabs already carry (generically named in WMWorldPrefabMaker.cs, e.g. TerrainMaterial, Sea1Material -- not 'Disc1TerrainMaterial') are themselves disc-agnostic, already-loadable-by-name Resources assets that a from-scratch runtime-built block could legitimately Resources.Load<Material>(...) -- unverified; requires an actual asset-name dump of the game's Resources.assets/bundles.",
    "Whether a freshly AddComponent<WMWorld>()'d instance (never deserialized from the baked prefab, so the serialization-layout landmine described at WMWorld.cs:2069-2074 wouldn't apply) initializes and behaves identically to the shipped, deserialized singleton -- only a portion of WMWorld.cs's 2200+ lines were read this session; its Singleton<WMWorld> base class and the full Initialize/OnInitialize/Update lifecycle were not fully audited for other baked-only assumptions.",
    "Whether SetDisc's hardcoded 'disc != 1 && disc != 4' (WMWorld.cs:1661) is the only hardcoded disc-domain constant in the engine, or whether other call sites (WorldConfiguration.GetDisc, the save-file's disc byte, NCalcUtility.cs:307's 'WorldDisc' scripting variable which reads ff9.w_frameDisc, etc.) also assume exactly two valid discs -- only the sites surfaced by this session's targeted greps were examined; a full-engine audit of every 'disc =='/'frameDisc' comparison was out of scope here."
  ]
}
```

## R3 -- World registration + dispatch (state vs. geography)

```json
{
  "state_vs_geography_verdict": "Two SEPARATE, currently DECOUPLED axes. (1) EventDB world-STATE (wldMapNo 9000-9012) is dispatched by ff9InitStateWorldMap(MapNo) [ff9.cs:9293-9312]: it writes map.nextMapNo/ff.wldMapNo and loads+runs the .eb named by FF9DBAll.EventDB[MapNo] from the World/ subfolder. It never touches currentDisc/w_frameDisc or mesh loading -- pure gameplay-logic/script/camera layer. (2) Mesh-tree/disc selection (1 vs 4) is computed independently by WorldConfiguration.GetDisc() [WorldConfiguration.cs:234-241]: returns 4 if a data-driven Disc4 NCalc condition is active, else the hardcoded default (ScenarioCounter >= 11090 ? 4 : 1). This runs at WMWorld.Init [WMWorld.cs:135-138] and never consults wldMapNo/EventDB. Grep confirms zero cross-reference either direction. A new dispatcher 9013 would run its own .eb but render on whatever disc GetDisc() currently returns, with no say of its own. CAVEAT: disc is capped at exactly {1,4} by one ternary/cast; WMWorld.SetDisc [WMWorld.cs:1659-1671] only Debug.LogErrors for other values, does not block them. Per-cell prefabs load via generic string format WorldMap/Prefabs/WorldDisc{disc}/r{y}/Block[x][y] [WMWorld.cs:512] -- disc-agnostic as a path mechanism. BUT the coarse 480-cell topology (InitialX/InitialY/IsSea) comes from ONE serialized field, public Transform WorldDisc on WMWorld [WMWorld.cs:2033], baked into the pre-built prefab per the project's own comment [:2070-2074]; BuildBlockArray(this.WorldDisc) [:105,449] walks its children, and there is ZERO runtime C# reassignment of .WorldDisc anywhere -- the coordinate grid/land-sea baseline is shared fixed infrastructure regardless of disc value. CONCLUSION: a new EventDB world-state (9013+) is cheap and already-precedented (EventDB is a runtime-mutable Dictionary DataPatchers.cs already writes into) but does NOT create new geography by itself. A literal 3rd mesh tree is far heavier: engine-code widening of GetDisc/SetDisc is trivial, but whole-GameObject block prefabs cannot be loose-file-loaded (AssetManager.LoadFromDisc errors for GameObject, AssetManager.cs:382,392-426 -- the only loose hook is WorldMeshOverride's MESH-ONLY .ff9mesh format, built specifically because GameObject loose-loading is unsupported, WorldMeshOverride.cs:12); a new WorldDisc3 prefab set would need a mod AssetBundle (plausible per the prefix-based GetBelongingBundleFilename, AssetManagerUtil.cs:372-387) requiring a real Unity 5.2.3 Editor session -- a capability class the toolkit does not have today; and whether the shared WorldDisc topology Transform could ever encode a different land/sea silhouette per disc is unresolved (lives in a binary Unity asset outside Assembly-CSharp). The CHEAP, precedented version of Path D: keep disc at 1 or 4, mint a new EventDB dispatcher for its own script/camera/entrance identity, and build the new area via WorldMeshOverride per-cell (disc,x,y) reclaim-donor overrides inside the EXISTING 480-cell grid -- the Southern Ring's own technique. A true 3rd mesh tree beyond that grid is not proven possible from source alone.",
  "worldscene_directive_design": "Add 'WorldScene <id> <name> [disc=1|4]' to DataPatchers.cs beside FieldScene (:497-529) / BattleScene (:530-548). Required registration: FF9DBAll.EventDB[ID] = 'EVT_WORLD_' + name -- zero new infrastructure, EventDB is already a runtime-mutable Dictionary<Int32,String> that FieldScene (:516) and BattleScene (:538) already write into; this is a copy-paste-and-rename. Do NOT reuse FieldScene's eventIDToFBGID/eventIDToMESID side-writes (field-specific, unused by ff9InitStateWorldMap, which only calls the stateless ETb.InitMessage()). Ship the .eb at Assets/Resources/CommonAsset/EventEngine/EventBinary/World/{Lang}/EVT_WORLD_{name}.eb.bytes, loaded via loadEventData's AssetManager.LoadBytesMerged (EventEngineUtils.cs:1858-1859), which checks loose mod-folder files before Resources.Load -- so the script itself is a plain drop-in loose file, no rebuild. Optionally a 4th token registers into ff9.eventWorldMaps (ff9.cs:10511, also a mutable static HashSet<Int16>) if the state is cutscene-only. Treat disc= as BOOKKEEPING ONLY at first: it does not grant new geometry (disc stays ScenarioCounter-derived, independent of dispatcher id); it just tells the kit which existing tree the dispatcher's WorldMeshOverride reclaim content (already keyed disc,x,y) should target, mirroring every existing world/*.py module's disc parameter. If a real 3rd disc is later pursued, the directive would need disc=N (N not in {1,4}) gated on two small engine edits (widen GetDisc's return expression :240, relax SetDisc's {1,4} warning :1661-1664) PLUS a mod AssetBundle supplying new WorldDisc{N} prefabs -- a new toolkit capability (Unity asset authoring, not loose-file patching) -- gated on the WorldDisc-topology unknown below. The EventDB half of WorldScene is low-risk precedented; the disc/geometry half should ship as documented bookkeeping until the unknowns are probed.",
  "evidence": [
    {
      "file_line": "ff9.cs:9293-9312",
      "quote": "ff9InitStateWorldMap writes map.nextMapNo=ff.wldMapNo; loads .eb via FF9DBAll.EventDB[MapNo] + loadEventData(ebSubFolderWorld); StartEvents; ETb.InitMessage(). No disc/mesh reference."
    },
    {
      "file_line": "WorldConfiguration.cs:234-241",
      "quote": "GetDisc(): return _customDiscModifier.IsActive ? 4 : 1 (if condition set), else w_frameScenePtr >= 11090 ? 4 : 1."
    },
    {
      "file_line": "WMWorld.cs:135-138",
      "quote": "w_frameScenePtr = ushort_gEventGlobal(0); w_frameDisc = WorldConfiguration.GetDisc(); currentDisc = w_frameDisc."
    },
    {
      "file_line": "WMWorld.cs:1659-1671",
      "quote": "SetDisc(disc): logs error if disc not in {1,4} but still sets w_frameDisc/currentDisc and reloads WorldMapDebug scene -- warning, not a block."
    },
    {
      "file_line": "WMWorld.cs:511-514",
      "quote": "name = String.Format(WorldMap/Prefabs/WorldDisc{0}/r{1}/{2}, disc, initialY, arg); AssetManager.Load<GameObject>(name)."
    },
    {
      "file_line": "WMWorld.cs:2033,2070-2074",
      "quote": "public Transform WorldDisc; comment: WMWorld is a MonoBehaviour baked into the pre-built WorldDisc prefab."
    },
    {
      "file_line": "WMWorld.cs:105,449",
      "quote": "InitialBlocks/Blocks = WMWorld.BuildBlockArray(this.WorldDisc) -- both built from the same single WorldDisc Transform."
    },
    {
      "file_line": "FF9DBAll.Events.cs:5-8,1834-1846",
      "quote": "public static Dictionary<Int32,String> EventDB = new Dictionary<Int32,String>{ ... {9000,EVT_WORLD_WORLD00} ... {9012,EVT_WORLD_WORLD12} ... }"
    },
    {
      "file_line": "DataPatchers.cs:497-517",
      "quote": "FieldScene branch: FF9DBAll.EventDB[ID] = EVT_ + entry[4]; also writes eventIDToFBGID and eventIDToMESID."
    },
    {
      "file_line": "DataPatchers.cs:530-540",
      "quote": "BattleScene branch: FF9DBAll.EventDB[ID] = EVT_BATTLE_ + entry[2]; also writes FF9BattleDB.SceneData/MapModel."
    },
    {
      "file_line": "EventEngineUtils.cs:25-27",
      "quote": "ebSubFolderField = Field/; ebSubFolderWorld = World/."
    },
    {
      "file_line": "WorldMeshOverride.cs:8-23,77-83",
      "quote": "Comment: AssetManager.LoadFromDisc<Mesh/GameObject> is unsupported, there is no loose-mesh hook, only this one. HasLandOverride(disc,x,y) keyed generically by disc."
    },
    {
      "file_line": "AssetManager.cs:372-383,425-426",
      "quote": "LoadFromDisc<T> comment: GameObject ... Cant be read from disc currently; falls through to Log.Error for unsupported types."
    },
    {
      "file_line": "AssetManagerUtil.cs:372-387",
      "quote": "GetBelongingBundleFilename checks CheckModuleBundleFromName(ModuleBundle.WorldMaps, assetName) by path prefix, not a fixed name catalog."
    },
    {
      "file_line": "AssetManager.cs:979-984",
      "quote": "IsAssetInModInBundle looks up a mod AssetBundleRef by bundle filename and checks assetBundle.Contains(nameInBundle)."
    },
    {
      "file_line": "ff9.cs:10510-10513",
      "quote": "IsEventWorldMap => eventWorldMaps.Contains(wldMapNo); eventWorldMaps is a mutable static HashSet<Int16> seeded with 9001,9004,..."
    },
    {
      "file_line": "FF9StateGlobal.cs:916-995",
      "quote": "public Int16 wldMapNo { get => _wldMapNo; ... } private Int16 _wldMapNo;"
    },
    {
      "file_line": "dictpatch.py:65-67,131",
      "quote": "ID_KEYED_DIRECTIVES = (FieldScene, LocationName) -- WorldScene not present anywhere in the kit today."
    },
    {
      "file_line": "world/entrance.py:906,910",
      "quote": "world_state=9000 + int(name[-2:]) -- kit already treats 9000-9012 as the known dispatcher band."
    }
  ],
  "unknowns": [
    "Whether WMWorld.WorldDisc (WMWorld.cs:2033) is one shared marker hierarchy for both discs today, or the Unity scene secretly holds a second root -- unreadable from C# source alone; the central unknown for whether new coastline geometry is possible at all vs hard-capped at the existing 480-cell silhouette.",
    "Whether a mod AssetBundle can introduce a genuinely new-named asset (e.g. WorldDisc3/...) via ModFileList.txt + IsAssetInModInBundle, or whether mod bundles are restricted to overriding names the base game's own worldmap bundle already contains -- needs a cheap in-game probe.",
    "Whether world-map dialogue for a new dispatcher needs any id-keyed message-block registration -- ff9InitStateWorldMap only calls the stateless ETb.InitMessage(), suggesting no, but the .eb text-display opcode chain was not fully traced.",
    "Whether SetDisc's log-only gate is the sole validation on disc end-to-end, or some other consumer (minimap, save schema, netsync, a fixed-size array indexed by disc-1) silently assumes disc in {1,4} and would misbehave rather than warn.",
    "Call-site ordering of DataPatchers.cs's directive loop relative to the first possible ff9InitStateWorldMap call (New Game boot) was not traced, so it is unconfirmed a WorldScene-registered id would exist in time.",
    "Whether the existing Disc4 WorldEnvironment NCalc token is already exposed through any ff9mapkit Python authoring surface, or is unused stock Memoria capability -- not grepped specifically."
  ]
}
```

## R4 -- Authoring a brand-new world .eb dispatcher from scratch

```json
{
  "can_author_from_scratch": "NO, not today -- but the gap is narrow, and the existing tooling generalizes to it almost for free.\n\n(1) THE .eb CONTAINER IS FORMAT-AGNOSTIC BETWEEN FIELD AND WORLD. Confirmed by reading the whole of eb/model.py and eb/edit.py: neither file contains any field-vs-world branch anywhere. world/entrance.py (entrance.py:129-144, 360-369, 549-568) and studies/overworld-topography/scene-ladder/rung3c_origin_departure.py (whole file; FNAME=\"EVT_WORLD_WORLD11.eb.bytes\" at line 83) both call eb.model.EbScript and eb.edit.replace_function_body / add_function / repoint_switch_case, and eb.cmdasm.assemble_block/disassemble_block, DIRECTLY against real WORLD .eb bytes with zero adaptation -- the exact same primitives build.py uses for fields. So the byte-splicing/assembly layer needs nothing new to work on a world dispatcher.\n\n(2) BUT NOTHING IN THE KIT EVER SYNTHESIZES AN .eb CONTAINER FROM NOTHING. eb/model.py's own docstring calls the 40-byte header at [0x04..0x2B] \"opaque; preserved verbatim\" (model.py:15,44), and EbScript's only constructors (from_bytes/from_file, model.py:99-106) require a valid \"EV\" magic already present, raising otherwise (model.py:93-94). The field-authoring \"new field from scratch\" path is not actually from scratch either: build.py:5311 calls `_data.blank_field_bytes(lang)`, and data/__init__.py's own docstring says that blank field is \"a cleaned clone of a base field\" (data/__init__.py:6-9,18-19) -- every .eb the kit ever produces, field or world, starts life as a byte-exact clone of a REAL file extracted from the user's own install (`extract-templates`), never a from-nothing header/entry-table.\n\n(3) FOR WORLD DISPATCHERS SPECIFICALLY there is no `blank_world_bytes()` counterpart to `blank_field_bytes()`, and world/entrance.py's `load_world_dispatchers()`/`load_all_dispatchers()` (entrance.py:87-126) only ever loads the 13 REAL EVT_WORLD_WORLD00..12 files live from p0data. Verified this session by running it against the actual live install: exactly 13 files (996B-23584B), of which 9 (WORLD00,02,03,05,07,08,09,10,11) carry a base-2/59-case AREA switch (`dispatcher_cases()`, entrance.py:129-144) -- the free-roam states -- and 4 (WORLD01,04,06,12) do not, and are scripted one-shot cutscene states (WORLD04's Main_Init ends `Field(2261)`; matches ff9.cs:10511-10513's `eventWorldMaps` HashSet, e.g. 9001 = \"World Map\\\\Event: Cargo Ship\"). So today's `world/` module can only EDIT one of these 13 real donors in place (exactly what entrance.py and the scene-ladder rung do); it has no path to mint a 14th.\n\n(4) THE .eb ENGINE-SIDE LOADING IS FULLY DATA-DRIVEN AND GENERALIZES FOR FREE, up to one missing directive. Verified directly in the Memoria source (C:\\gd\\FFIX\\Memoria\\Assembly-CSharp): `ff9InitStateWorldMap(Int32 MapNo)` (ff9.cs:9293-9312) does `String ebFileName = FF9DBAll.EventDB[MapNo]; map.evtPtr = EventEngineUtils.loadEventData(ebFileName, EventEngineUtils.ebSubFolderWorld);` -- an ordinary `Dictionary<Int32,String>` lookup (FF9DBAll.EventDB declared at FF9DBAll.Events.cs:7), no numeric range check anywhere in this path, in `WMAPJUMP`'s handler (EventEngine.DoEventCode.cs:2458-2462, `this.SetNextMap(this.getv2()); return 5;`), or in `SetNextMap`/`FF9ChangeMap` (EventEngine.cs:1296-1323, which just writes `nextMapNo` keyed on the CURRENT execution mode). This is the exact same indirection mechanism fields use. HOWEVER `FF9DBAll.EventDB` is a hardcoded C# static-initializer dictionary, and the only DictionaryPatch directives that write into it at mod-load time are `FieldScene` and `BattleScene` (Memoria\\Configuration\\DataPatchers.cs:497-548 -- confirmed via a full grep of every `String.Equals(entry[0], ...)` dispatch in that file, 22 directives total, no \"WorldScene\"). So a genuinely new world-map id cannot be registered via any existing DictionaryPatch line -- reachability needs one small, precedented new engine-patch directive (EventDB[ID]=\"EVT_...\" + eventIDToMESID[ID]=mesID; simpler than FieldScene since no FBG-art registration is needed). This sits in memoria-patches/, not ff9mapkit/eb/ or ff9mapkit/world/, but it gates whether any from-scratch dispatcher (however built) is ever reachable.\n\n(5) THE FREE-ROAM CAMERA REQUIRES NO PER-WORLD .eb SETUP BEYOND A CONTROLLED ACTOR -- directly verified, not just repeated from memory. `DefinePlayerCharacter` (opcode 0x2C) does nothing but `this._context.controlUID = this.gExec.uid` (EventEngine.DoEventCode.cs:1033-1045). Every world frame tick re-derives `ff9.w_moveActorPtr = ff9.GetControlChar()` off that UID (ff9.cs:3795, inside the same per-frame block that calls `w_cameraUpdate()` at ff9.cs:3813). `w_cameraUpdate()` (ff9.cs:2665-2691) computes the ENTIRE free-roam camera -- FOV, eye/aim offsets, rotation -- purely from `w_moveCHRControlPtr`/`w_moveActorPtr`'s live transform plus a terrain-topograph query; there is no separate camera-init opcode anywhere in the .eb opcode table this session found. So the prior \"pure managed C#, automatic once an actor exists\" claim is CONFIRMED at the source level, not just repeated from memory -- the one and only .eb-side requirement is that some InitObject'd entry's own Init calls DefinePlayerCharacter() (verified in a real dispatcher: WORLD09 entry 5 tag 0 does this conditionally on the rider state, entrance.py's worldexit.py documents the on-foot twin object at model 310/309).",
  "minimal_dispatcher_spec": "Grounded in a live byte-decode this session of WORLD02 (8144B, the smallest of the 9 real free-roam dispatchers) and WORLD04 (996B, a cutscene-only dispatcher, for contrast) via the kit's own eb.model/eb.cmdasm tooling against the real installed game.\n\nCONTAINER: identical \"EV\" format to a field .eb (model.py:9-30) -- magic, entryCount byte, 40B opaque header, 84B name region, then a u16-addressed entry table. No world-specific format work needed; eb.model.EbScript / eb.edit already handle it.\n\nENTRY 0 (Main_Init, tag 0) -- decoded verbatim from WORLD02 (79 bytes):\n```\nSET(Global.Byte[102] = 2)                 -- unread this session; a world-family/mode selector (untraced)\nInitCode(11,0); InitCode(1,0); InitCode(2,0); InitCode(3,0); InitCode(4,0)   -- arm the \"type 0\" daemon/code entries\nInitObject(14,0); InitObject(7,0); InitObject(8,0); InitObject(9,0); InitObject(10,0); InitObject(5,0); InitObject(6,0)  -- arm the \"type 2\" positional/actor entries (one of which -- WORLD09's entry 5 -- is the walking avatar whose OWN Init calls DefinePlayerCharacter())\nSET(Map.Byte[24] = 100)                   -- the idle/window-close sentinel other logic (entry 0 tag 1, and entry 1's shared run) reads\nSET(Map.Byte[31] = 0)\nRunWorldCode(0, 4)                        -- ff9.cs:3847-3858, weather auto-cycle: cosmetic tuning, not required\nRunWorldCode(26, 365)                     -- ff9.cs:3929-3931, w_frameEventBattleProb: the RAGTIME MOUSE probability (NOT the encounter rate -- corrected 2026-08-27), not required\nSET(Map.Byte[33] = 0)\nRET()\n```\nOnly the InitObject of a DefinePlayerCharacter()-calling avatar entry, plus (arguably) Map.Byte[24]=100 if entry-0's own idle loop (tag 1) is kept, are load-bearing for a \"stand there and look around\" world; the RunWorldCode calls and Global.Byte[102]/[31]/[33] writes are tuning/unverified-but-plausibly-optional (see unknowns).\n\nENTRY 0 tag 1 (idle loop, 39 bytes, WORLD02) -- appears to be AUTO-ARMED by the engine for entry 0 specifically: no dispatcher's Main_Init ever explicitly InitObject/InitCode's entry 0 itself, yet it clearly runs every frame (it is the CloseWindow(6)/CloseWindow(7) housekeeping entrance.py's own docstring describes at entrance.py:226-236). Content: `if Map.Byte[24]<=100: CloseWindow(6); CloseWindow(7); Map.Byte[35]=0; end; Map.Byte[24]=100; tick`. Not required if the minimal world never opens windows 6/7 (i.e. never authors an entrance/vehicle-icon HUD).\n\nAREA-SWITCH / ENTRY 1: NOT NEEDED DAY ONE. Confirmed both by structure and by cross-referencing entrance.py's own machinery: entry 1 tag 0 is a 1-byte stub RET (WORLD02); tag 1 is the large (1307B in WORLD02) shared run -- opens with `SWITCH(0, <default>, <case0>)` testing `Global.Byte[190]` (a global \"transition pending\" flag, not a per-map one) to either fall into vehicle-icon/nameplate window bookkeeping or the AREA switch further down (the base-2/59-case switch `dispatcher_cases()` finds). This whole apparatus exists only to service (a) the on-foot entrance handshake that `entrance.py`'s `author_entrance()` fires via `RunScriptSync(6,1,11)` -- itself only triggered by a WorldEvent tile the author places -- and (b) a few hardcoded special cases (e.g. case 52 = the quicksand `Battle(0,144)`, entrance.py:815). A dispatcher that never authors any entrance tile has nothing to invoke this machinery, so it can validly omit entry 1's InitCode arming (and even the entry body) entirely on day one, adding it later exactly the way entrance.py already adds entrances to the 13 real dispatchers -- EXCEPT entrance.py's switch tooling (eb.edit.find_switch/repoint_switch_case) only LOCATES and REPOINTS an EXISTING switch; nothing constructs a brand-new AREA switch from zero cases. eb.cmdasm.assemble_block CAN mechanically emit a fresh SWITCH/SWITCH2 instruction from text (cmdasm.py's `_CTRL_NAMES` maps the mnemonics; `assemble_instruction`'s variable-operand branch at cmdasm.py:112-127 handles 0x06/0x0B/0x0D), so this is buildable, just not yet wired into a reusable helper.\n\nPLAYER AVATAR: at least one InitObject'd entry whose own Init calls DefinePlayerCharacter() (verified byte-for-byte in WORLD09 entry 5 tag 0, gated on a rider-state check; worldexit.py documents the on-foot twin at model 310/309). This is the ONLY .eb-side requirement the free-roam camera has (see can_author_from_scratch point 5) -- no explicit camera-setup opcode exists or is needed.\n\nEventDB / FILE PLACEMENT: `.eb.bytes` goes at `.../eventbinary/world/<lang>/<NAME>.eb.bytes` per language (entrance.py `_WORLD_EB_SUBDIR`, matching the engine's `EventEngineUtils.ebSubFolderWorld` used in `ff9InitStateWorldMap`, ff9.cs:9307). Registering a NEW MapNo to that filename needs a new DictionaryPatch directive (see gap 4 in kit_gaps) since no \"WorldScene\" directive exists today.",
  "kit_gaps": [
    "No `blank_world_bytes()` (or any curated minimal-world-dispatcher donor + accessor) in ff9mapkit/ff9mapkit/data/__init__.py -- only `blank_field_bytes()` exists (data/__init__.py:32-40). Nothing anywhere in the kit synthesizes an .eb's opaque 40-byte header/entry-table region from first principles (model.py:15,44 calls it 'opaque; preserved verbatim'), so a from-scratch world author needs a real donor's bytes as a starting container -- e.g. clone-and-strip one of the 13 real EVT_WORLD_WORLDxx files (WORLD04 at 996B is the smallest overall; WORLD02 at 8144B is the smallest that already carries a full free-roam AREA switch).",
    "No orchestrator module for a world dispatcher analogous to build.py's field construction (field.toml -> blank_field_bytes + splice). Today ff9mapkit/ff9mapkit/world/entrance.py only EDITS/EXTENDS the 13 real donors in place (author_entrance, entrance.py:731-1039); nothing assembles a fresh entry-0 Main_Init (spawn avatar + DefinePlayerCharacter, Byte[24]=100, idle loop) from cmdasm text end-to-end as a reusable function, though every needed primitive (cmdasm.assemble_block, eb.edit.append_entry/add_function/grow_entry_table) is already proven generically on world bytes by the scene-ladder study.",
    "No reusable 'start a new AREA switch from zero cases' helper. eb/edit.py's switch tooling (find_switch, repoint_switch_case, switch_case_reloff_pos, edit.py:383-455) all assume an EXISTING switch instruction to locate and repoint a dead arm of; cmdasm.assemble_block can mechanically emit a brand-new SWITCH/SWITCH2 instruction from text (verified capability, cmdasm.py:112-127), but nobody has built the 'author entry 1 from nothing' wrapper around it.",
    "ENGINE-LAYER (outside ff9mapkit/eb/ and ff9mapkit/world/, in memoria-patches/): no 'WorldScene' DictionaryPatch directive exists in Memoria\\Configuration\\DataPatchers.cs -- only 'FieldScene' (DataPatchers.cs:497-529) and 'BattleScene' (:530-548) write into the hardcoded FF9DBAll.EventDB dictionary (FF9DBAll.Events.cs:7). Without a small new directive (EventDB[ID]='EVT_...' + eventIDToMESID[ID]=mesID; simpler than FieldScene, no FBG-art fields needed), a brand-new world-map id has no way to be registered at mod-load time, so no from-scratch dispatcher -- however well-built -- is reachable via WorldMap(<id>)/ff9InitStateWorldMap today. This is the single hardest gate on Path D's day-one reachability and is NOT an ff9mapkit/ python-side gap; it needs a memoria-patches/ change following the FieldScene precedent."
  ],
  "unknowns": [
    "What WMWorld actually renders/raycasts a from-scratch dispatcher's spawned avatar against if its wldMapNo has no matching terrain-block data: discmirror.py's own docstring states the overworld ships exactly TWO asset trees ('worldmap/disc1' and 'worldmap/disc4', only WorldDisc1/WorldDisc4 prefabs exist). I did not trace WMWorld.cs's scene-build path to see whether terrain selection is keyed off wldMapNo directly, off a separate 'currentDisc' state variable, or something else -- this is squarely the mesh/scene subsystem's problem (worldpack.py/discmirror.py/mesh.py), not the .eb dispatcher's, but it gates whether a from-scratch dispatcher can be PLAYTESTED at all before that side is solved. Needs a cheap probe: register a new EventDB id pointing at a cloned dispatcher and see what WMWorld does with no matching disc-tree content.",
    "Whether entry-0's tag-1 is truly engine-auto-armed with zero explicit call, or whether some other mechanism (outside the .eb bytes I decoded) arms it. I inferred this purely from never observing an explicit InitObject/InitCode(0,...) call for entry 0 across every Main_Init I decoded (consistent with the field-side Main_Init/Main convention in CLAUDE.md's glossary), but did not find and read the specific C# 'entry 0 is implicitly instantiated' code path to confirm at the engine-source level.",
    "Whether RunWorldCode(0,4) (weather auto-cycle) or RunWorldCode(26,<n>) (the Ragtime Mouse probability) -- or any other RunWorldCode call -- is a hard requirement for the world tick to run without an exception/soft-lock, versus purely cosmetic tuning a minimal world can omit. I read w_frameSetParameter's switch (ff9.cs:3842-3931) and neither write looks load-bearing for the frame loop itself, but did not exhaustively trace every downstream reader of w_weatherAutoChange / w_frameEventBattleProb for a null/uninitialized-state crash on a wldMapNo that never touches them. Worth a cheap in-game probe (deploy a stripped Main_Init, tilde-warp to the new id) before committing engineering effort.",
    "What Global.Byte[102] does (set to 2 in WORLD02's Main_Init, 4 in WORLD04's) -- I did not trace its reader(s); likely a world-family/BGM/UI-mode selector. Unconfirmed whether a from-scratch world needs a specific value, an unused value, or can omit it.",
    "The exact mechanism that turns EventEngine.DoEventCode's WMAPJUMP return value (5, vs Field's 4) into `map.nextMode = 3` before ff9ShutdownStateFieldMap's switch (HonoluluFieldMain.cs:441-457) reads it. I traced FF9ChangeMap (EventEngine.cs:1296-1323) dispatching on the CURRENT `_ff9Sys.mode` (not a value carried by the opcode), which strongly suggests the field->world transition is opcode-identity-driven rather than value-range-gated (i.e. a from-scratch id is not blocked by some hidden 9000-9012 range check) -- but I did not find and read the exact code that sets nextMode=3 off the return-code-5 path to close this out with certainty.",
    "Whether any OTHER hardcoded table in Assembly-CSharp beyond FF9DBAll.EventDB / EventEngineUtils.eventIDToMESID (both confirmed generic Dictionary<Int32,*>, no range check found) silently assumes exactly the 13 known wldMapNo values -- e.g. `eventWorldMaps` (ff9.cs:10511, a HashSet -- open, but I did not check every reader), the disc-switch/debug-menu World tab, or the minimap/navi tables. Not exhaustively grepped this session; a from-scratch id could still snag on one of these even with EventDB/mesID registered."
  ]
}
```

## R5 -- Minimap/location + encounter-zone table ceilings

```json
{
  "tables": [
    {
      "name": "w_naviLocationPos (minimap landmark markers)",
      "capacity": "ff9.navipos[2,64] -- OUTER dim = 2 worlds (hardcoded), INNER dim = 64 landmark slots per world",
      "current_usage": "World-slot 0 (disc1-3): 26 of 64 populated (idx 0-25 real vx/vy/tx/ty; idx 26-63 all-zero padding). World-slot 1 (disc4): 54 of 64 populated (idx 0-48=49 real + idx 54-58=5 real; idx 49-53 and 59-63 zero padding). Verified by reading every array3[0,n]/array3[1,n] literal, ff9.cs:422-1317.",
      "needs_engine_change": true,
      "file_line": "declared readonly ff9.cs:10393; populated ff9.cs:421-1318 (array3 = new ff9.navipos[2,64]); consumed via ff9.cs:6338-6368,7136 keyed by ff9.w_naviMapno (SByte, ff9.cs:10369)",
      "reasoning": "CONFIRMED by direct count, correcting/verifying prior-research's '26 / 54' claim exactly. The array is `public static readonly`, assigned once in the static ctor -- adding a 3rd world's markers at array3[2,*] is an IndexOutOfRangeException at runtime; the outer dim must be grown in source and recompiled (an ordinary memoria-patches-style engine change, same shape as s34). BUT: within an EXISTING world slot there IS free capacity today -- 38 unused slots on disc1's side, 10 on disc4's -- so a NEW LANDMARK on one of the two existing worlds needs no dimension growth, only editing the existing literal (still a recompile since the array is readonly, but not a structural change). A genuinely 3rd world's OWN landmark set requires the [2,64]->[3,64]-class engine change."
    },
    {
      "name": "w_naviMapno world-index selector + w_naviGetPos coordinate normalizer",
      "capacity": "Binary (0 or 1); SByte field so the type itself isn't the limiter",
      "current_usage": "0 selected for w_frameScenePtr<5990 (disc1-3 era); 1 selected for >=5990 (disc4) at world-pack-constructor time; also force-set to 1 for the WorldMapDebug scene.",
      "needs_engine_change": true,
      "file_line": "assignment ff9.cs:8833-8836 (`if (w_frameScenePtr >= 5990) w_naviMapno=1; else 0;`); debug override ff9.cs:3718; consumer ff9.cs:7094-7110 w_naviGetPos (only handles ==0 and ==1 branches)",
      "reasoning": "This is the actual selector that indexes into w_naviLocationPos's outer dimension, and it is a hardcoded scenePtr THRESHOLD (5990), not derived from w_frameDisc. w_naviGetPos itself is an if/else-if with no default case -- any value other than 0 or 1 silently leaves sx=sy=0 (minimap marker collapses to top-left, no crash but visually broken). A 3rd world needs both this threshold switch AND w_naviGetPos extended with a 3rd normalization formula (its own view-rect constants, currently two different literal formulas for 0 vs 1)."
    },
    {
      "name": "w_worldAreaZone (area -> zone LUT)",
      "capacity": "Byte[64] -- exactly matches the 6-bit 'area' field ((IDALL & 0x3F00) >> 8) decoded by m_GetIDArea",
      "current_usage": "FULLY DENSE: all 64 slots populated with values 0-24 (25 distinct zone ids). No free/unassigned area id exists. Table is FLAT and shared across BOTH existing worlds/discs (not disc-indexed at all).",
      "needs_engine_change": false,
      "file_line": "literal ff9.cs:1348-1414; decl ff9.cs:10469 (readonly Byte[]); consumer w_worldArea2Zone ff9.cs:9229-9232, called from w_worldGetBattleScenePtr ff9.cs:9234-9237",
      "reasoning": "Needs_engine_change is FALSE only for getting SOME/ANY encounters: a new world's terrain can be tangent.x-tagged (via ff9mapkit/world/extract.py's already-existing encode_id(), verified against m_GetIDArea's exact bit layout at ff9.cs:2340-2343) with an EXISTING 0-63 area id and it will resolve to that area's existing zone -- zero engine change, fully within the toolkit's current mesh-authoring capability (terrain.py already reads/writes this exact tangent.x IDALL encoding, confirmed against WMBlock.cs:210/231's `tangents[triangles[...]].x` raycast read). HOWEVER because the table is dense (no free area id) and DISC-AGNOSTIC (m_GetIDArea/w_worldArea2Zone never consult w_frameDisc), reusing an area id also reuses whichever real stock place currently owns that area's zone slice -- there is no way to give a 3rd world an UNENTANGLED zone of its own without an engine change (see w_worldZoneFigure/w_worldZoneInfo row below)."
    },
    {
      "name": "w_worldZoneFigure / w_worldZoneInfo (zone -> EncountData row-count LUT)",
      "capacity": "Byte[26] each -- 25 real zones (0-24) + 1 terminator entry (value 0); the cumulative-sum loop that builds w_worldZoneInfo from w_worldZoneFigure is ALSO hardcoded to exactly 26 iterations",
      "current_usage": "All 26 entries populated (25 real per-zone row-counts summing to the pack's total EncountData rows, +1 terminator).",
      "needs_engine_change": true,
      "file_line": "w_worldZoneFigure literal ff9.cs:1415-1443, decl ff9.cs:10471; w_worldZoneInfo alloc ff9.cs:1444 (`new Byte[26]`), decl ff9.cs:10473; cumulative-sum loop ff9.cs:8821-8830 (`for (num2=0L; num2<26L; ...)`)",
      "reasoning": "THREE hardcoded constants (the array literal length, the Byte[26] size, and the literal '26L' loop bound) must grow in lockstep to add zone 25 -- a genuine engine change. AND it is gated behind w_worldAreaZone's density problem above: even after growing this table, no area id (0-63) is free to point at the new zone 25 without EITHER growing w_worldAreaZone past 64 (impossible without widening m_GetIDArea's bit mask, which eats into the topograph or event bits of the same packed tangent.x value used map-wide) OR repurposing an existing area id (data-only, but entangles with a real stock place, same caveat as above)."
    },
    {
      "name": "w_frameBattleScenePtr / EncountData (discmr.img kWorldPackEncountTable, the actual per-zone monster rows)",
      "capacity": "Fixed row count baked in the loaded discmr.img pack, sliced per-zone by the hardcoded w_worldZoneFigure counts above; ff9mapkit/ff9mapkit/world/worldpack.py's own docstring (line 105-106, not independently re-verified byte-for-byte by me this session) states 355 encounter records + 9x12 specials per pack.",
      "current_usage": "Whatever's authored in the shipped disc1/disc4 discmr.img; each zone's slice is exactly the row-count w_worldZoneFigure[zoneId] allocates, no more no less.",
      "needs_engine_change": false,
      "file_line": "loaded ff9.cs:8831 (`w_frameBattleScenePtr = w_framePackGetPtr_w_frameBattleScenePtr(w_memorySPSData, 3)`); consumed ff9.cs:9234-9257; kit codec ff9mapkit/ff9mapkit/world/worldpack.py:1-40,104-136,217-252 (Discmr class, ENCOUNT_IDX=3, load_discmr/deploy_discmr, whole-file mod override, no DLL)",
      "reasoning": "Content of already-allocated rows (which monster/battle-scene a given zone+topograph+fog combination rolls) is fully data-driven and already tool-supported for in-place edits (no DLL) -- this is the genuinely-free part of the encounter path. It is NOT free to ADD rows to a zone (capped by w_worldZoneFigure, see above), and the FILE this table loads from is gated by the disc1-vs-disc4 selector below, not by an arbitrary 'which world' key."
    },
    {
      "name": "w_fileImagenameServer1 / w_fileImagenameServer4 world-pack FILE selector",
      "capacity": "Exactly 2 named file-sets (5 filenames each: discmr.img, pk_stat_.img, pk_temp_.img, model_hm.nwp, model_vm.nwp)",
      "current_usage": "Both slots in active use (disc1, disc4); selection is `if (w_frameDisc==1) array=Server1; else array=Server4;` -- i.e. a strict 2-way branch, not an N-way dispatch, so ANY w_frameDisc value other than literal 1 silently falls into the disc4 branch.",
      "needs_engine_change": true,
      "file_line": "arrays declared+populated ff9.cs:352-368; selector ff9.cs:3621-3644 (w_fileSystemConstructor)",
      "reasoning": "This is the actual gate on whether a 3rd world can have its OWN encounter/stat/temp data pack at all. Confirmed by full read of the function: there is no third array, and no branch could ever reach one -- a 3rd, independent discmr.img requires adding a `w_fileImagenameServerX` array plus a real 3rd branch here (engine change). Without this change, a new world is forced to silently reuse either the disc1 or disc4 pack file wholesale (same file the corresponding vanilla disc already uses), which the kit's worldpack.py can still edit in place, but any edit also changes that same disc's real encounters."
    },
    {
      "name": "WorldConfiguration.GetDisc()",
      "capacity": "Return type is Byte (0-255) but the achievable OUTPUT DOMAIN is hardcoded to exactly {1, 4} in every code path, including the 'data-driven' override.",
      "current_usage": "Default: `w_frameScenePtr >= 11090 ? 4 : 1`. NCalc-conditional override (`_customDiscModifier`, set via a `Disc4` token in WorldEnvironment.txt): `_customDiscModifier.IsActive ? 4 : 1` -- the CONDITION is data-driven/NCalc-arbitrary, but the two literals it chooses between are not.",
      "needs_engine_change": true,
      "file_line": "WorldConfiguration.cs:234-241 (GetDisc); mod-config token parsing WorldConfiguration.cs:355-381 (`Disc4` regex case) and 415-430 (LoadWorldEnvironmentSimpleToken)",
      "reasoning": "This directly falsifies treating WorldConfiguration as unconditionally 'free/data-driven for a new world id' -- it is data-driven only in WHEN to switch, never in WHAT to switch to. A 3rd disc value needs this ternary's two literal branches turned into a real 3-or-more-way selection, i.e. an engine change, even though the mod-file surface around it (WorldEnvironment.txt `Disc4 [Condition=...]`) is otherwise a clean NCalc hook that the project could extend."
    },
    {
      "name": "Continent-title banner: scenePtr switch + WorldConfiguration.GetContinentName",
      "capacity": "Exactly 4 named continent banners (titleId 0-3, SByte w_naviTitle)",
      "current_usage": "All 4 in use: 0=Mist, 1=Outer, 2=Forgotten, 3=Lost, keyed off 4 literal w_frameScenePtr values (2400, 5990, 9605, 9890).",
      "needs_engine_change": true,
      "file_line": "scenePtr switch ff9.cs:8838-8852 (inside w_worldSystemConstructor, NOT ff9.cs:8683 as the prior-research pointer claimed -- ff9.cs:8681-8698 is unrelated weather-color-interpolation clamping code, verified by direct read); GetContinentName 4-case switch WorldConfiguration.cs:343-353; sprite rect/duration overrides WorldConfiguration.cs:321-341, 556-612 (Title token, only recognizes the same 4 names or 'All')",
      "reasoning": "CORRECTS the task's cited line number -- I read ff9.cs:8640-8698 directly and it is `w_weatherInterColor`'s t1/t2 clamp, nothing to do with banners. The real switch is 155 lines later. Two separate hardcoded ceilings stack here: (1) the ff9.cs scenePtr->titleId switch has no data-driven hook at all (no scenePtr range is configurable, only 4 literal exact-match cases, default -1/no-title); (2) even if w_naviTitle somehow reached 4, GetContinentName's switch has no case for it (falls through to String.Empty, silent) and the WorldEnvironment.txt `Title` token can only reference one of the 4 existing CONTINENT_NAME_* constants by name (or the 'All' wildcard, which sets shared Rect/Duration for every title, not a per-id override) -- so a 5th, uniquely-named banner needs engine changes in both places."
    },
    {
      "name": "WMWorld.WorldDisc baked block hierarchy + SetDisc()",
      "capacity": "Exactly 2 pre-built WorldDisc Transform hierarchies exist today (one per disc scene), each a 24x20=480-cell WMBlock GameObject tree with InitialX/InitialY/IsSea baked in.",
      "current_usage": "Both in use; Path C tooling (s34-worldmap-mesh-override.patch) already RESHAPES individual existing blocks' terrain meshes via a loose .ff9mesh override hook in WMWorld.RegisterBlockComponent, but creates no new placeholder blocks and no new WorldDisc root.",
      "needs_engine_change": true,
      "file_line": "public Transform WorldDisc field WMWorld.cs:2033; consumed by BuildBlockArray WMWorld.cs:1673-1690 (walks worldDisc.transform's EXISTING children only) and OnInitialize/Initialize WMWorld.cs:57-156,445-474; SetDisc soft-guard WMWorld.cs:1659-1671 (`if (disc!=1 && disc!=4) LogError(...)` -- warns but does not hard-block, then still proceeds); per-block visual dressing load path WMWorld.cs:490-516 IS generic over an integer `disc` via a Resources-style path string `WorldMap/Prefabs/WorldDisc{0}/r{1}/Block[{2}][{3}]`",
      "reasoning": "This is the single largest structural unknown for Path D (folded into the unknowns list too). WorldDisc is a plain serialized Unity Transform field with NO runtime construction code anywhere in WMWorld.cs -- BuildBlockArray only ENUMERATES children that already exist, it never creates them. The project's own in-source comment (WMWorld.cs:2069-2074, authored for the s34 Path-D coastal-reclaim work) states outright: 'WMWorld is a MonoBehaviour baked into the pre-built WorldDisc prefab.' By contrast, the PER-BLOCK visual dressing load (WMWorld.cs:512, AssetManager.Load with a disc-interpolated path) is already string-generic and would resolve a 'WorldDisc3' folder if the ASSET existed. So the ceiling is specifically: does a 3rd WorldDisc's 480 WMBlock placeholders (with their InitialX/InitialY/IsSea/mesh-slot wiring) have to be authored via the Unity Editor (an asset-authoring problem, out of ff9mapkit's current Python-only scope), or can they be instantiated purely from C# at runtime (WMBlock is a plain MonoBehaviour with public, non-serialize-attributed InitialX/InitialY/IsSea fields, WMBlock.cs:243,256-257, which is at least SUGGESTIVE that AddComponent<WMBlock>() + field assignment could work) -- this needs a cheap runtime-instantiation probe before committing engineering effort, not source reading alone."
    },
    {
      "name": "WMPsxCamera.cs",
      "capacity": "N/A -- not a capacity-bound table",
      "current_usage": "Dead. The entire class body (everything except the class declaration itself) is a single C-style block comment spanning lines 7-189 of a 191-line file; only the empty `public class WMPsxCamera {}` shell remains live.",
      "needs_engine_change": false,
      "file_line": "Global/WM/WMPsxCamera.cs:1-191 (read in full)",
      "reasoning": "CONFIRMED genuinely dead/unused as prior research claimed: grepped the whole Assembly-CSharp tree for 'WMPsxCamera' and the only hits are the file itself and the .csproj compile-include line -- nothing instantiates or calls it. The REAL camera math (world-space raycast projection for the overworld) lives directly in WMWorld.cs (CreateProjectionMatrix/PsxProj2UnityProj/PerspectiveOffCenter, WMWorld.cs:1923-1969, plus PsxGeomScreen/ClipDistance/OffCenterOffsetX/Y fields around WMWorld.cs:2190-2200) -- essentially a near-duplicate of WMPsxCamera's commented-out methods, but live and namespaced under WMWorld instead. I grepped this whole file for disc/scenePtr/naviMapno hardcoding (same query used for the disc-hit census above) and NONE of the hits fall inside the camera code -- it's disc-agnostic and would work unchanged for a 3rd world with zero engine change."
    },
    {
      "name": "Disc4 '+254 alternate encounter band'",
      "capacity": "A single hardcoded row offset (254), gated to the first 100 rows of whichever pack is loaded.",
      "current_usage": "Active only when `w_frameDisc==4 && i<100`: the matched EncountData row index is bumped by 254 within the SAME loaded pack to pick a disc4-specific variant record.",
      "needs_engine_change": true,
      "file_line": "ff9.cs:9250-9255 (inside w_worldGetBattleScenePtr, immediately after the s60 table-hole fix noted in the adjacent comment ff9.cs:9258-9263)",
      "reasoning": "A third, orthogonal hardcoded disc-keyed switch found while reading w_worldGetBattleScenePtr in full -- not one of the two the task named, but same family. It confirms the encounter path has THREE independent disc==1/4 hardcodings stacked (file selector, this offset, plus the disc-agnostic-but-dense area/zone LUTs above), each of which would need its own new branch for a 3rd world to get an analogous 'alternate variant' mechanism; none of it is required just to get baseline encounters (that only needs the file-selector and zone/area LUTs addressed)."
    },
    {
      "name": "WorldPlace / WorldEffect enums (WorldConfiguration's Place/Effect mod-config hooks)",
      "capacity": "WorldPlace: ~64 named members (incl. 4 non-enterable at 0x100+); WorldEffect: 12 named members -- both closed C# enums.",
      "current_usage": "All members map to real, named FF9 locations/effects (Alexandria, Cleyra, FireShrine, SandStorm, ...).",
      "needs_engine_change": true,
      "file_line": "Memoria/World/WorldPlace.cs:1-73; Memoria/World/WorldEffect.cs:1-18; consumed via TryEnumParse in WorldConfiguration.cs:383-413 (LoadWorldEnvironmentDictionaryToken)",
      "reasoning": "Only relevant if a 3rd world needs a NEW named place/effect semantic hook (e.g. 'this world's own destroyed-town toggle') -- the WorldEnvironment.txt `Place`/`Effect` tokens can only reference an EXISTING enum member by name (`args[0].TryEnumParse`), so a genuinely new named concept needs an enum-member engine change. By contrast the Mist/Rain/Light/Title tokens (WorldConfiguration.cs:369-378, 415-612) are NOT enum-keyed -- they're free-form NCalc-conditioned List<> entries -- and remain genuinely open/data-driven for a 3rd world's weather/lighting/rain/banner-timing needs without touching this enum ceiling."
    }
  ],
  "unknowns": [
    "Can a 3rd WorldDisc's 480-cell WMBlock placeholder hierarchy be instantiated purely at runtime via C# (AddComponent<WMBlock>() + setting the public, non-attributed InitialX/InitialY/IsSea fields, WMBlock.cs:243,256-257), or does it require the Unity Editor to author a baked prefab/scene (as the project's own s34-era comment at WMWorld.cs:2069-2074 implies)? I read WMWorld.cs's OnInitialize/BuildBlockArray in full and found zero runtime construction code -- it only enumerates children that already exist -- but I did NOT read WMBlock's Awake()/init sequence or attempt an actual instantiation, so I cannot rule either way. This is the single highest-leverage cheap probe for de-risking Path D: try building a minimal N-cell WMBlock tree at runtime under a fresh Transform and see whether WMWorld's block-loading pipeline (LoadBlock/OnUpdateLoading/the walkmesh raycast) accepts it.",
    "Does AssetManager.Load<T>(path, ...) (used at WMWorld.cs:512 for the per-block visual-dressing prefab, path format 'WorldMap/Prefabs/WorldDisc{disc}/r{row}/Block[x][y]') resolve ANY string against a loose/mod-folder override the same way DictionaryPatch-based field assets do, or does it consult a closed asset-bundle manifest limited to the two shipped bundles (WorldDisc1, WorldDisc4)? I did not read AssetManager.cs this session. If it's override-friendly like field assets, a 3rd disc's per-block dressing prefabs might already be loadable via a loose-file convention with zero engine change (mirroring the s34 pattern), which would substantially de-risk Path D's visual layer even if the WorldDisc placeholder-hierarchy problem above remains open.",
    "ff9mapkit/ff9mapkit/world/worldpack.py's docstring claims 355 total encounter records + 9x12 specials per discmr.img pack (worldpack.py:105-106); I did not independently parse a live discmr.img this session to verify that count, nor did I verify whether Discmr.to_bytes() supports RESIZING a zone's row allocation (vs. strictly in-place same-length edits) -- this determines whether 'the data-driven part is truly free' extends to adding rows, or is capped exactly at the hardcoded w_worldZoneFigure counts as I inferred from ff9.cs alone.",
    "Whether the IDALL bit layout packed into terrain mesh tangent.x (event:2 + area:6 + topograph:6 + flags:2 = 16 bits total, per ff9mapkit/ff9mapkit/world/extract.py:65-87 and m_GetIDArea/m_GetIDTopograph/m_GetIDEvent at ff9.cs:2335-2348) is truly fixed at 16 bits by some OTHER consumer (e.g. a serialization format, a sentinel comparison), or is just conventionally 16 bits because that's what decode_id/encode_id assume -- since tangent.x is a full 32-bit float, widening the area field (to escape w_worldAreaZone's 64-slot density problem) may be far cheaper than I assumed IF no other code path hard-assumes the 16-bit packing. I found one sentinel check (WMBlock.cs:211,232: `mapid != 0x31EE`) that would need re-auditing against any new bit layout, but did not exhaustively search for others.",
    "WMBeeMenu.cs (the World-tab debug menu) has several more `w_frameDisc==1`/`==4` branches (lines 29,129,134,140,153 per grep) that I did not read in full -- likely UI-only (debug menu gating which buttons show), probably low-priority for Path D's engineering plan, but not confirmed to be free of anything load-bearing.",
    "I did not exhaustively grep ff9.cs (11,543 lines total) for every possible per-world array beyond the ones the task named plus what I found incidentally while reading adjacent code (w_naviLocationPos, w_worldAreaZone/Figure/Info, w_fileImagenameServer1/4, the +254 band, the continent-title switch); a targeted second pass (e.g. grepping every `readonly` array declaration in the 10000-10500 static-field block and checking each one's population code) could still surface something I missed."
  ]
}
```

## R6 -- Kit-side (ff9mapkit) disc-count assumptions

```json
{
  "files": [
    {
      "path": "ff9mapkit/ff9mapkit/world/extract.py",
      "disc_handling": "already_generalizes",
      "evidence": "Every function takes disc as an open int (default 1), no {1,4} branch anywhere: read_block(x,y,*,disc:int=1,lod:str='0_1',part:str='terrain',game=None) L299; list_blocks(*,disc:int=1,...) L365; list_object_blocks L328; list_coastal_donors L342; extract_block L448. _worldmap_env(disc:int=1,game=None) L126 builds needle=f'worldmap/disc{disc}/0_1/' L131 -- pure string interpolation over whatever container strings exist in the loaded p0data bundle. Raises ValueError L160 only when NO container matches -- a DATA-availability gate (see unknowns), not a code restriction. block_world_origin/BLOCK_SIZE/decode_id/encode_id (tile-id bit math) are disc-independent already."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/mesh.py",
      "disc_handling": "already_generalizes",
      "evidence": "override_relpath(disc:int,x,y,lod='0_1',part='Terrain') L135 returns f'FF9_Data/WorldMap/Disc{disc}/{lod}/r{y}/Block[{x}][{y}] {part}.ff9mesh' L141 -- exactly the s34 hook path shape, fully N-generic (no {1,4} check). donor_sidecar_relpath L144 same pattern. deploy_override(bm,*,mod_folder,game=None,lod='0_1',part='Terrain') L163 and deploy_donor_sidecar(donor_x,donor_y,*,mod_folder,disc:int,x,y,lod='0_1',game=None) L151 forward disc straight through, never validated against a fixed set. CAVEAT (not a 2-disc hardcode, but an unexamined cross-disc assumption): require_block_in_grid L43-57 enforces ONE global GRID_COLS,GRID_ROWS=24,20 constant (L32, sourced from WMWorld.BuildBlockArray) for every disc uniformly -- the kit has no way to detect if a new world's engine-side block array were a different size."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/discmirror.py",
      "disc_handling": "already_generalizes",
      "evidence": "mirror(mod_folder:str,*,src_disc:int=1,dst_disc:int=4,lod:str='0_1',game=None,dry_run=False,cells=None,log=print) L186-187 and auto_mirror(written,*,mod_folder:str,skip_mirror:bool=False,dst_disc:int=4,log=print) L88 both take disc numbers as plain int params -- 1/4 are only DEFAULTS. Path construction is N-generic: src_root=.../f'Disc{src_disc}'/lod, dst_root=.../f'Disc{dst_disc}'/lod L197-198; _real_parts(disc:int,...) L61 and _parts_identical(blk,part,src_disc:int,dst_disc:int,...) L73 same. auto_mirror derives src_disc purely by regex-parsing whichever 'Disc{n}' path segment the caller's own written-file paths carry (_DISC_SEG_RE=re.compile(r'^Disc(\\d+)$') L58, scan L133-141) -- it does not hardcode which source discs exist. No isinstance/membership check anywhere restricts src_disc/dst_disc to {1,4}. DESIGN CAVEAT (not code): per its own module docstring L1-26, this tool exists specifically because the ENGINE's currentDisc selects between two trees representing the SAME logical overworld at different story points; calling mirror(src_disc=1,dst_disc=<newN>) is mechanically identical to the disc1->disc4 case, but whether 'mirror content into tree N' is even the right operation for a genuinely separate third WORLD (vs. a new disc-state of the existing world) is a design question this file cannot answer."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/worldpack.py",
      "disc_handling": "already_generalizes",
      "evidence": "load_discmr(disc:int=1,game=None) L217 is generic: _CONTAINER_RE='worldmap/wmap/disc{disc}/discmr.img' L40, .format(disc=disc) L223 -- N-generic string, no {1,4} check; raises ValueError L237 only on no match (DATA-availability gate). deploy_discmr/apply_config take NO disc param (operate on an already-loaded Discmr). CAVEAT: the zone/record-table SHAPE is fixed data, not re-derived per disc: _AREA_ZONE (65 entries) and _ZONE_FIGURE (26 entries) L48-51 are constants 'probed from ff9.cs' for disc-1's own table; zone_info()/zone_slice()/area_to_zone() L56-78 apply these SAME fixed constants to whatever disc is passed. The module's own docstring (L74) only ASSERTS 'For disc 4 the same layout holds in disc4/discmr.img' -- not independently re-derived here -- so a third disc's table sharing this exact 355-record/25-zone/65-area shape is an assumption, not a guarantee; if it differed, match()/zone_slice() would return silently-wrong indices rather than error. SEPARATE FINDING (different file, see cli.py entry): the CLI's world-encounters verb hardcodes --disc to choices=[1,4] at cli.py:7955 -- worldpack.py's own functions have no such restriction."
    },
    {
      "path": "ff9mapkit/ff9mapkit/cli.py",
      "disc_handling": "already_generalizes",
      "evidence": "20 world-* verbs' --disc argument is plain `type=int, default=1` with NO choices= restriction (help text is only an informational hint, 'world disc: 1 or 4 (default 1)', never enforced): world-extract L7022, world-deform L7038, world-retarget L7087, world-mesh-export L7113, world-mesh-build L7125, world-texture-palette L7160, world-atlas-catalog L7181, world-terrain L7208, world-reclaim L7236, world-coast L7251, world-placement-* L7524, world-morphs L7546, world-island L7605, world-forest L7627, world-hill L7647, world-mountain L7677, world-water L7725, world-entrance L7774, world-fuse L7878, world-minimap L7914. world-mirror's --src-disc/--dst-disc (L7692-7693) are likewise plain type=int with no choices=. THE ONE EXCEPTION: world-encounters' --disc at L7955 is `type=int, default=1, choices=[1, 4]` ('which disc's discmr.img (default 1; disc 4 has its own late-game table)') -- a genuine, but trivial (one-line), CLI-layer restriction backing worldpack.load_discmr (which itself has no such restriction). This is the single line in the whole CLI that would need editing to expose a third disc's encounter table."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/environment.py",
      "disc_handling": "hardcoded_to_1_4",
      "evidence": "No disc parameter exists anywhere in this module -- not even an open int. The ENGINE's own Environment.txt grammar (per this file's docstring, sourced from WorldConfiguration.cs:93) recognizes a FIXED literal token set: 'line tokens ^(Place|Effect|Mist|Disc4|Rain|Light|Title)' L6. 'Disc4' is a single hardcoded keyword ('force the Mist-Continent mist on/off (Disc4 the same, for disc-4 forms)' L13) -- there is no generic DiscN form in the engine's own parser. The kit mirrors this literally: validate_environment checks `for key in ('mist', 'disc4')` L66-69; build_environment_txt emits `if 'disc4' in cfg ...: lines.append(f'Disc4 [Condition={_cond(cfg[\"disc4\"])}]')` L107-108. This is a binary is-disc-4 toggle, not a disc-selector axis -- there is no way to express 'apply only on world N' for any N other than the one literal keyword. Cannot be generalized on the kit side alone: it mirrors an ENGINE-side literal, so a third world's own environment condition would need a new engine grammar keyword first."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/locate.py",
      "disc_handling": "not_disc_aware",
      "evidence": "No function in this file takes a disc (or world-state) parameter at all. WORLD_EB_CONTAINER = 'eventbinary/world/us/evt_world_world00.eb' L32 (commented 'disc-1 free-roam overworld dispatcher') is a single hardcoded literal container path. _world_eb_bytes(game=None) L121-140, case_to_fields(game=None) L154, case_to_cells(game=None) L197, case_to_blocks(game=None) L223, locate(game=None) L246 all take only `game`. This means the whole 'world-locate' entrance-geography decoder (cell -> dispatch case -> destination field, the mechanism documented L1-19) currently ONLY ever reads WORLD00's table -- it doesn't even cover disc-4's dispatcher or any of the ~12 other known world-state dispatchers (contrast entrance.py's load_all_dispatchers, which discovers all of them by regex), let alone a hypothetical new dispatcher for a third world. Generalizing this file needs a real parameter replacing the hardcoded constant -- genuine rework, not a call-site tweak."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/entrance.py",
      "disc_handling": "already_generalizes",
      "evidence": "The .eb-dispatcher side is genuinely N-generic and data-driven, unlike locate.py: load_all_dispatchers(game=None) L87-120 globs every p0data*.bin and regex-matches `_WORLD_RE = re.compile(r'eventbinary/world/([a-z]{2})/(evt_world_world\\d+)\\.eb')` L84 against EVERY TextAsset container actually present, returning {name: {lang: bytes}} for whatever is found -- no hardcoded count or name list, so a hypothetical new dispatcher asset (e.g. world13) would be picked up automatically. The mesh-side disc:int=1 param (author_entrance L731-732, read_block_stacked L605) follows the same open-int pattern as the rest of world/. TEMPLATE_TAG=0x9895 L38 ('WORLD00's Ice-Cavern (case 4) entrance func -- the proven clone donor') is a fixed bytecode CLONE TEMPLATE, then added to EVERY discovered dispatcher (L13-16 docstring) -- a reasonable fixed 'known-good donor' choice, not a restriction on dispatcher/world count."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/encounter.py",
      "disc_handling": "already_generalizes",
      "evidence": "No disc parameter exists in this file at all -- it operates purely on the .eb world-state axis, already N-generic via entrance.load_all_dispatchers(). deploy_encounter_rate(*,mod_folder,game=None,multiplier=None,set_prob=None,peaceful=False,langs=None,dry_run=False) L116-160 calls `alld = _entrance.load_all_dispatchers(game)` L129 then `for name in sorted(alld):` L135 -- iterates however many dispatchers were actually discovered; a cutscene-state dispatcher (no SET-26 write) is skipped generically via `if not us or not any(True for _ in rate_writes(us))` L137, not via a hardcoded exclusion list of names."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/navimap.py",
      "disc_handling": "already_generalizes",
      "evidence": "composite_world_map(mod_folder:str,*,disc:int=1,lod:str='0_1',game=None,dry_run=False,verbose=True) L338 is an open-int disc param, no {1,4} check. The OUTPUT asset it writes, MAP_SPRITE_REL='FF9_Data/EmbeddedAsset/ui/sprites/world_map_full_all.png' L239, is a SINGLE disc-agnostic minimap image shared by the whole game's UI. Comment L225-234 notes a SEPARATE 'mistcontinent' crop map exists for some disc-4 UI context that this function does NOT currently handle -- flagged as an unknown. WORLD_MAP_EXTENT=(1536.0,1280.0) L237 and the registered art-frame calibration L310-320 are properties of the fixed 24x20-block/64u grid (matches mesh.py's GRID_COLS/GRID_ROWS), not of any particular disc."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/orphangate.py",
      "disc_handling": "already_generalizes",
      "evidence": "default_context_provider(region_cells,*,mod_folder:str,disc:int=1,lod:str='0_1',...) L187 and another disc:int=1 signature L447 both forward disc generically into mesh.override_relpath / world.read_block, no {1,4} restriction."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/interior.py",
      "disc_handling": "already_generalizes",
      "evidence": "Every disc-touching function takes disc as an open int, default 1: census_gate(changed,*,disc:int=1,game=None,log=print,probe=None) L2435; deploy_mountain_parts(res,*,mod_folder:str,disc:int=1,lod:str='0_1',game=None,skip_mirror=False,log=print) L2465; deploy_changed(changed,*,mod_folder:str,disc:int=1,lod:str='0_1',game=None,backup=True,skip_mirror=False,log=print) L2503; _mountain_blob(donor_blocks,*,rock_topos,alcove_box,disc=1,game=None,log=print) L1010. Each forwards disc into extract.read_block / mesh.hidden_block_mesh / mesh.deploy_override / discmirror.auto_mirror -- no {1,4} branch found."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/island.py",
      "disc_handling": "already_generalizes",
      "evidence": "_sea_plane(disc:int=1,game=None) L873, _real_block_parts(blk,*,disc:int=1,lod:str='0_1',game=None) L879, landmass(mod_folder:str,*,...,disc:int=1,lod:str='0_1',game=None,dry_run=False,skip_mirror=False) L894-898 all take disc as an open int forwarded into extract.read_block/transplant.world_tris -- no {1,4} check found."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/islandbeach.py",
      "disc_handling": "already_generalizes",
      "evidence": "build_beach(outline,radii,center,arc,*,ground,land_height,rim,width=2.4,swash=4.0,pins_from=(20,5),disc=1,game=None) L83-84 takes disc as a generic default-1 int; used only to forward into terrain/mesh reads, no {1,4} check."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/coastscan.py",
      "disc_handling": "already_generalizes",
      "evidence": "beach_windows(bx,by,*,disc=1,lod='0_1',game=None) L72, cliff_windows(bx,by,*,disc=1,lod='0_1',game=None) L135, scan_block(bx,by,*,verbs=None,disc=1,lod='0_1',game=None) L267 all take disc generically, forwarding into terrain.world_tris -- no restriction found."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/coastmorph.py",
      "disc_handling": "already_generalizes",
      "evidence": "Every one of its ~14 public builders takes disc as an open int, default 1, with no {1,4} branch: CoastMorphWindow.__init__(...,disc:int=1,...) L114; beach_bump L547; beach_rebuild L1046; beach_slide L2147; band_convert L2968; sand_rebuild L3260; cap_rebuild L3515; cliff_bump L5981; cliff_headland L6024; cliff_bay L6034; cliff_lobes L6047 (plus private helpers _assert_pure_sea4/_freeform_window/_beach_window at L296/463/929). All forward disc into extract.read_block/transplant.world_tris."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/terrain.py",
      "disc_handling": "already_generalizes",
      "evidence": "reshape(mod_folder,*,radius,at=None,seg=None,amount=None,flatten=False,height=None,disc:int=1,falloff='smooth',game=None,dry_run=False,skip_mirror=False) L32-34; coast(mod_folder,*,cells,donor,disc:int=1,lod='0_1',game=None,dry_run=False,skip_mirror=False) L87-88; reclaim(mod_folder,*,cells,disc:int=1,...) L213-216. All open-int, no {1,4} check. Docstrings at L39,95,246 mention auto-mirroring writes to Disc4 -- that's discmirror's DEFAULT behavior, not a restriction on terrain.py's own disc param."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/transplant.py",
      "disc_handling": "already_generalizes",
      "evidence": "world_tris(bx:int,by:int,part:str,*,disc:int=1,lod:str='0_1',game=None) L114, effective_prefab_arm(meshes,*,cell,sidecar_parts,disc:int=1,lod:str='0_1') L2179, _prefab_fallback(need,*,disc,lod,game) L73, _soup_block_mesh(name,cell,tris,*,disc:int,lod:str) L2419 -- all open-int disc params, no {1,4} branch found; this module underlies coastscan/coastmorph/island's own world_tris calls."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/fuse.py",
      "disc_handling": "already_generalizes",
      "evidence": "fuse_layout(mod_folder:str,placements,*,disc:int=1,lod:str='0_1',game=None,allow_overwrite=False,dry_run=False,skip_mirror=False) L119-121 and its helper _existing_overrides(cells,mod_folder:str,*,disc:int,lod:str,game=None) L106 both take disc generically. Docstring L130 mentions the default Disc4 auto-mirror behavior only."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/water.py",
      "disc_handling": "already_generalizes",
      "evidence": "read_shade_grid(sx:int,sy:int,*,disc:int=1,lod:str='0_1',game=None) L464 and read_sea5_tiles(sx:int,sy:int,*,disc:int=1,lod:str='0_1',game=None) L523 are both open-int; docstrings L349,417,584 mention only the default Disc4 auto-mirror step."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/blendio.py",
      "disc_handling": "already_generalizes",
      "evidence": "export_obj(blocks,*,disc:int=1,part='object',lod:str='0_1',out,game=None) L26 and build_from_obj(obj_path,*,into_block,mod_folder:str,disc:int=1,part:str='object',lod:str='0_1',...) L184-187 both take disc as an open int forwarded into extract.read_block / mesh.deploy_override -- no {1,4} restriction. L203 docstring mentions only the default Disc4 auto-mirror behavior."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/palette.py",
      "disc_handling": "already_generalizes",
      "evidence": "sample_donor_faces(disc:int=1,part:str='terrain',*,blocks=None,max_blocks:int=24,game=None) is the module's one disc-taking entry point -- open int, default 1, forwarded into extract.read_block; no {1,4} check found."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/atlas.py",
      "disc_handling": "already_generalizes",
      "evidence": "tile_catalog(part='terrain',*,disc:int=1,out,per_topo=8,thumb=40,game=None) L297-298 is open-int, forwarded to placement/read logic. atlas_override_path(part,*,mod_folder,game=None) L329-331 explicitly notes 'Same layout for all discs' -- the atlas mod-override path (SearchAssetOnDisc, AssetManager.cs:804) is disc-agnostic by construction, not keyed to a disc at all."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/placement.py",
      "disc_handling": "already_generalizes",
      "evidence": "place(meshlist,x,z,y=0.0,*,sky=True) L44 and census(meshlist,*,span=(2.0,62.0,-62.0,-2.0),samples=24,y=0.0) L81 take NO disc parameter at all -- they operate purely on an already-loaded list of (part_name, BlockMesh) tuples, disc-agnostic by construction (one abstraction level above 'which disc'). Genuinely reusable for any world's geometry unchanged."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/grassland.py",
      "disc_handling": "already_generalizes",
      "evidence": "extract_stamps(disc:int=1,*,blocks=None,game=None,cache:bool=True) L355 is an open-int disc param; its cache path is N-generic: f'{_STAMP_CACHE}_disc{disc}.json' L367 (no {1,4} literal). Forwards disc into extract.read_block."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/texgates.py",
      "disc_handling": "uncertain",
      "evidence": "No function in this file takes a disc parameter -- its gates (zero_uv_area_gate, one_window_gate, family_rect_gate, sea_plan_gate, texture_sea_gates, L218-438+) are pure functions over an already-built {(bx,by): [(part,BlockMesh)]} dict, disc-agnostic by construction like placement.py. CAVEAT: one_window_gate's empirical pass-rate thresholds were 'measured 2026-07-25 against READ-ONLY stock disc-1 bytes' (L37-38, citing studies/overworld-topography/out/foldback/texgates_calibration_raw.json) -- calibrated ONLY against disc-1 samples of a handful of real ground families (Cleyra/grass/dunes, L42-44). Whether those thresholds remain valid acceptance criteria for a stylistically different third world's synthesized geometry is unverified in this session -- a real DATA/design risk even though the code itself has no disc restriction."
    },
    {
      "path": "ff9mapkit/ff9mapkit/world/__init__.py",
      "disc_handling": "already_generalizes",
      "evidence": "Docstring-only (7 lines), no executable code. States 'an OFFLINE reader for the disc-1/disc-4 block TERRAIN meshes' L3 -- descriptive of the CURRENT two known worlds, not an enforced restriction; carries no logic to generalize or restrict."
    },
    {
      "path": "ff9mapkit/tests/test_discmirror.py + test_discmirror_auto.py",
      "disc_handling": "uncertain",
      "evidence": "Extensive fixtures use CONCRETE disc=1/disc=4 values throughout (e.g. test_discmirror.py L130-135, L192-195, test_discmirror_auto.py L61-98, L379-498) but NO test anywhere asserts `disc in (1, 4)` as a code-level gate -- grepped for 'if disc'/'disc =='/'disc in'/'disc not in' across ff9mapkit/ff9mapkit/world/*.py and found only discmirror.py:139's `disc_n == dst_disc` (a derived-value comparison against a caller-supplied dst_disc, not a fixed literal). The two-world assumption in these tests is a FIXTURE CHOICE (only two real discs exist to test against today), not a hardcoded validation in the library under test -- new fixtures would need adding for a third disc, but no source rework."
    },
    {
      "path": "ff9mapkit/tests/test_worldpack.py",
      "disc_handling": "already_generalizes",
      "evidence": "L174: `@pytest.mark.parametrize(\"disc\", [1, 4])` -- a data-driven parametrization exercising worldpack.load_discmr against both real discs; this is a list a third value could simply be appended to, not an assertion that disc must be 1 or 4."
    }
  ],
  "unknowns": [
    "Does a genuinely new disc/world tree (e.g. a hypothetical 'Disc5') exist, or CAN exist, as a real Unity asset container in the game's p0data bundles / StreamingAssets at all? Every kit read path (extract._worldmap_env, worldpack.load_discmr, entrance/locate's p0data scans) is code-generic over disc but raises ValueError the moment no matching container string is found -- the kit cannot create this asset data itself. discmirror.py's own docstring states 'only WorldDisc1/WorldDisc4 prefabs exist' as an engine/Unity fact; whether the engine's WorldMeshOverride/AssetManager path lookup for WorldMap/Disc{D}/... is itself open to any D or hardcoded to {1,4} is an ENGINE-side question outside this session's scope (likely owned by a parallel engine-side investigation) and blocks everything downstream if closed.",
    "Is the fixed 24x20 block grid (mesh.py GRID_COLS=24,GRID_ROWS=20, sourced from WMWorld.BuildBlockArray) genuinely engine-wide (one array size for ALL discs), or could a new third world need a different grid shape? Confirmed only that disc-1 and disc-4 both match this constant per the module's own comment (mesh.py:25-31) -- not independently re-verified against disc-4's own bytes in this session, and definitely not verifiable for a hypothetical new world without engine-side confirmation.",
    "Does discmr.img's zone/record-table SHAPE (355 records, 25 zones, 65 areas, encoded as fixed constants _AREA_ZONE/_ZONE_FIGURE in worldpack.py) actually hold for disc-4's real discmr.img, and would it hold for a third world's? worldpack.py's own docstring only ASSERTS disc-4 shares the layout (worldpack.py:74); this session did not parse disc-4's actual discmr.img bytes to confirm, and a third disc's table could differ in ways that would make match()/zone_slice() return silently-wrong record indices rather than raise.",
    "Is 'mirror content from disc1 into the new tree' (discmirror.py's actual, only operation) even the right deploy strategy for a genuinely separate third WORLD, as opposed to a new disc-state variant of the SAME existing overworld map? discmirror exists specifically to solve currentDisc-driven duplicate-asset-tree sync for ONE logical map; a bona fide new/separate world may need an entirely different content-authoring strategy that this file's mechanism doesn't address -- a product/design question, not a code question.",
    "Does the native minimap have a second disc-4-specific asset (the 'mistcontinent' crop mentioned in navimap.py's comment L225-234) with engine-side hardcoding to disc 4 specifically, and would a third world need its own such crop, or would the existing world_map_full_all.png (which navimap.py DOES already composite disc-generically) suffice? navimap.py currently only touches the latter and does not handle the mistcontinent crop at all.",
    "Is the engine's Environment.txt parser (WorldConfiguration.cs, referenced only via docstring in environment.py, not read directly this session) capable of being extended with a new 'World<N>' or similar literal token for a third world's own weather/mist condition, or is 'Disc4' baked in more deeply than a simple grammar table? This determines whether environment.py's hardcode is a one-line engine parser extension away from generalizing, or something harder.",
    "Are the 13 known world-state dispatchers (EVT_WORLD_WORLD00..12, EventDB[9000..9012], per CLAUDE.md flagged as a RESERVED id hole) a truly fixed engine allocation, or could a genuinely new dispatcher (e.g. world13) for a third world's own on-foot/vehicle states be registered? entrance.py's load_all_dispatchers would pick up such an asset automatically via its regex if it existed and were reachable, but whether the engine's own state-machine could ever transition into a new EventDB id outside the reserved 9000-9012 hole is unverified here.",
    "texgates.py's one_window_gate acceptance thresholds were empirically calibrated ONLY against disc-1 stock ground samples (Cleyra/grass/dunes families) -- would those thresholds need re-calibration against a stylistically different third world's synthesized terrain, or do they generalize? Not verified this session; flagged as a real risk despite the code itself carrying no disc restriction.",
    "This entire investigation was a STATIC READ of the Python source -- no code was executed against the live game install this session (no UnityPy probe run). None of the 'already_generalizes' findings were empirically confirmed by actually calling e.g. extract.read_block(disc=4,...) or entrance.load_all_dispatchers() against the real StreamingAssets to prove the claimed data (13 dispatchers, disc-4's container naming, the zone-table shape match) is really there and really parses the way the source implies. A cheap runtime probe against the real install (confirming what disc-4's actual containers/dispatcher count/table shape look like) should be the FIRST de-risking step before any third-world engineering investment, since several 'already_generalizes' verdicts are conditional on the DATA existing, not just the code accepting the parameter."
  ]
}
```
