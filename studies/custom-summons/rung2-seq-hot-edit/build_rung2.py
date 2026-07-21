"""Custom Summons -- rung 2: the shared-folder .seq HOT-EDIT probe.

Overrides the STOCK Bahamut cinematic's outer choreography file
(``Data/SpecialEffects/ef227/PlayerSequence.seq``) with a mod-folder copy carrying exactly two
edits, to prove -- on the ALREADY-RUNNING game, no relaunch, no redeploy -- that:

  1. a mod-folder ``.seq`` override is read in preference to the stock file
     (``AssetManager.LoadString`` walks ``FolderNames`` high-to-low; ``FF9CustomMap`` is index 0
     in the user's live ``Memoria.ini`` -> highest priority);
  2. the file is re-parsed FRESH on every single cast (no cache anywhere in this code path for a
     plain numeric ``VfxIndex`` ability -- see the recon citations below), so editing it while the
     game sits open and simply RE-CASTING is a strictly faster loop than ``~`` field-reload;
  3. an inserted ``PlaySound`` line resolves and plays from a hand-edited ``.seq``.

THE TWO EDITS (both source-cited in ``studies/custom-summons/PLAN.md`` §5 rung 2 and the rung-2
recon transcripts this script was built from):

  (a) WAIT RETIME -- the file's one unconditional numeric-``Time`` tween:
        SetBackgroundIntensity: Intensity=0 ; Time=12          (stock)
        SetBackgroundIntensity: Intensity=0 ; Time=45          (edited, +33 ticks ~= +2.2s at the
                                                                 user's live BattleTPS=15)
      This line sits at the MAIN thread level (unconditional). The file's other two numeric-Time
      lines (the two `Turn:...Time=5` / move-forward-back pairs) are BOTH gated behind
      `StartThread` conditions that are FALSE for this bench's ability (AllEnemy target, player
      caster) -- editing those would be a silent no-op, not a smaller change. Do not touch them.

  (b) PLAYSOUND INSERTION -- a brand-new first executable line, before anything else runs:
        PlaySound: Sound=103 ; SoundType=SoundEffect ; Volume=1.0
      id 103 = stock "Menu Select" (Sounds02/SE00/se000001, AudioResources.cs:235) -- a positively
      IDENTIFIED, already-registered stock blip (no minting, no relaunch needed to hear it), chosen
      over the seq-recon's own `Sound=1110` alternative precisely because 1110's content was never
      confirmed (its own open_risks flagged this) while 103 was live-extracted and named via the
      kit's `sfx-list` CLI. This is the one place the two recon reports actively disagreed on WHICH
      stock id to use for the immediate no-relaunch proof; 103 is the better-verified pick and is
      what this script ships.

Track B (mint-now-arms-later, per the sound recon's split-track design): this script ALSO stages a
freshly minted, wholly-synthetic probe chime as a new SFX id (100000, the first id in the kit's sfx
mint band) via `sound.mint_song(..., kind="sfx")`. That id is NOT wired into the .seq by this
script -- SoundMetaData's id table loads once at process start (SoundLib.LazyLoadSoundResources's
`hasLoadedSoundResources` latch) so a brand-new registered id cannot go live on the ALREADY-RUNNING
game; it only arms on the user's NEXT relaunch (whenever that happens, for any reason -- do not wait
for it). Staging it now means the asset is deployed and ready; closing the "does a MINTED id resolve
from inside a .seq PlaySound line" question is a follow-up, done after that relaunch, not gated on
this rung.

PROVENANCE: the edited PlayerSequence.seq this script writes is a modified copy of Square-Enix's own
shipped file -- SE-derived content, and is therefore NEVER written into the repo. This script is the
committable source of truth (regenerates the edit from the user's own install every run); the ONLY
record of the edit is the unified diff this script prints (and the edit-spec in this docstring). The
output lands directly in the LIVE mod folder (``<game>/FF9CustomMap/...``), never under
``studies/``. The minted probe chime is 100% synthetic (a stdlib sine tone, zero SE bytes) but is
also written straight to the live mod folder, not committed, to keep this directory to exactly the
three deliverable files.

Run from anywhere (game may be OPEN -- no relaunch, no redeploy needed for the .seq half):

    py studies/custom-summons/rung2-seq-hot-edit/build_rung2.py

Then: re-enter a battle on bench field 30300 and recast "Bahamut Cinema" from Iviv's Spark command.
See README.md for the full expect/failure-mode table and the revert instructions
(``revert_rung2.py``).
"""
from __future__ import annotations

import difflib
import hashlib
import math
import struct
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/rung2-seq-hot-edit -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import config, fsutil, sound            # noqa: E402

# --------------------------------------------------------------------------- the .seq edit
EF_ID = 227                                 # Bahamut__Full's effect folder (SpecialEffect.cs:99)
SEQ_REL_PATH = f"StreamingAssets/Data/SpecialEffects/ef{EF_ID:03d}/PlayerSequence.seq"

