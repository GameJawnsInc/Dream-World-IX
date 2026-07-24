"""The concept map must read as a TRUNK, not a scatter: the Journey ▸ Campaign ▸ Field spine gets a raised
plinth painted BEFORE the nodes and heavier trunk edges, while the field-children stay light.  These assert
the LAWS (plinth underneath + spine-heavier-than-child), not the literal pixel weights -- a uniform-weight
regression (the "scatter" state) fails them."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import (QApplication, QGraphicsLineItem,   # noqa: E402
                               QGraphicsPathItem)

from ff9mapkit.workspace import conceptmap                        # noqa: E402

_PAL = {"surface": "#16223a", "surface_btn": "#1e2d4a", "accent": "#5fc9d8", "accent_fg": "#08171b",
        "text": "#e8edf6", "muted": "#9fadc4", "border": "#2b3d5e"}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _view():
    return conceptmap.ConceptMapView(dict(_PAL), on_concept=lambda t: None)


def test_spine_edges_are_classified_from_the_edge_table():
    # the trunk links (both ends on the spine) vs the field-children -- _EDGES already distinguishes them.
    spine = [(a, b) for a, b in conceptmap._EDGES if conceptmap._is_spine_edge(a, b)]
    child = [(a, b) for a, b in conceptmap._EDGES if not conceptmap._is_spine_edge(a, b)]
    assert (0, 1) in spine and (1, 2) in spine, "Journey▸Campaign▸Field must classify as trunk links"
    assert (2, 3) in child, "Field▸Gateway is a field-child, not a trunk link"
    assert len(spine) == 2 and len(child) == 3


def test_trunk_edges_outweigh_field_children(app):
    # THE LAW: spine links draw heavier than leaf links.  A no-op that reverts every edge to one weight
    # (the old scatter) collapses these two buckets and fails the strict inequality below.
    v = _view()
    widths = sorted(round(it.pen().widthF())
                    for it in v._scene.items() if isinstance(it, QGraphicsLineItem))
    assert len(widths) == len(conceptmap._EDGES)
    spine_w = [w for w in widths if w == conceptmap._W_SPINE]
    child_w = [w for w in widths if w == conceptmap._W_CHILD]
    assert len(spine_w) == 2 and len(child_w) == 3, f"expected 2 trunk + 3 child weights, got {widths}"
    assert conceptmap._W_SPINE > conceptmap._W_CHILD, "the trunk pen must be heavier than a field-child"


def test_the_map_hears_the_text_dial(app):
    """CALIBRE reaches painted text only when THREADED (the mapview law -- no stylesheet reaches a
    QGraphicsScene): at 150% the view's minimum, the drawn glyphs, AND the click targets must all grow
    in one frame. The px-constant map this converts was deaf by construction."""
    from PySide6.QtWidgets import QGraphicsSimpleTextItem

    small = _view()
    big = conceptmap.ConceptMapView(dict(_PAL), on_concept=lambda t: None, scale=150)
    assert big.minimumWidth() > small.minimumWidth()
    assert big.minimumHeight() > small.minimumHeight()

    def title_pt(v):
        return max(it.font().pointSize() for it in v._scene.items()
                   if isinstance(it, QGraphicsSimpleTextItem))

    assert title_pt(big) > title_pt(small), "the glyphs must grow, not just the frame"
    # hit-test coords live in the SAME frame as the drawn boxes -- a scale that moved the art but not
    # the click targets would leave every box dead at 150%.
    assert big._boxes[0][0] == pytest.approx(small._boxes[0][0] * 1.5)
    assert big._scene.sceneRect().width() > small._scene.sceneRect().width()


def test_the_shell_threads_the_dial_through_the_door():
    """THE CALL-SITE LAW: a scale param nobody passes is a mechanism in a box. The shell's opener must
    hand its live _text_scale to show_concept_map -- asserted on the AST (a docstring naming the kwarg
    must not satisfy a fence about code)."""
    import ast
    import inspect
    import textwrap

    from ff9mapkit.workspace import shell

    tree = ast.parse(textwrap.dedent(inspect.getsource(shell.Workspace._show_concept_map)))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and getattr(n.func, "id", getattr(n.func, "attr", "")) == "show_concept_map"]
    assert calls, "the opener no longer calls show_concept_map"
    kw = {k.arg: k.value for c in calls for k in c.keywords}
    v = kw.get("scale")
    assert isinstance(v, ast.Attribute) and v.attr == "_text_scale", \
        "the opener must pass scale=self._text_scale (the call-site law)"


def test_plinth_is_a_quiet_band_painted_under_the_spine(app):
    v = _view()
    items = v._scene.items()                                # top-of-stack first
    paths = [it for it in items if isinstance(it, QGraphicsPathItem)]
    # the plinth is the ONE path drawn in the neutral border pen (nodes wear the accent), palette-token
    # only -- no gold, no accent (the one-accent rule: nodes already spend it).
    plinths = [p for p in paths if p.pen().color().name().lower() == _PAL["border"].lower()]
    assert len(plinths) == 1, "exactly one border-pen plinth expected"
    plinth = plinths[0]
    assert plinth.brush().color().name().lower() == _PAL["surface_btn"].lower(), "plinth fill = surface_btn"
    assert plinth.pen().color().name().lower() != _PAL["accent"].lower(), "plinth must not wear the accent"
    # painted FIRST -> lowest in the stack -> LAST in the top-first items() list.
    assert items.index(plinth) == len(items) - 1, "the plinth must sit under every node and arrow"
    # and it must span the whole spine trio (Journey..Field), so the three read as one backbone.
    band = plinth.boundingRect()
    for i in conceptmap._SPINE:
        nx, ny = conceptmap._NODES[i][3], conceptmap._NODES[i][4]
        assert band.left() <= nx and band.right() >= nx + conceptmap._NW, f"node {i} not inside the plinth"
        assert band.top() <= ny and band.bottom() >= ny + conceptmap._NH
