"""M1b STEP 7 -- STAGE (do NOT deploy) the GEO 6201 mint for the s54 hybrid's skinned Thomas.

Mirrors build_thomas.py's proven GEO-mint precedent (6200 = GEO_MON_B0_M200) at the NEXT id:
    id 6201  ->  GEO_MON_B0_M201  (M201 = 6201 - MINT_BAND_START 6000; type "MON" -> ModelType 3)
so it never collides with the existing 6200 flight-path Thomas mint. Verified against the kit
(ff9mapkit.models.mint.resolve_mint) AND the engine (ModelFactory.GetModelType/GetGEOID + ModelImporter).

Staged tree (a deploy-ready mod-folder fragment; the arming agent copies it into the live mod folder):
    m1b_stage/StreamingAssets/Assets/Resources/Models/3/6201/6201.fbx   <- the skinned raw-scale FBX
    m1b_stage/StreamingAssets/Assets/Resources/Models/3/6201/Thomas_d.png  <- the original texture (unmodified)
    m1b_stage/DictionaryPatch.txt                                        <- "3DModel 6201 GEO_MON_B0_M201"
    m1b_stage/ARMING.txt                                                 <- the exact [SfxHybrid] ini + ModelPath

Binary-SAFE copies (never text-decode a binary FBX/PNG). Provenance: this is committable CODE; it copies
local SCRATCH assets (the third-party Thomas FBX/PNG + our own skinned export) and embeds no game bytes.

Run:  py stage_mint.py
"""
import hashlib
import shutil
import sys
from pathlib import Path

# ---- inputs (local SCRATCH only) ----
SKINNED_FBX = Path(r"C:/gd/SCRATCH/summon-transplant/thomas_skinned.fbx")   # the engine copy (raw scale)
TEX_SRC = Path(r"C:/gd/SCRATCH/thomas/Thomas_d.png")                        # the original, unmodified texture
STAGE_ROOT = Path(r"C:/gd/SCRATCH/summon-transplant/m1b_stage")

# ---- the mint identity (kit + engine verified) ----
GEO_ID = 6201
GEO_NAME = "GEO_MON_B0_M201"
TYPE_INT = 3                       # "MON" -> ModelType.mon == 3 (ModelFactory.GetModelType)
REL_MODEL_DIR = Path("StreamingAssets/Assets/Resources/Models") / str(TYPE_INT) / str(GEO_ID)
DIRECTIVE = f"3DModel {GEO_ID} {GEO_NAME}"

# s54 patch surface (READ from memoria-patches/s54-sfx-hybrid-drive.patch, section 2.1):
#   [SfxHybrid] ModelPath accepts a FileList-style GEO name resolved through ModelFactory.CreateModel.
#   ModelFactory.GetGEOID(name) -> FF9BattleDB.GEO.TryGetKey(name) (populated by the 3DModel directive) ->
#   6201 -> "Models/3/6201/6201.fbx". So the ModelPath value = the GEO NAME below.
MODELPATH_VALUE = GEO_NAME


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fail(msg):
    print("STAGE FAILED: " + msg)
    sys.exit(1)


# ---- preflight ----
if not SKINNED_FBX.is_file():
    fail(f"skinned FBX missing: {SKINNED_FBX} (run skin_thomas.py first)")
if SKINNED_FBX.open("rb").read(20) != b"Kaydara FBX Binary  ":
    fail(f"{SKINNED_FBX} is not a binary FBX")
if not TEX_SRC.is_file():
    fail(f"texture missing: {TEX_SRC}")
if TEX_SRC.open("rb").read(8) != b"\x89PNG\r\n\x1a\n":
    fail(f"{TEX_SRC} is not a PNG")

