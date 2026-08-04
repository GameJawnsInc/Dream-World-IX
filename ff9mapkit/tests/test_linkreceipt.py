"""`.ff9links.json` -- the journey's cross-campaign doors exist ONLY in the install.

No dist can contain them: the destination is another campaign's id and only the journey knows it. So a
single-campaign `deploy-campaign` (rmtree + copytree of the unpatched dist) reverts them silently. These
tests pin the three states that matters -- applied, still applied, reverted -- plus the interaction that
makes the feature usable: a correct journey deploy must NOT read as drift.
"""

from __future__ import annotations

import pytest

from ff9mapkit import linkreceipt as lr
from ff9mapkit import stamp

PATCHED = b"PATCHED---BYTES"
UNPATCHED = b"UNPATCHED-BYTES"


def _folder(tmp_path, body=UNPATCHED):
    root = tmp_path / "FF9CustomMap-x"
    (root / "sub").mkdir(parents=True)
    eb = root / "sub" / "EVT_BOUNDARY.eb.bytes"
    eb.write_bytes(body)
    stamp.write(root, stamp.finalize(
        {"stamp_version": 1, "kit_version": "x", "built_utc": "t", "mod_name": "M",
         "context": "journey", "source": None, "members": []}, root))
    return root, eb


def _apply(root, eb):
    """What journey._record_link_receipts does after patching: re-stamp, THEN receipt."""
    stamp.write(root, stamp.finalize(stamp.read(root), root))
    return lr.write_receipt(root, lr.build_receipt(root, [{
        "eb": "EVT_BOUNDARY", "mode": "field_remap", "dst_id": 6501,
        "remap": {300: 6501}, "files": [str(eb)], "found": True}]))


def test_a_patched_folder_records_what_was_applied(tmp_path):
    root, eb = _folder(tmp_path)
    eb.write_bytes(PATCHED)
    assert _apply(root, eb) is not None
    st = lr.check(root)
    assert st.has_receipt and st.satisfied
    assert st.intact and not st.reverted and not st.missing
    assert st.receipt["links"][0]["dst_id"] == 6501


def test_a_correct_journey_deploy_does_not_read_as_drift(tmp_path):
    """★ THE INTERACTION. Patching the install changes bytes the build stamp already hashed, so without
    the re-stamp a CORRECT journey deploy reports drift -- and a check that fires on the right workflow is
    one nobody reads. The receipt file itself must also be excluded from the digest, or it lands as an
    'extra' and verify-build can never go clean after a journey."""
    root, eb = _folder(tmp_path)
    eb.write_bytes(PATCHED)
    _apply(root, eb)
    rep = stamp.verify(root)
    assert rep.clean, rep.render()
    assert lr.RECEIPT_NAME not in rep.extra and lr.RECEIPT_NAME not in (rep.stamp.get("files") or {})


def test_a_campaign_redeploy_reverting_the_patch_is_caught(tmp_path):
    """The whole point: the dist holds UNPATCHED bytes, so a wholesale replace puts them back."""
    root, eb = _folder(tmp_path)
    eb.write_bytes(PATCHED)
    _apply(root, eb)
    eb.write_bytes(UNPATCHED)                                   # what deploy_campaign's copytree does
    st = lr.check(root)
    assert not st.satisfied
    assert [f for _, f in st.reverted] == ["sub/EVT_BOUNDARY.eb.bytes"]
    assert "NOT APPLIED HERE ANY MORE" in st.render()
    assert "deploy-journey" in st.render(), "the report has to say how to restore them"


def test_a_deleted_patched_file_is_caught_separately_from_a_revert(tmp_path):
    root, eb = _folder(tmp_path)
    eb.write_bytes(PATCHED)
    _apply(root, eb)
    eb.unlink()
    st = lr.check(root)
    assert not st.satisfied and st.missing and not st.reverted


def test_a_journey_that_patches_nothing_removes_a_stale_receipt(tmp_path):
    """A receipt for links the journey no longer has would block a deploy forever."""
    root, eb = _folder(tmp_path)
    eb.write_bytes(PATCHED)
    assert _apply(root, eb) is not None and lr.read_receipt(root) is not None
    assert lr.write_receipt(root, lr.build_receipt(root, [])) is None
    assert lr.read_receipt(root) is None
    assert not lr.check(root).has_receipt


def test_an_unpatched_folder_has_no_receipt(tmp_path):
    root, _eb = _folder(tmp_path)
    st = lr.check(root)
    assert not st.has_receipt and not st.satisfied
    assert "no journey links applied here" in st.render()


@pytest.mark.parametrize("body", [b"", b"not json", b'{"links": "not a list"}'])
def test_a_malformed_receipt_reads_as_absent_not_as_a_crash(tmp_path, body):
    root, _eb = _folder(tmp_path)
    lr.receipt_path(root).write_bytes(body)
    assert lr.read_receipt(root) is None
    assert not lr.check(root).has_receipt
