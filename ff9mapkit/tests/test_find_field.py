"""`ff9mapkit find-field` / extract.find_fields -- the id<->name<->FBG reverse lookup.

Pure table lookup (the in-package FBG_TO_EVT), so these run with no install / UnityPy / templates.
The friendly `name` + archive `folder` are user-local extras (manifest / import-all archive) and are
NOT asserted here -- only the always-available id / fbg / evt core."""
from ff9mapkit import extract


def test_by_id_is_exact_single_match():
    rows = extract.find_fields("2934")               # Crystal World CYSW_MAPX30
    assert [r["id"] for r in rows] == [2934]
    assert "cysw" in rows[0]["fbg"] and rows[0]["evt"].startswith("EVT_")


def test_digit_query_does_not_substring_match():
    # a digit is an EXACT id, not a substring: "293" must not return id 2934/2930/...
    assert all(r["id"] == 293 for r in extract.find_fields("293"))


def test_substring_matches_a_whole_zone():
    rows = extract.find_fields("cysw")
    assert len(rows) >= 20                            # the CYSW (Memoria/Crystal World) area
    assert all("cysw" in r["fbg"] for r in rows)
    assert rows == sorted(rows, key=lambda r: r["id"])  # sorted by id


def test_substring_matches_evt_name():
    # 'alex1' is only in the Prima Vista EVT names (EVT_ALEX1_*) -- not their FBG folders or friendly
    # names -- so every match here proves substring search reaches the EVT name.
    rows = extract.find_fields("alex1")
    assert rows and all("alex1" in r["evt"].lower() for r in rows)


def test_no_match_returns_empty():
    assert extract.find_fields("zzzznope-not-a-field") == []


def test_unknown_archive_dir_degrades_to_no_folder():
    rows = extract.find_fields("2934", archive_dir="/no/such/archive/dir")
    assert rows and rows[0]["folder"] is None