# verify the FBX material references the texture by its bare filename (path_mode STRIP). The engine's
# ModelImporter reads materials[i].TexturePath and loads it from the model folder, so the staged PNG must
# match that name. We grep the raw FBX bytes for the ASCII "Thomas_d.png" reference.
fbx_bytes = SKINNED_FBX.read_bytes()
if b"Thomas_d.png" not in fbx_bytes:
    fail("the skinned FBX does not reference 'Thomas_d.png' -- the material/texture binding did not survive "
         "the export; re-check skin_thomas.py's material handling before staging")
print("preflight OK: FBX is binary + references 'Thomas_d.png'; texture PNG present")

# ---- stage ----
if STAGE_ROOT.exists():
    shutil.rmtree(STAGE_ROOT)
model_dir = STAGE_ROOT / REL_MODEL_DIR
model_dir.mkdir(parents=True, exist_ok=True)

fbx_dest = model_dir / f"{GEO_ID}.fbx"
tex_dest = model_dir / "Thomas_d.png"
shutil.copyfile(SKINNED_FBX, fbx_dest)           # binary-safe
shutil.copyfile(TEX_SRC, tex_dest)               # binary-safe
assert fbx_dest.read_bytes() == fbx_bytes, "fbx copy mismatch"
assert tex_dest.read_bytes() == TEX_SRC.read_bytes(), "tex copy mismatch"

dp = STAGE_ROOT / "DictionaryPatch.txt"
dp.write_text(DIRECTIVE + "\n", encoding="utf-8", newline="\n")

arming = STAGE_ROOT / "ARMING.txt"
arming.write_text(
    "s54 HYBRID DRIVE -- ARM THE THOMAS SWAP (Bahamut donor, effect 227)\n"
    "==================================================================\n\n"
    "1) DEPLOY this fragment into the live mod folder (merge, do not replace):\n"
    f"     {REL_MODEL_DIR}/{GEO_ID}.fbx   +   {REL_MODEL_DIR}/Thomas_d.png\n"
    "   and APPEND to that folder's DictionaryPatch.txt (idempotent -- only if absent):\n"
    f"     {DIRECTIVE}\n"
    "   (a NEW 3DModel id registers only at launch -> RELAUNCH after first deploy.)\n\n"
    "2) Memoria.ini [SfxHybrid] block (relaunch to apply):\n"
    "     [SfxHybrid]\n"
    "     Enabled=1\n"
    "     EffectId=227\n"
    f"     ModelPath={MODELPATH_VALUE}\n"
    "     HideNative=1\n"
    "     HideMask=0x3\n"
    "     NodeCount=93\n"
    "     ApplyColumnScale=0\n"
    "     Log=1        ; first cast only, then set 0\n\n"
    f"   ModelPath = {MODELPATH_VALUE}  (the GEO name; ModelFactory.CreateModel -> GetGEOID via the 3DModel\n"
    f"   registry -> {GEO_ID} -> Models/{TYPE_INT}/{GEO_ID}/{GEO_ID}.fbx). This is the exact value to write.\n\n"
    "3) Cast Bahamut on the bench (field 30300, id 194). Expect: the tank engine, posed to the dragon's\n"
    "   live 93-bone motion (a rigid train deforming on the dragon skeleton -- the intended effect), native\n"
    "   body hidden. See studies/.../m1b/ + m0/S54-DRAFT.md sections 3-5 for the go/no-go gates + risks.\n",
    encoding="utf-8", newline="\n")

print("\nSTAGED under:", STAGE_ROOT)
print(f"  {fbx_dest.relative_to(STAGE_ROOT)}   sha256={sha(fbx_dest)[:16]}...  ({fbx_dest.stat().st_size} B)")
print(f"  {tex_dest.relative_to(STAGE_ROOT)}   sha256={sha(tex_dest)[:16]}...  ({tex_dest.stat().st_size} B)")
print(f"  DictionaryPatch.txt: {DIRECTIVE!r}")
print(f"  ARMING.txt written")
print(f"\ns54 [SfxHybrid] ModelPath = {MODELPATH_VALUE}")
print("STAGE DONE (staged only -- NOT deployed).")