# The exact sha256 of the stock file this script (and both recon passes) read. If the user's
# install has a different Memoria/mod version with a changed ef227, this differs and we refuse to
# guess at an edit against unknown content -- the drift guard.
EXPECTED_SHA256 = "4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63"

OLD_TIME_LINE = "SetBackgroundIntensity: Intensity=0 ; Time=12\r\n"
NEW_TIME_LINE = "SetBackgroundIntensity: Intensity=0 ; Time=45\r\n"
FIRST_EXEC_LINE = "WaitAnimation: Char=Caster\r\n"      # insertion point: BEFORE this line's FIRST occurrence
PLAYSOUND_LINE = "PlaySound: Sound=103 ; SoundType=SoundEffect ; Volume=1.0\r\n"

# --------------------------------------------------------------------------- the minted-sound stage (Track B)
SFX_KIND = "sfx"
SFX_FIXED_ID = 100000                       # sound.MINT_ID_BASE["sfx"] -- first free id in a fresh manifest
SFX_RESOURCE_ID = "Sounds02/SE00/rung2chime"


class DriftError(RuntimeError):
    """The stock file's bytes don't match what this script was built against."""


def apply_edits(stock_text: str) -> str:
    """Apply exactly the two documented edits to the stock ``.seq`` text. Raises ``DriftError`` if
    either anchor line is missing (the stock file has changed shape since this script was written)."""
    lines = stock_text.splitlines(keepends=True)

    try:
        idx = lines.index(OLD_TIME_LINE)
    except ValueError:
        raise DriftError(
            f"expected line {OLD_TIME_LINE!r} not found in the stock file -- "
            "its shape has changed since this script's edits were derived; abort rather than guess"
        ) from None
    lines[idx] = NEW_TIME_LINE

    try:
        insert_at = lines.index(FIRST_EXEC_LINE)   # first occurrence only
    except ValueError:
        raise DriftError(
            f"expected line {FIRST_EXEC_LINE!r} not found in the stock file -- "
            "its shape has changed since this script's edits were derived; abort rather than guess"
        ) from None
    lines.insert(insert_at, PLAYSOUND_LINE)

    return "".join(lines)


def stock_seq_path(game_path: Path) -> Path:
    return game_path / SEQ_REL_PATH


def build_seq_override(mod_root: Path, game_path: Path) -> dict:
    """Read the stock ``ef227/PlayerSequence.seq``, verify its hash, apply the two edits, and write
    the result to the mod-folder override path (created fresh -- the folder doesn't exist yet in a
    stock install). Idempotent: re-running always re-derives from the untouched stock file and
    overwrites the override with the identical bytes."""
    src = stock_seq_path(game_path)
    if not src.exists():
        raise FileNotFoundError(f"stock file not found: {src}")
    raw = src.read_bytes()
    got_hash = hashlib.sha256(raw).hexdigest()
    if got_hash != EXPECTED_SHA256:
        raise DriftError(
            f"{src} sha256 {got_hash} != expected {EXPECTED_SHA256} -- "
            "the stock file differs from what the rung-2 recon read; refusing to apply blind edits. "
            "Re-derive the edit lines against the new content before re-running."
        )

    stock_text = raw.decode("utf-8")
    edited_text = apply_edits(stock_text)
    edited_bytes = edited_text.encode("utf-8")

    dest = mod_root / SEQ_REL_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_bytes(dest, edited_bytes)

    # verify the write landed byte-exact (feedback-verify-the-cache-write-lands)
    readback = dest.read_bytes()
    if readback != edited_bytes:
        raise RuntimeError(f"write verification failed at {dest} -- readback != what we wrote")

    diff = "".join(difflib.unified_diff(
        stock_text.splitlines(keepends=True), edited_text.splitlines(keepends=True),
        fromfile=f"stock/{SEQ_REL_PATH}", tofile=f"FF9CustomMap/{SEQ_REL_PATH}",
    ))
    return {
        "stock_path": str(src), "stock_sha256": got_hash,
        "override_path": str(dest), "override_sha256": hashlib.sha256(edited_bytes).hexdigest(),
        "diff": diff,
    }


# --------------------------------------------------------------------------- the minted probe chime
def _tiny_chime_wav(path: Path, secs: float = 0.4, sr: int = 22050, freq: float = 880.0) -> None:
    """A 100% synthetic sine-wave WAV (stdlib wave+struct+math, zero SE bytes -- the repo's own
    test-fixture idiom, `ff9mapkit/tests/test_sound.py:_tiny_wav`), with a short fade in/out so the
    encoded ogg doesn't click. This is the ffmpeg INPUT; `sound.mint_song` transcodes it to Vorbis."""
    n = int(sr * secs)
    fade = max(1, int(sr * 0.03))     # 30ms fade in/out
    frames = bytearray()
    for i in range(n):
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = (n - i) / fade
        sample = int(9000 * env * math.sin(2 * math.pi * freq * i / sr))
        frames += struct.pack("<h", sample)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))


