#!/usr/bin/env python3
"""RUNG 8 -- ASSEMBLE THE NIMBRA BENCH, staged, with the live install untouched.

    py studies/custom-summons/rung8-epic/bench/build_rung8_bench.py --clean --check

WHAT THIS IS. The four build lanes (creature / sequence+kit / audio / this one) each own their own bytes.
This script is the only place they meet: it drives the REAL productized code paths -- ``build.build_mod``
for the field + ability, ``summons.deploy.emit_overlay`` for the ``[[summon]]`` block, ``sound.mint_song``
for the three minted sfx ids -- into ONE mod folder under ``../stage/final/``, then re-reads every emitted
byte and checks it. Nothing here is a mock and nothing here is hand-written: if a file lands in
``stage/final/FF9CustomMap/`` it is what a live deploy would write, produced by the same function.

THE THREE DEPLOY STEPS IT MIRRORS (see ../RUNBOOK.md -- the orchestrator runs those against the install):

    1. `tools/deploy_field.py bench/rung8.field.toml --id 30301`   -> the field + the "Nimbra" ability
    2. `ff9mapkit summon-deploy --from-toml bench/rung8.field.toml` -> ef080/ + ef091/ (THE PAIR) + the GEO
       6400 mint
    3. the audio mint (100001-100003)                              -> the .ogg files + the manifest override

Run in that order, because step 1 is a WHOLESALE field build (it owns DictionaryPatch.txt) and steps 2/3
append to it. This script runs them in that same order for exactly that reason.

IT NEVER TOUCHES THE GAME.
  * the field build reads the install's CSV/text tables (read-only) and writes only under ``--out``;
  * the summon emit runs with ``game=None`` -- an AUTHORED cast reads no donor ``.seq``, no ``ef###.bytes``,
    and needs no install at all;
  * the audio mint runs with ``set_priority=False``, so ``Memoria.ini`` is never written (the real deploy
    needs ``[Audio] PriorityToOGG = 1``; the runbook says so out loud). It DOES read the install's stock
    ``SoundEffectMetaData.txt`` because the override REPLACES that table and must therefore carry all of
    it -- read-only, and cached in the system temp dir, never in the install.

THE PAIR (2026-07-24, the short/full roll round). ONE ``[[summon]]`` block now stages TWO self-contained
effect folders from ONE shared model + clip pool: ef080 = THE FULL (vfx1, ~23.0s) and ef091 = THE WHISPER
(vfx2, ~9.3s, byte-identical to the live install). The AbilityFeatures roll that picks between them is
ability-DISCRIMINATED (``roll_command`` AND ``roll_ability``) because Iviv's minted command 46 hosts FOUR
abilities and a command-wide roll would flip the other three onto their own Vfx2. See section 4 below
("THE ROLL") for the artifact this script checks.

Exit code 0 = every check green.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent           # .../rung8-epic/bench
RUNG8 = HERE.parent                              # .../rung8-epic
REPO = RUNG8.parents[2]                          # <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))

from ff9mapkit import sound                      # noqa: E402
from ff9mapkit.summons import deploy as D        # noqa: E402
from ff9mapkit.summons import seqlint as SL      # noqa: E402

BENCH_TOML = HERE / "rung8.field.toml"
AUDIO_DIR = RUNG8 / "audio"
AUDIO_STAGE = RUNG8 / "stage" / "audio"
MOD_NAME = "FF9CustomMap"

#: the three minted cues, mirrored from the audio lane's own module constants (imported, not retyped, so
#: an id or resource-id edit over there cannot silently desync from the ``.seq`` that plays them).
AUDIO_MODULES = ("make_nimbra_drone", "make_nimbra_whispers", "make_nimbra_strike")

#: THE PAIR (2026-07-24, the short/full roll round) -- per-cast two-clock arithmetic, restated here as the
#: integration ASSERTION rather than prose. FULL and SHORT are two INDEPENDENT effect folders/timelines;
#: never share one constant pair (that was the addendum's own law for the [[summon]] block, mirrored here).
FULL_PRIVATE_EF = 80            # THE FULL -- rung8.field.toml's `private_ef` (STORYBOARD 6.1's spare)
FULL_PLAY_SFX_TICK = 55         # the fixed wait before PlaySFX (FULL-STORYBOARD 4.1)
FULL_WINDOW = 260               # PINNED to ../nimbra_full.seq's WaitSFXDone beat (FULL-STORYBOARD 4.1/4.3)
FULL_DRAIN_TICK = 315           # FULL_PLAY_SFX_TICK + FULL_WINDOW

SHORT_PRIVATE_EF = 91           # THE WHISPER -- the live install's own folder; the re-emit must match it
SHORT_PLAY_SFX_TICK = 25        # the ORIGINAL STORYBOARD 11.2 arithmetic -- now the short half's own
SHORT_WINDOW = 110
SHORT_DRAIN_TICK = 135          # SHORT_PLAY_SFX_TICK + SHORT_WINDOW

GEO_ID = 6400                   # shared: ONE model, ONE clip pool (60000-60003) -- both casts reference it
ABILITY = "Nimbra"
ROLL_COMMAND = 46               # Iviv's minted command1 ("Spark") -- section 4 (THE ROLL) asserts the
                                 # field build's OWN Commands.csv output actually resolved it to this id,
                                 # not just that the toml claims it -- a band-order change must fail loud.
ROLL_ABILITY = 195              # Nimbra's minted ability id -- THE DISCRIMINATOR (roll_ability): command
                                 # 46 hosts FOUR abilities, so CommandId alone cannot tell them apart.


# --------------------------------------------------------------------------------------- lane resolution
def load_block() -> dict:
    """The bench toml's first ``[[summon]]`` block with every relative path resolved against the TOML's own
    directory -- the same rule ``lint``/``build`` apply via ``base_dir``, and the same rule
    ``summon-deploy --from-toml`` applies via ``cli._rebase_summon_paths`` (mirrored here key-for-key, PLUS
    ``short_sequence`` -- THE PAIR's second authored cast, which needs the identical treatment ``sequence``
    already gets. ``manifest``/``short_manifest`` are bare file names -- deliberately left untouched, same
    as ``cli._rebase_summon_paths`` never touches them)."""
    block = dict(tomllib.loads(BENCH_TOML.read_text(encoding="utf-8"))["summon"][0])

    def fix(p):
        q = Path(str(p))
        return str(q if q.is_absolute() else (HERE / q).resolve())

    for key in ("model", "sequence", "short_sequence"):
        block[key] = fix(block[key])
    for key in ("clips", "particles"):
        block[key] = [fix(v) for v in block[key]]
    return block


def audio_cues() -> list:
    """``[(module, channels, wav_path)]`` for the three cues, read from the AUDIO lane's own modules."""
    sys.path.insert(0, str(AUDIO_DIR))
    import importlib
    out = []
    for name in AUDIO_MODULES:
        mod = importlib.import_module(name)
        out.append((mod, 2 if "whispers" in name else 1, AUDIO_STAGE / "wav" / f"{mod.NAME}.wav"))
    return out


