"""ForkDonorPatch.txt merge/revert bookkeeping (ff9mapkit.forkdonor) -- the fork-fidelity donor map that
every deploy into a folder shares. The revert must be SURGICAL: the old wholesale snapshot restore meant
fork A's redeploy (whose prelude runs A's revert) silently deleted fork B's row if B deployed after A --
B then loses its engine donor remap (occlusion / off-mesh exemptions) with nothing printed anywhere.
"""

from ff9mapkit import forkdonor as FD


def test_merge_row_is_byte_compatible_with_the_historical_file_shape():
    # tools/deploy_field.py always wrote exactly this header + one row per line; existing live files must
    # round-trip unchanged so the engine (and deploystack.fork_donor_blocks_at) keep reading them.
    out = FD.merge_row("", 4003, 1860)
    assert out == "# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n4003 1860\n"
    # re-merging replaces our own row, never duplicates it
    assert FD.merge_row(out, 4003, 561) == "# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n4003 561\n"


def test_merge_row_keeps_foreign_rows_and_matches_exact_id():
    live = FD.merge_row(FD.merge_row("", 300, 100), 3000, 200)
    assert "300 100" in live and "3000 200" in live                       # 300 did not claim 3000's row
    live2 = FD.merge_row(live, 300, 999)
    assert "300 999" in live2 and "3000 200" in live2 and "300 100" not in live2


def test_revert_row_preserves_a_foreign_row_added_since_the_backup():
    """THE scenario: fork A deploys into an empty file (backup = ""), fork B adds its row, A redeploys --
    A's prelude revert must leave B's row standing (the old snapshot restore deleted the whole file)."""
    live_after_a = FD.merge_row("", 30500, 1860)                          # A's deploy; backup was ""
    live_after_b = FD.merge_row(live_after_a, 30600, 561)                 # B deploys later
    out = FD.revert_row(live_after_b, "", 30500)                          # A's revert
    assert "30600 561" in out and "30500" not in out
    assert out.startswith(FD.HEADER)


def test_revert_row_restores_our_prior_row_from_the_backup():
    backup = FD.merge_row("", 30500, 1860)                                # our OLD mapping at backup time
    live = FD.merge_row(FD.merge_row("", 30500, 2200), 30600, 561)        # redeployed to a new donor + B
    out = FD.revert_row(live, backup, 30500)
    assert "30500 1860" in out and "30500 2200" not in out and "30600 561" in out


def test_revert_row_empty_result_signals_delete():
    live = FD.merge_row("", 30500, 1860)                                  # we are the only row
    assert FD.revert_row(live, "", 30500) == ""                           # "" -> the caller unlinks the file


def test_own_row_matches_exact_first_token():
    text = FD.merge_row(FD.merge_row("", 300, 100), 3000, 200)
    assert FD.own_row(text, 300) == "300 100"
    assert FD.own_row(text, 3000) == "3000 200"
    assert FD.own_row(text, 30) is None
