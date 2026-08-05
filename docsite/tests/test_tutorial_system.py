"""The tutorial system's gates: frontmatter, the UI-label inventory gate, the CLI command gate.
Each gate is proven WITH TEETH (a planted defect must fail) -- a gate only ever seen green is a
gate never seen working.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import build as B  # noqa: E402

FRONT = """# 99 — Test

```toml
[tutorial]
goal = "A goal."
requires = ["gui"]

[[tutorial.ui]]
label = "Find…"
widget = "import_field.find_btn"
```

Body with **Find…** in it.
"""


def test_frontmatter_parses_and_strips():
    meta, rest = B.parse_tutorial_front(FRONT)
    assert meta["goal"] == "A goal."
    assert meta["ui"][0]["widget"] == "import_field.find_btn"
    assert "```toml" not in rest and "**Find…**" in rest


def test_inventory_is_committed_and_sane():
    inv = json.loads((B.HERE / "assets" / "ui-inventory.json").read_text(encoding="utf-8"))
    flat = {}
    for ents in inv["surfaces"].values():
        flat.update(ents)
    assert len(flat) > 50, "the harvest collapsed"
    assert flat["import_field.find_btn"]["text"] == "Find…"
    assert flat["import_field.field"]["a11y"] == "Field id or name"
    nj = inv["surfaces"]["dlg:new-journey"]
    assert len(nj) > 10, "the dialog harvest collapsed"
    assert "Multi-campaign arc — chain forked campaigns" in nj
    forms = {k: v for k, v in inv["surfaces"].items() if k.startswith("form:")}
    assert len(forms) > 15, "the editor-form harvest collapsed"
    assert forms["form:npc"]["requires_flag"]["text"] == "Appears when flag set"
    assert forms["form:choice-option"]["text"]["text"] == "Option text"   # <THING>_SPEC -> dashes


def test_committed_inventory_records_no_machine_state():
    """The inventory must describe the UI, never the box that harvested it. `build_deploy.dep_hint`
    once carried the SHARED mod folder's live deploy count ("410 deployed here · ..."), so the
    committed file drifted 410 -> 422 during unrelated work and `uiharvest --check` alarmed on
    another session's deploy. uiharvest._pin_live_state pins the known live reads; machine_leaks is
    the path-shaped backstop, and this is its always-runs (Qt-free) half -- the twin-harvest fence
    in test_uiharvest_pins.py covers the counts."""
    import uiharvest as U

    inv = json.loads((B.HERE / "assets" / "ui-inventory.json").read_text(encoding="utf-8"))
    assert U.machine_leaks(inv) == []
    # TEETH: an auditor only ever seen green is an auditor never seen working.
    planted = json.loads(json.dumps(inv))
    planted["surfaces"]["tab:build"]["build_deploy.dep_hint"]["text"] = str(Path.home() / "x.toml")
    assert U.machine_leaks(planted), "machine_leaks ignored a planted home-directory path"


def test_ledger_dependent_labels_are_pinned_in_the_committed_inventory():
    """Name the specific labels the pin owns, so removing a pin fails HERE (Qt-free, every run) and
    not only in the Qt fence -- which a machine without PySide6 skips."""
    import uiharvest as U

    build = json.loads((B.HERE / "assets" / "ui-inventory.json").read_text(
        encoding="utf-8"))["surfaces"]["tab:build"]
    n_rows, n_undo = len(U.PINNED_LEDGER), sum(1 for r in U.PINNED_LEDGER if r["script"])
    assert build["build_deploy.dep_hint"]["text"].startswith(
        f"{n_rows} deployed here · {n_undo} with an undo")
    assert str(U.PINNED_NEWGAME) in build["build_deploy.newgame_status"]["text"]
    assert str(U.PINNED_DEPLOY_TARGET[1] or 4003) in build["build_deploy.rb_test"]["text"]


def test_form_inventory_is_fresh_against_the_live_specs():
    """The ui_gate proves tutorial -> inventory. This proves inventory -> the LIVE forms.py.

    Without it the two halves can agree with each other while the real GUI has moved on: renaming a
    Field's label WITHOUT re-running the harvest left the build green at 191 pages and every gate
    passing -- precisely the rot the gate exists to catch, one layer further back. Closing it is only
    possible for `form:` surfaces, because harvest_forms() is plain data; the Qt-harvested tab:/dlg:
    halves need a driven app, so their freshness stays a `uiharvest --check` chore.
    """
    import uiharvest as U

    live = U.harvest_forms()
    committed = {k: v for k, v in json.loads(
        (B.HERE / "assets" / "ui-inventory.json").read_text(encoding="utf-8")
    )["surfaces"].items() if k.startswith("form:")}
    if live == committed:
        return
    drift = [f"  surface {k} vanished from forms.py" for k in committed.keys() - live.keys()]
    drift += [f"  surface {k} is new in forms.py" for k in live.keys() - committed.keys()]
    for k in live.keys() & committed.keys():
        for fk in committed[k].keys() - live[k].keys():
            drift.append(f"  {k}.{fk} vanished from forms.py")
        for fk in live[k].keys() - committed[k].keys():
            drift.append(f"  {k}.{fk} is new in forms.py")
        for fk in live[k].keys() & committed[k].keys():
            if live[k][fk] != committed[k][fk]:
                drift.append(f"  {k}.{fk}: committed {committed[k][fk]} -> live {live[k][fk]}")
    raise AssertionError(
        "docsite/assets/ui-inventory.json is STALE against ff9mapkit/ff9mapkit/editor/forms.py.\n"
        + "\n".join(sorted(drift))
        + "\nRe-run: py docsite/uiharvest.py   (then check whether any tutorial prose quoted the "
          "old label -- the ui_gate will say so)")


def test_ui_gate_dialog_scoped_declaration():
    good = FRONT.replace('label = "Find…"\nwidget = "import_field.find_btn"',
                         'label = "Hub name"\nwidget = "dlg:new-journey"') \
                .replace("**Find…**", "**Hub name**")
    assert B.ui_gate(_page(good)) == []
    # (the first draft used "Pick FF9 regions…" as the absent label -- and the gate correctly
    # REFUSED to fail it: that button exists in the dialog, hidden under the default Type. The
    # inventory harvests state-hidden controls on purpose; existence, not visibility, is its claim.)
    bad = good.replace('"Hub name"', '"No Such Control"').replace("**Hub name**",
                                                                  "**No Such Control**")
    assert any("no control labeled" in e for e in B.ui_gate(_page(bad)))


# An editor-FORM declaration: `form:<section>.<field key>`, the shape the core track's prose needs
# (its labels come from forms.py's <THING>_SPEC data, not from a rendered Qt tab).
FORM_FRONT = FRONT.replace('label = "Find…"\nwidget = "import_field.find_btn"',
                           'label = "Appears when flag set"\n'
                           'widget = "form:npc.requires_flag"') \
                  .replace("**Find…**", "**Appears when flag set**")


def test_ui_gate_form_field_declaration():
    assert B.ui_gate(_page(FORM_FRONT)) == []


def test_ui_gate_teeth_form_declarations():
    def errs(old: str, new: str) -> list[str]:
        return B.ui_gate(_page(FORM_FRONT.replace(old, new)))
    # an unknown form, an unknown field key, a whole-form path, and a stale label -- each named
    assert any("form surface 'form:goblin' is not in the inventory" in e
               for e in errs("form:npc.", "form:goblin."))
    assert any("has no field 'requires_flg'" in e for e in errs("requires_flag", "requires_flg"))
    assert any("names a whole form" in e for e in errs("form:npc.requires_flag", "form:npc"))
    stale = errs("Appears when flag set", "Shows when flag set")     # frontmatter AND prose
    assert any("no longer matches form:npc.requires_flag" in e
               and "Appears when flag set" in e for e in stale), stale


def _page(raw: str) -> dict:
    meta, _ = B.parse_tutorial_front(raw)
    p = B.Page(src=None, rel="t.html", title="t", body="", raw=raw, meta=meta)
    return {"t.html": p}


def test_ui_gate_passes_a_true_declaration():
    assert B.ui_gate(_page(FRONT)) == []


def test_ui_gate_teeth_wrong_label():
    assert any("no longer matches" in e
               for e in B.ui_gate(_page(FRONT.replace('label = "Find…"', 'label = "Fetch…"')
                                        .replace("**Find…**", "**Fetch…**"))))


def test_ui_gate_teeth_vanished_widget():
    assert any("not in the inventory" in e
               for e in B.ui_gate(_page(FRONT.replace("find_btn", "gone_btn"))))


def test_ui_gate_teeth_unused_label():
    assert any("never appears" in e
               for e in B.ui_gate(_page(FRONT.replace("Body with **Find…** in it.", "Body."))))


def test_cli_gate_teeth():
    raw = "```bash\nff9mapkit lint --no-such-flag x\nff9mapkit frobnicate\n```\n"
    pages = {"t.html": B.Page(src=None, rel="t.html", title="t", body="", raw=raw)}
    errs = B.cli_gate(pages, B.the_parser())
    assert any("--no-such-flag" in e for e in errs)
    assert any("frobnicate" in e for e in errs)


def test_cli_gate_accepts_placeholders_and_globals():
    raw = ("```bash\nff9mapkit --game <path> lint <your.field.toml>\n"
           "ff9mapkit <cmd>\npy -m ff9mapkit doctor\n```\n")
    pages = {"t.html": B.Page(src=None, rel="t.html", title="t", body="", raw=raw)}
    assert B.cli_gate(pages, B.the_parser()) == []


def test_spine_tutorials_declare_and_render_chips(tmp_path):
    for name in ("s1-fork-and-deploy.md", "s2-add-an-npc.md"):
        src = B.REPO / "ff9mapkit" / "docs" / "tutorials" / name
        page = B.page_from_source(src)
        assert page.meta and page.meta.get("track") == "S", f"{name} lost its frontmatter"
        assert page.meta.get("ui"), f"{name} declares no [[tutorial.ui]] controls"
        assert B.ui_gate({page.rel: page}) == []
        assert 'class="tut-reqs"' in page.body and 'class="chip track"' in page.body
        assert "```toml" not in page.body and "[tutorial]" not in page.body
    assert B.page_from_source(B.REPO / "ff9mapkit" / "docs" / "tutorials"
                              / "s2-add-an-npc.md").meta["builds_on"] == \
        ["s1-fork-and-deploy"]


def test_tutorials_index_gate_flags_unlisted_and_misordered():
    from pathlib import Path
    def tut(name, track=None, step=None):
        meta = {"goal": "g"}
        if track:
            meta.update(track=track, step=step)
        return B.Page(src=Path("ff9mapkit/docs/tutorials") / name, rel=f"ff9mapkit/docs/tutorials/{name[:-3]}.html",
                      title=name, body="", raw="", meta=meta)
    idx = B.Page(src=Path("ff9mapkit/docs/tutorials/README.md"), rel=B._TUT_INDEX,
                 title="idx", body="", raw="see x2-b.md then x1-a.md")
    pages = {p.rel: p for p in (idx, tut("x1-a.md", "X", 1), tut("x2-b.md", "X", 2), tut("x3-c.md"))}
    errs = B.tutorials_index_gate(pages)
    assert any("x3-c.md" in e for e in errs), errs                      # unlisted -> named
    assert any("out of step order" in e for e in errs), errs            # x2 before x1 -> flagged
    idx.raw = "x1-a.md then x2-b.md and x3-c.md"
    assert B.tutorials_index_gate(pages) == []