# --------------------------------------------------------------------------------------- the three steps
def step_field(mod_root: Path) -> dict:
    """Step 1 -- the field + the minted "Nimbra" ability, through the real ``build_mod``.

    Run as a SUBPROCESS on purpose: ``build_mod`` compiles a C# scripts DLL for Iviv's "Soul Leech"
    (``script = {template = "drain_hp"}``) and shells out to the .NET toolchain, and a failure there should
    surface as this step's stderr rather than as a half-imported module state in ours."""
    cmd = [sys.executable, "-m", "ff9mapkit", "build", str(BENCH_TOML), "--out", str(mod_root)]
    p = subprocess.run(cmd, cwd=str(KIT), capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"field build FAILED (rc={p.returncode}):\n{p.stdout}\n{p.stderr}")
    return {"stdout": p.stdout.strip().splitlines(), "warnings":
            [ln for ln in p.stderr.splitlines() if ln.startswith("warning:")]}


def step_summon(mod_root: Path, work_dir: Path) -> dict:
    """Step 2 -- the ``[[summon]]`` block, through the real overlay emitter (``game=None``). ONE call now
    stages BOTH effect folders (THE PAIR) plus the AbilityFeatures roll -- there is no separate short-half
    step; ``emit_overlay`` owns that internally once ``short_sequence`` is set."""
    return D.emit_overlay(load_block(), mod_root, None, work_dir=work_dir)


