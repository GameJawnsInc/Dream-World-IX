#!/usr/bin/env python3
"""journey.merge_dists -- the single-folder journey deploy: union built campaign dists (+ the hub) into ONE
mod folder. The journey's id/FBG/EVT/text-block disjointness makes the per-field assets union cleanly; the
root DictionaryPatch/BattlePatch are concatenated verbatim (NOT deduped); the fixed-path start-state CSVs
collide, so the entry campaign wins. Pure/offline.
"""
from __future__ import annotations

from ff9mapkit import journey as J
from ff9mapkit.editor import jobs


def _mkdist(root, *, fields, battle, csv_marker, asset, mesid, item_text=False):
    """A minimal built mod dist mirroring the real layout: a disjoint FieldMaps asset dir + a disjoint
    <mesid>.mes dialogue block under FF9_Data (NOT StreamingAssets!), a (colliding) start-state CSV, a
    DictionaryPatch (FieldScene lines), a BattlePatch (Battle:/Music: pairs), optionally a TextPatch, a
    ModDescription."""
    fm = root / "StreamingAssets" / "assets" / "resources" / "FieldMaps" / asset
    fm.mkdir(parents=True)
    (fm / "x.bytes").write_text("a", encoding="utf-8")
    mes = root / "FF9_Data" / "embeddedasset" / "text" / "us" / "field"     # the dialogue text lives HERE
    mes.mkdir(parents=True)
    (mes / f"{mesid}.mes").write_text(f"dialogue-{mesid}", encoding="utf-8")
    csvd = root / "StreamingAssets" / "Data" / "Items"
    csvd.mkdir(parents=True)
    (csvd / "InitialItems.csv").write_text(csv_marker, encoding="utf-8")
    (root / "DictionaryPatch.txt").write_text(
        "\n".join(f"FieldScene {i} 11 N{i} N{i} 20000" for i in fields) + "\n", encoding="utf-8")
    (root / "BattlePatch.txt").write_text(
        "\n".join(f"Battle: {s}\nMusic: 0" for s in battle) + "\n", encoding="utf-8")
    # ForkDonorPatch.txt: the per-campaign fork->donor map (Dante's off-mesh exemption etc.) -- ADDITIVE
    (root / "ForkDonorPatch.txt").write_text(
        "# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n"
        + "\n".join(f"{i} {i - 6000}" for i in fields) + "\n", encoding="utf-8")
    if item_text:
        (root / "TextPatch.txt").write_text(f">DATABASE find/replace {asset}\n", encoding="utf-8")
    (root / "ModDescription.xml").write_text("<Mod></Mod>", encoding="utf-8")
    return root


def test_merge_dists_unions_assets_concats_patches_entry_csv_wins(tmp_path):
    d1 = _mkdist(tmp_path / "d1", fields=[6000, 6001], battle=[336], csv_marker="CAMPAIGN_A", asset="FBG_A",
                 mesid=20000, item_text=True)
    d2 = _mkdist(tmp_path / "d2", fields=[6200, 6201], battle=[337], csv_marker="CAMPAIGN_B_ENTRY", asset="FBG_B",
                 mesid=20001, item_text=True)
    out = tmp_path / "merged"
    info = J.merge_dists([d1, d2], out=out, folder_name="FF9CustomMap-jtest", entry_dist=d2)

    base = out / "StreamingAssets" / "assets" / "resources" / "FieldMaps"
    assert (base / "FBG_A" / "x.bytes").is_file() and (base / "FBG_B" / "x.bytes").is_file()  # disjoint assets union

    # the dialogue text under FF9_Data/ (NOT StreamingAssets) must be carried -- both campaigns' blocks
    mesdir = out / "FF9_Data" / "embeddedasset" / "text" / "us" / "field"
    assert (mesdir / "20000.mes").is_file() and (mesdir / "20001.mes").is_file()

    dp = (out / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert dp.count("FieldScene") == 4 and "6000" in dp and "6201" in dp                       # all lines concatenated

    bp = (out / "BattlePatch.txt").read_text(encoding="utf-8")
    # both campaigns' battles + Music: 0 NOT deduped away (the bug a naive line-dedup would cause)
    assert "Battle: 336" in bp and "Battle: 337" in bp and bp.count("Music: 0") == 2

    tp = (out / "TextPatch.txt").read_text(encoding="utf-8")                                   # item-text concatenated
    assert "FBG_A" in tp and "FBG_B" in tp

    # ★ the Dante regression: ForkDonorPatch is ADDITIVE -> BOTH campaigns' fork->donor maps must survive
    # (entry-last-wins-copy kept only the entry's, silently breaking every other campaign's special-case gates).
    fd = (out / "ForkDonorPatch.txt").read_text(encoding="utf-8")
    assert "6000 0" in fd and "6200 200" in fd and "6201 201" in fd                            # campaign A AND B maps

    csv = out / "StreamingAssets" / "Data" / "Items" / "InitialItems.csv"
    assert csv.read_text(encoding="utf-8") == "CAMPAIGN_B_ENTRY"                                # entry dist (last) wins

    assert "FF9CustomMap-jtest" in (out / "ModDescription.xml").read_text(encoding="utf-8")
    assert info["fields"] == 4 and info["dists_merged"] == 2


def test_merge_dists_overwrites_an_existing_out_and_handles_no_battlepatch(tmp_path):
    d1 = _mkdist(tmp_path / "d1", fields=[6000], battle=[336], csv_marker="A", asset="FBG_A", mesid=20000)
    (d1 / "BattlePatch.txt").unlink()                          # a campaign with no scripted-battle BGM
    out = tmp_path / "merged"
    out.mkdir()
    (out / "stale.txt").write_text("old", encoding="utf-8")    # a prior merge that must be wiped
    J.merge_dists([d1], out=out, folder_name="FF9CustomMap-x", entry_dist=d1)
    assert not (out / "stale.txt").exists()                    # out is rebuilt, not appended to
    assert not (out / "BattlePatch.txt").exists()              # no BattlePatch when no dist has one
    assert (out / "DictionaryPatch.txt").read_text(encoding="utf-8").count("FieldScene") == 1


def test_deploy_journey_argv_single_folder_flag():
    a = jobs.deploy_journey_argv("/repo", "j.toml", apply=True, single_folder=True)
    assert "--single-folder" in a and "--apply" in a
    b = jobs.deploy_journey_argv("/repo", "j.toml", apply=True, single_folder=False)
    assert "--single-folder" not in b
    # single_folder is gated under --apply (a dry-run never merges)
    c = jobs.deploy_journey_argv("/repo", "j.toml", single_folder=True)
    assert "--single-folder" not in c and "--apply" not in c