def stage_minted_sound(mod_root: Path, game_path: Path) -> dict:
    """Mint the rung-2 probe chime as a fresh sfx id (Track B: staged now, arms on the user's NEXT
    relaunch -- SoundMetaData's id table loads once at process start, so this can NOT go live on the
    already-running game). Idempotent: re-running detects the id/resource already staged and
    no-ops rather than erroring or minting a second id."""
    dest_ogg = mod_root / sound.override_rel_path(SFX_RESOURCE_ID)
    base = sound.base_entries(mod_root, SFX_KIND, game=game_path)
    existing = next((e for e in base if e["id"] == SFX_FIXED_ID), None)

    if existing is not None and existing["resource_id"] != SFX_RESOURCE_ID:
        raise RuntimeError(
            f"sfx id {SFX_FIXED_ID} is already claimed by {existing['resource_id']!r} in "
            f"{sound.manifest_override_path(mod_root, SFX_KIND)} -- refusing to clobber it"
        )

    if existing is not None and dest_ogg.exists():
        return {"minted": False, "already_staged": True, "song_id": SFX_FIXED_ID,
                "resource_id": SFX_RESOURCE_ID, "path": str(dest_ogg),
                "manifest": str(sound.manifest_override_path(mod_root, SFX_KIND))}

    with tempfile.TemporaryDirectory(prefix="ff9mk-rung2-") as td:
        wav = Path(td) / "rung2_probe_chime.wav"
        _tiny_chime_wav(wav)
        if existing is not None:
            # manifest row already present (a prior partial run) but the ogg is missing -- just
            # re-encode, don't touch/duplicate the manifest.
            sound.encode_ogg(wav, dest_ogg)
            result = {"minted": False, "already_staged": True, "song_id": SFX_FIXED_ID,
                      "resource_id": SFX_RESOURCE_ID, "path": str(dest_ogg),
                      "manifest": str(sound.manifest_override_path(mod_root, SFX_KIND))}
        else:
            result = sound.mint_song(wav, mod_root, kind=SFX_KIND, new_id=SFX_FIXED_ID,
                                     resource_id=SFX_RESOURCE_ID, game=game_path)
    return result


def main() -> int:
    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)   # FF9CustomMap -- the bench's own mod folder

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print()

    try:
        seq_result = build_seq_override(mod_root, game_path)
    except DriftError as e:
        print(f"DRIFT GUARD TRIPPED -- refusing to write an edit against unexpected content:\n  {e}",
              file=sys.stderr)
        return 1

    print("=== .seq override (Track A -- immediate, no relaunch) ===")
    print(f"stock sha256    : {seq_result['stock_sha256']}  (expected {EXPECTED_SHA256})")
    print(f"stock file      : {seq_result['stock_path']}")
    print(f"override written: {seq_result['override_path']}")
    print(f"override sha256 : {seq_result['override_sha256']}")
    print()
    print("--- unified diff (the ONLY record of the edit -- can't commit SE-derived content) ---")
    print(seq_result["diff"])

    sfx_result = stage_minted_sound(mod_root, game_path)
    print("=== minted probe chime (Track B -- staged now, arms on the NEXT relaunch) ===")
    if sfx_result.get("already_staged"):
        print(f"already staged  : sfx id {sfx_result['song_id']} = {sfx_result['resource_id']}")
    else:
        print(f"minted sfx id   : {sfx_result['song_id']} = {sfx_result['resource_id']} (minted={sfx_result.get('minted')})")
    print(f"ogg path        : {sfx_result['path']}")
    print(f"manifest        : {sfx_result.get('manifest')}")
    print("NOTE: this id is NOT referenced by the .seq yet -- SoundMetaData loads once at process")
    print("      start, so a fresh id can't go live on the already-running game. Wire it in with")
    print("      `PlaySound: Sound=100000` AFTER the user's next relaunch (any reason), then recast.")
    print()

    vol = sound.ini_volume("sfx", game=game_path)
    if vol == 0:
        print(f"WARNING: Memoria.ini SoundVolume=0 -- SFX are MUTED; a silent recast would be a false")
        print("         negative, not proof the mechanism failed. Raise SoundVolume before testing.")
    else:
        print(f"Memoria.ini SoundVolume = {vol!r} (governs both PlaySound lines above; SFX, not Music)")

    print()
    print("Next: re-enter a battle on bench field 30300 (game already running -- no relaunch, no")
    print("redeploy) and recast \"Bahamut Cinema\" from Iviv's Spark command. See README.md for the")
    print("full expect/failure-mode table. Revert with revert_rung2.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