def step_audio(mod_root: Path, *, offline: bool) -> dict:
    """Step 3 -- mint sfx 100001-100003 into the mod folder.

    ``sound.mint_song`` is the real minting lane; ``set_priority=False`` keeps ``Memoria.ini`` out of it.
    The masters come from ``../stage/audio/wav/`` (the audio lane's build output) -- if they are not there,
    the audio lane has not been run and this says so rather than inventing silence.

    ``offline=True`` skips the install read (the stock ``SoundEffectMetaData.txt``) and writes an override
    manifest carrying ONLY our three rows. That file would be WRONG to deploy -- the override REPLACES the
    stock table, so a partial one deletes every stock sound effect -- and it is therefore named
    ``.PARTIAL`` and reported as such. It exists so the pipeline is checkable on a box with no install."""
    cues = audio_cues()
    missing = [str(w) for _m, _c, w in cues if not w.is_file()]
    if missing:
        raise SystemExit("the audio lane has not been built -- missing master WAV(s):\n  "
                         + "\n  ".join(missing)
                         + "\n  run: py studies/custom-summons/rung8-epic/audio/build_audio.py")
    minted = []
    if offline:
        entries = []
        for mod, _ch, wav in cues:
            dest = mod_root / sound.override_rel_path(mod.RESOURCE_ID)
            sound.encode_ogg(wav, dest, quality=6)
            entries.append({"id": mod.SOUND_ID, "resource_id": mod.RESOURCE_ID, "type": "SoundEffect"})
            minted.append({"song_id": mod.SOUND_ID, "resource_id": mod.RESOURCE_ID, "ogg": str(dest)})
        mpath = sound.manifest_override_path(mod_root, "sfx").with_suffix(".txt.PARTIAL")
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(sound.serialize_manifest(entries), encoding="utf-8")
        return {"minted": minted, "manifest": str(mpath), "partial": True, "stock_rows": 0}
    for mod, _ch, wav in cues:
        res = sound.mint_song(wav, mod_root, kind="sfx", new_id=mod.SOUND_ID,
                              resource_id=mod.RESOURCE_ID, quality=6, set_priority=False)
        minted.append({"song_id": res["song_id"], "resource_id": res["resource_id"], "ogg": res["ogg"]})
    mpath = sound.manifest_override_path(mod_root, "sfx")
    rows = sound.parse_manifest(mpath.read_text(encoding="utf-8"))
    return {"minted": minted, "manifest": str(mpath), "partial": False,
            "stock_rows": len(rows) - len(minted), "total_rows": len(rows)}


# --------------------------------------------------------------------------------------------- the check
class Check:
    """A tiny pass/fail ledger -- every assertion in one list, with the law it defends named."""

    def __init__(self):
        self.rows = []

    def __call__(self, ok: bool, label: str, detail: str = "") -> bool:
        self.rows.append({"ok": bool(ok), "label": label, "detail": detail})
        return bool(ok)

    @property
    def failed(self) -> list:
        return [r for r in self.rows if not r["ok"]]

    def report(self) -> int:
        for r in self.rows:
            print(f"  [{'ok' if r['ok'] else 'FAIL'}] {r['label']}" + (f"  -- {r['detail']}" if r["detail"] else ""))
        print(f"\n{len(self.rows) - len(self.failed)}/{len(self.rows)} check(s) passed")
        return 0 if not self.failed else 2


