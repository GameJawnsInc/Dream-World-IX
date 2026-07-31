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
    for name, wants_ui in (("s1-stand-in-the-game.md", True), ("s2-someone-lives-here.md", False)):
        src = B.REPO / "ff9mapkit" / "docs" / "tutorials" / name
        page = B.page_from_source(src)
        assert page.meta and page.meta.get("track") == "S", f"{name} lost its frontmatter"
        assert bool(page.meta.get("ui")) == wants_ui
        assert B.ui_gate({page.rel: page}) == []
        assert 'class="tut-reqs"' in page.body and 'class="chip track"' in page.body
        assert "```toml" not in page.body and "[tutorial]" not in page.body
    assert B.page_from_source(B.REPO / "ff9mapkit" / "docs" / "tutorials"
                              / "s2-someone-lives-here.md").meta["builds_on"] == \
        ["s1-stand-in-the-game"]