def check_effect_folder(ck: Check, mod_root: Path, spec: dict, *, ef_id: int, tick: int, window: int,
                        drain: int, manifest_name: str, staging_curves: dict, key_strs: set,
                        on_disc_clips: set, label: str) -> dict:
    """THE PER-FOLDER CHECKS (formerly a single hardcoded pass over ef091 -- THE PAIR round generalized it
    to run against EITHER effect folder, called once for FULL and once for SHORT): the folder is staged,
    ``Sequence.seq`` is absent (R15), the ``.seq`` lints clean against ITS OWN ``ef_id``, the manifest +
    particles are staged and lint clean, ``FileList.txt`` names ITS OWN manifest, the two clocks align,
    every curve spans the window, Movement anchors on ``TargetAveragePosition*``, the playlist covers the
    window at Speed 1 against ITS OWN ``staging_curves`` (never the other folder's), and every playlist
    entry both names a minted clip and resolves to a staged ``.anim`` (the clips are a SHARED pool -- minted
    ONCE -- but each folder's playlist may reference a different subset/order of it). Returns the parsed
    manifest's ``FBX[0]`` dict."""
    ef = mod_root / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{ef_id:03d}"

    seq_path = ef / "PlayerSequence.seq"
    ck(seq_path.is_file(), f"{label}: PlayerSequence.seq staged")
    ck(not (ef / "Sequence.seq").exists(), f"{label}: Sequence.seq ABSENT",
       "R15: SFXData.cs:174 reads it unconditionally; a present one threads in as duplicate damage")

    parts = [Path(p).name for p in (spec.get("particles") or [])]
    rep = SL.lint_seq_file(seq_path, private_ef=ef_id, particles=parts)
    ck(not rep.errors, f"{label}: the staged .seq lints clean",
       f"{len(rep.errors)} error(s), {len(rep.warnings)} warning(s), {rep.total_ticks} fixed-Wait ticks")
    for p in rep.problems:
        print(f"      seqlint({label}): {p}")

    for name in parts + [manifest_name]:
        f = ef / name
        if not ck(f.is_file(), f"{label}: {name} staged"):
            continue
        probs = SL.lint_sfxmodel_file(f)
        ck(not probs, f"{label}: {name} lints clean", "; ".join(probs))

    fl = (ef / "FileList.txt").read_bytes() if (ef / "FileList.txt").is_file() else b""
    ck(fl == f"Model {manifest_name}\n".encode(),
       f"{label}: FileList.txt grammar (single spaces, its OWN manifest name)", repr(fl))

    man = json.loads((ef / manifest_name).read_text(encoding="utf-8"))
    fbx = man["FBX"][0]
    ck(fbx["Path"] == spec["name"], f"{label}: manifest names the minted GEO", fbx["Path"])
    win = int(fbx["End"]) - int(fbx["Start"])
    ck(tick + win == drain, f"{label}: THE TWO CLOCKS align",
       f"PlaySFX@{tick} + window {win} = {tick + win} (expected {drain})")
    for curve in ("Movement", "Rotation", "Scaling"):
        total = sum(int(p["Duration"]) for p in fbx[curve])
        ck(total == win, f"{label}: {curve} spans the whole window", f"{total} vs {win}")
    ck(all("TargetAveragePosition" in v for k, v in fbx["Movement"][0].items()
           if k.startswith(("Origin", "Destination"))),
       f"{label}: Movement anchors on TargetAveragePosition*",
       "THE MULTI-TARGET NULL: SFXData.cs:149 nulls the target for an AllEnemy cast")

    cov = D.playlist_coverage(spec, staging_curves)
    ck(cov is not None and cov["short_by"] == 0, f"{label}: the playlist covers the window (never freezes)",
       f"{cov['playlist_ticks']} ticks over {cov['window']} ({', '.join(cov['detail'])})" if cov else "not derivable")
    # THE SPEED-DIVISOR DEFECT (STORYBOARD 11.9): animFrame is a CLIP-FRAME index and animMaxFrame is a
    # TICK count, and SFXDataMesh.cs:869 divides one by the other -- equal only at Speed 1. Any entry
    # above 1 runs its clip out after 1/s of the entry and FREEZES the rig for the remainder.
    ck(cov is not None and not cov["nonunit_speeds"],
       f"{label}: every playlist entry is Speed 1 (THE SPEED-DIVISOR DEFECT)",
       "SFXDataMesh.cs:869 -- size the CLIP to the beat, never the divisor"
       if cov and not cov["nonunit_speeds"] else f"non-unit speeds: {cov['nonunit_speeds'] if cov else '?'}")

    entries = {e["Path"].rsplit("/", 1)[-1] for e in fbx.get("Animations", [])}
    ck(entries == key_strs, f"{label}: every playlist entry names a MINTED clip", str(sorted(entries)))
    ck(entries <= on_disc_clips, f"{label}: every playlist entry resolves to an .anim on disc",
       f"playlist {sorted(entries)} vs disc {sorted(on_disc_clips)}")
    return fbx


def check_all(mod_root: Path, summon: dict, audio: dict, out_dir: Path) -> Check:
    ck = Check()
    spec = summon["spec"]
    short = summon["short"]

    # --- 1. the two effect folders (THE PAIR) -----------------------------------------------------------
    keys = [c["key"] for c in summon["overlay"].get("clip_files", [])]
    key_strs = {str(k) for k in keys}
    on_disc = {p.stem for p in mod_root.rglob(f"Animations/{GEO_ID}/*.anim")}

    check_effect_folder(ck, mod_root, spec, ef_id=FULL_PRIVATE_EF, tick=FULL_PLAY_SFX_TICK,
                        window=FULL_WINDOW, drain=FULL_DRAIN_TICK, manifest_name=spec["manifest"],
                        staging_curves=spec["staging_curves"], key_strs=key_strs, on_disc_clips=on_disc,
                        label=f"ef{FULL_PRIVATE_EF:03d} (FULL)")
    check_effect_folder(ck, mod_root, spec, ef_id=SHORT_PRIVATE_EF, tick=SHORT_PLAY_SFX_TICK,
                        window=SHORT_WINDOW, drain=SHORT_DRAIN_TICK, manifest_name=spec["short_manifest"],
                        staging_curves=spec["short_staging_curves"], key_strs=key_strs, on_disc_clips=on_disc,
                        label=f"ef{SHORT_PRIVATE_EF:03d} (SHORT)")

    # --- 2. the clips + the mint (minted ONCE -- a shared 60000-60003 band, both folders reference it) ---
    ck(keys == [60000, 60001, 60002, 60003], "clips minted into the 60000 band (named stems)", str(keys))
    for c in summon["overlay"].get("clip_files", []):
        dest = Path(c["dest"])
        n = D.anim_frame_count(dest)          # the KIT's own reader, not a local re-implementation
        ck(dest.is_file() and n is not None, f"clip {c['name']} loads under the kit reader",
           f"{n} frames -> {dest.name}")
    mint = summon["mint"]
    ck(Path(mint["fbx_dest"]).is_file(), "the FBX mint landed", mint["fbx_dest"])
    ck(bool(mint["textures"]), "the atlas rode along", ", ".join(Path(t).name for t in mint["textures"]))

    dp = (mod_root / "DictionaryPatch.txt").read_text(encoding="utf-8").splitlines()
    ck(f"3DModel {GEO_ID} {spec['name']}" in dp, "the 3DModel line is registered (RELAUNCH gate)")
    ck(sum(1 for ln in dp if ln.startswith(f"3DModel {GEO_ID} ")) == 1, "exactly one 3DModel line for 6400")
    ck(not any(ln.startswith(f"3DModelAnimation 6000") for ln in dp),
       "NO 3DModelAnimation line for the summon clips",
       "the SFX route loads by literal path (SFXDataMesh.cs:793) -- clips are recast-only")

    # --- 3. the ability wiring (the cross-lane join the storyboard cares most about) -------------------
    act_path = mod_root / "StreamingAssets" / "Data" / "Battle" / "Actions.csv"
    ck(act_path.is_file(), "Actions.csv delta emitted")
    act_lines = act_path.read_text(encoding="utf-8").splitlines()
    row = next((ln for ln in act_lines if ln.split(":", 1)[-1].startswith(ABILITY + ";")), "")
    ck(bool(row), f"the {ABILITY!r} row exists", row)
    if row:
        f = row.split(":", 1)[-1].split(";")
        ck(f[1] == str(ROLL_ABILITY),
           f"{ABILITY!r} keeps minted ability id {ROLL_ABILITY} (roll_ability's live discriminator)", f[1])
        ck(f[3].startswith("AllEnemy"), "targets = AllEnemy (the rung-1 structural full-cast law)", f[3])
        ck(f[8] == str(FULL_PRIVATE_EF) and f[9] == str(SHORT_PRIVATE_EF),
           f"vfx1 = ef{FULL_PRIVATE_EF:03d} (FULL) AND vfx2 = ef{SHORT_PRIVATE_EF:03d} (SHORT)",
           f"vfx1={f[8]} vfx2={f[9]}")
        ck(f[10] != "87", "scriptId != 87 (Odin's Sword SA never triggered)", f[10])
        ck((int(f[2].split("(")[-1].rstrip(")")) & 4) == 0, "THE TYPE-4 MP LAW: bit 4 clear", f[2])
    ck(any("Bahamut Cinema;194;" in ln for ln in act_lines),
       "Bahamut Cinema keeps id 194 (the live M1b bench binding is untouched)")

    # --- 4. THE ROLL (review 2026-07-24, the short/full pair round) ------------------------------------
    # The AbilityFeatures Command-trigger the [[summon]] block's roll trio emits -- gated on BOTH
    # `roll_command` AND `roll_ability` (item 1: command 46 hosts four abilities, so CommandId alone
    # cannot discriminate which one is casting). Checked here, not just in the kit's own unit tests,
    # because THIS is the one place the two upstream steps (the field build's minted command/ability ids,
    # and the summon emit's roll formula) actually have to AGREE for the roll to fire correctly at all.
    ab_path = mod_root / "StreamingAssets" / "Data" / "Characters" / "Abilities" / "AbilityFeatures.txt"
    ck(ab_path.is_file(), "AbilityFeatures.txt staged (the roll artifact)")
    marker = f"summon-short-roll-{spec['id']}"
    begin = f"## >>> ff9mapkit ability_feature {marker} (auto -- edit the toml, not here)"
    cond = f"IsTheCaster && CommandId == {ROLL_COMMAND} && AbilityId == {ROLL_ABILITY}"
    formula = f"GetRandom() < (MP > {spec['roll_mp']} ? 230 : 170)"
    if ab_path.is_file():
        ab_text = ab_path.read_text(encoding="cp1252")
        ck(begin in ab_text, "the roll's marker section is present", marker)
        ck(f"[code=Condition] {cond} [/code]" in ab_text,
           "the roll's Condition discriminates command AND ability", cond)
        ck(f"[code=IsShortSummon] {formula} [/code]" in ab_text,
           "the roll's formula matches the 3a-compensated stock odds", formula)
        ck(ab_text.count(begin) == 1, "exactly ONE roll section", f"{ab_text.count(begin)} occurrence(s)")

    # a SECOND emit into the SAME mod_root must not duplicate the marker section -- the idempotent-redeploy
    # proof (MUST-FIX 2's fix), exercised here rather than only asserted in the kit's own unit tests.
    # `out=` is silenced: `Check.report()` prints every row only AFTER `check_all()` returns, so this
    # redeploy's own receipt would otherwise interleave BEFORE the "[ok] ..." lines it is nested between.
    redeploy = D.emit_overlay(load_block(), mod_root, None, work_dir=out_dir, out=lambda *a, **k: None)
    ck(redeploy["spec"]["short_private_ef"] == SHORT_PRIVATE_EF, "a redeploy resolves the SAME short_private_ef",
       str(redeploy["spec"]["short_private_ef"]))
    if ab_path.is_file():
        ab_text2 = ab_path.read_text(encoding="cp1252")
        ck(ab_text2.count(begin) == 1, "a re-run does NOT duplicate the roll section",
           f"{ab_text2.count(begin)} occurrence(s)")
        ck(ab_text2 == ab_text, "the re-run's AbilityFeatures.txt is byte-identical", "")

    # Iviv's minted command1 ("Spark") really resolved to `roll_command`'s target -- read from the field
    # build's OWN Commands.csv output, not re-derived from the toml, so a band-order/allocation change
    # fails loud HERE instead of silently desyncing the roll's Condition from the live command id.
    cmd_path = mod_root / "StreamingAssets" / "Data" / "Characters" / "Commands.csv"
    ck(cmd_path.is_file(), "Commands.csv delta emitted")
    if cmd_path.is_file():
        cmd_lines = cmd_path.read_text(encoding="utf-8").splitlines()
        cmd_row = next((ln for ln in cmd_lines if ln.rstrip().endswith("# Spark")), "")
        ck(bool(cmd_row), "Iviv's minted command1 ('Spark') row exists in Commands.csv", cmd_row)
        if cmd_row:
            cid = cmd_row.split(";", 1)[0]
            ck(cid == str(ROLL_COMMAND),
               f"'Spark' resolved to command id {ROLL_COMMAND} (roll_command's live target)",
               f"got {cid} -- a band-order change would desync the roll's Condition silently otherwise")

    # --- 5. the audio ------------------------------------------------------------------------------------
    ffprobe = _ffprobe()
    for m in audio["minted"]:
        ogg = Path(m["ogg"])
        ck(ogg.is_file() and ogg.read_bytes()[:4] == b"OggS", f"sfx {m['song_id']} .ogg staged", ogg.name)
        if ffprobe:
            info = _probe(ffprobe, ogg)
            ck(info.get("codec") == "vorbis", f"sfx {m['song_id']} decodes as vorbis",
               f"{info.get('codec')} {info.get('duration', 0):.2f}s")
    ck(len(audio["minted"]) == 3, "three ids minted", str([m["song_id"] for m in audio["minted"]]))
    ck(not audio["partial"], "the sfx manifest override carries the STOCK table too",
       f"{audio.get('stock_rows', 0)} stock + 3 minted"
       if not audio["partial"] else "PARTIAL (--offline-audio) -- do NOT deploy this manifest")
    full_seq_text = (mod_root / "StreamingAssets" / "Data" / "SpecialEffects" /
                     f"ef{FULL_PRIVATE_EF:03d}" / "PlayerSequence.seq").read_text(encoding="utf-8")
    for m in audio["minted"]:
        ck(f"Sound={m['song_id']}" in full_seq_text, f"the FULL .seq plays sfx {m['song_id']}")

    # --- 6. the blast radius -----------------------------------------------------------------------------
    sfx_dir = mod_root / "StreamingAssets" / "Data" / "SpecialEffects"
    others = sorted(p.name for p in sfx_dir.iterdir() if p.is_dir()) if sfx_dir.is_dir() else []
    expect = sorted([f"ef{FULL_PRIVATE_EF:03d}", f"ef{SHORT_PRIVATE_EF:03d}"])
    ck(others == expect, "the SpecialEffects tree is EXACTLY {ef080, ef091}, nothing else",
       f"ef084 (the live Thomas/M1b bench) is never in this tree: {others}")
    return ck


def _ffprobe():
    import shutil as _sh
    try:
        cand = sound.find_ffmpeg().replace("ffmpeg", "ffprobe")
    except RuntimeError:
        return None
    return cand if (_sh.which(cand) or Path(cand).exists()) else _sh.which("ffprobe")


def _probe(ffprobe: str, path: Path) -> dict:
    try:
        out = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                              "format=duration:stream=codec_name", "-of", "json", str(path)],
                             capture_output=True, text=True, check=True)
        d = json.loads(out.stdout)
        return {"duration": float(d["format"]["duration"]),
                "codec": d.get("streams", [{}])[0].get("codec_name", "")}
    except (subprocess.CalledProcessError, ValueError, KeyError, OSError):
        return {}


# ------------------------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(RUNG8 / "stage" / "final"), help="staging root (default ../stage/final)")
    ap.add_argument("--clean", action="store_true", help="wipe the staging root first")
    ap.add_argument("--check", action="store_true", help="re-read every emitted byte and check it")
    ap.add_argument("--offline-audio", action="store_true",
                    help="skip the install read for the stock sfx table (emits a .PARTIAL manifest that "
                         "must NOT be deployed) -- for a box with no FF9 install")
    args = ap.parse_args()

    out = Path(args.out)
    if args.clean and out.exists():
        shutil.rmtree(out)
    mod_root = out / MOD_NAME

    print(f"=== rung 8 bench -> {out}")
    print(f"--- step 1: the field + the {ABILITY!r} ability ({BENCH_TOML.name})")
    field = step_field(mod_root)
    for ln in field["stdout"]:
        print(f"    {ln}")

    print("--- step 2: the [[summon]] block (overlay lane, authored casts, game=None) -- THE PAIR")
    summon = step_summon(mod_root, out)
    spec = summon["spec"]
    print(f"    {spec['name']} (id {spec['id']})")
    print(f"    FULL  -> ef{spec['private_ef']:03d}/{spec['manifest']}")
    print(f"    host .seq (FULL) : {Path(summon['seq']['seq_dest']).name}  (AUTHORED, verbatim from "
          f"{Path(summon['seq']['seq_source']).name})")
    short = summon.get("short")
    if short:
        print(f"    SHORT -> ef{spec['short_private_ef']:03d}/{spec['short_manifest']}")
        print(f"    host .seq (SHORT): {Path(short['seq_dest']).name}  (AUTHORED, verbatim from "
              f"{Path(short['seq_source']).name})  -> {short['seq_dest']}")
        print(f"    roll     : command={spec['roll_command']} ability={spec['roll_ability']} "
              f"mp={spec['roll_mp']}")
    for c in summon["overlay"].get("clip_files", []):
        print(f"    clip     : {c['name']:<8} -> Animations/{spec['id']}/{c['key']}")
    for p in summon["overlay"].get("particles", []):
        print(f"    particle : {Path(p).name}")
    print(f"    revert   : {summon['revert_script']}")

    print("--- step 3: the minted sfx (100001-100003)")
    audio = step_audio(mod_root, offline=args.offline_audio)
    for m in audio["minted"]:
        print(f"    sfx {m['song_id']} -> {m['resource_id']}")
    print(f"    manifest : {audio['manifest']}"
          + ("  *** PARTIAL -- do NOT deploy ***" if audio["partial"] else
             f"  ({audio.get('stock_rows')} stock rows preserved)"))

    files = sorted(p for p in mod_root.rglob("*") if p.is_file())
    report = {"mod_root": str(mod_root), "files": len(files),
              "field_warnings": field["warnings"], "summon": {
                  "spec": {k: v for k, v in spec.items()
                          if k not in ("staging_curves", "short_staging_curves")},
                  "artifacts": summon["artifacts"], "revert_script": summon["revert_script"]},
              "audio": audio}
    print(f"\n{len(files)} file(s) staged under {mod_root}")

    rc = 0
    if args.check:
        print("\n--- check ---")
        ck = check_all(mod_root, summon, audio, out)
        rc = ck.report()
        report["checks"] = ck.rows
    (out / "BENCH-REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"report: {out / 'BENCH-REPORT.json'}")
    print("\n" + ("BENCH CLEAN" if rc == 0 else "BENCH FAILED"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
