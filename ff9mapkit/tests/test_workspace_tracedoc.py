"""TraceDoc — click-authoring Rung 1's Workspace host (studies/click-authoring/PLAN.md).

Pins the host half: the ingest is the SAME cover-crop the build performs (a traced point is a
build canvas pixel), gestures gate Generate through the horizon re-judge, undo/clear are a
host-side history (set_floor never echoes), and Generate emits EXACTLY the CLI command the
retired HTML tracer emitted — through the run seam, band-checked by pack.check_custom_id.
The canvas mechanics live in test_workspace_backdrop.py; the math in test_imagefield.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                    # noqa: E402

from ff9mapkit.workspace.shell import pick_palette            # noqa: E402
from ff9mapkit.workspace.tracedoc import TraceDoc             # noqa: E402

KIT = Path(__file__).resolve().parents[1]                     # the ff9mapkit checkout dir


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


class _Run:
    """The run_job seam: records the argv + kwargs, reports 'started'."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        return True


def _doc(app):
    run = _Run()
    return TraceDoc(pick_palette("dark"), KIT, run=run), run


def _photo(tmp_path, size=(800, 600)):
    from PIL import Image
    p = tmp_path / "photo.png"
    Image.new("RGB", size, (90, 80, 70)).save(p)
    return p


def test_construction_is_pure(app):
    """No image, no trace: the canvas frames the bare 384x448 canvas at the default camera and
    Generate is disabled with the teaching tooltip."""
    doc, run = _doc(app)
    assert doc.canvas._scene.sceneRect().width() == 384
    assert not doc.gen_btn.isEnabled()
    assert "at least 3" in doc.gen_btn.toolTip()
    assert not run.calls


def test_load_image_is_the_build_crop(app, tmp_path):
    """An 800x600 photo lands as the exact 2x cover-crop (768x896) — never a stretch — and the
    scene frame stays the logical canvas. A new image clears any prior trace."""
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.canvas._commit_floor([(100, 300), (200, 300), (150, 400)])
    doc.load_image(_photo(tmp_path))
    assert (doc._pixmap.width(), doc._pixmap.height()) == (768, 896)
    assert doc.canvas._scene.sceneRect().width() == 384
    assert doc.canvas.floor() == [] and doc._floor == [] and not doc._history
    assert "photo.png" in doc.img_label.text()


def test_gestures_gate_generate(app, tmp_path):
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(100, 300), (280, 300)])
    assert not doc.gen_btn.isEnabled()                 # 2 vertices: not a polygon yet
    doc.canvas._commit_floor([(100, 300), (280, 300), (190, 430)])
    assert doc.gen_btn.isEnabled()
    assert "3 vertices traced" in doc.status.text()


def test_pitch_rejudges_the_trace(app, tmp_path):
    """Pitch 6 lifts the horizon to y~175: vertices at y=100 go bad, Generate gates off, the
    status counts them."""
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(100, 100), (280, 100), (280, 430), (100, 430)])
    assert doc.gen_btn.isEnabled()
    doc.pitch.setValue(6)
    assert not doc.gen_btn.isEnabled()
    assert "2 above the horizon" in doc.status.text()
    doc.pitch.setValue(26)
    assert doc.gen_btn.isEnabled()


def test_undo_and_clear_are_host_history(app, tmp_path):
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(100, 300)])
    doc.canvas._commit_floor([(100, 300), (280, 300)])
    doc.on_undo()
    assert doc._floor == [(100, 300)] and doc.canvas.floor() == [(100, 300)]
    doc.on_clear()
    assert doc._floor == [] and doc.canvas.floor() == []
    doc.on_undo()                                      # clear is one undoable gesture
    assert doc._floor == [(100, 300)]


def test_generate_emits_the_tracer_command(app, tmp_path, monkeypatch):
    """Parity with the HTML tracer's emitted command: the same `image-field` argv, streamed
    through the run seam with the kit as cwd; default pitch adds no --pitch flag."""
    pytest.importorskip("PIL")
    doc, run = _doc(app)
    img = _photo(tmp_path)
    doc.load_image(img)
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.name_box.setText("HALLWAY")
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert len(run.calls) == 1
    argv, kw = run.calls[0]
    assert argv == [sys.executable, "-m", "ff9mapkit", "image-field", str(img),
                    "--floor", "130,200 254,200 364,440 20,440",
                    "--out", str(tmp_path / "photo-field"),
                    "--name", "HALLWAY", "--id", "30777"]
    assert kw["cwd"] == str(KIT)
    assert "30777" in kw["ok_next"]                    # the deploy + warp receipt names the id


def test_generate_band_checks_the_id(app, tmp_path, monkeypatch):
    """The shared validator is SPENT (the round-13 id_field lesson): a real-band id never
    reaches the CLI."""
    pytest.importorskip("PIL")
    doc, run = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.id_box.setText("100")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert not run.calls
    assert "custom band" in doc.status.text()


def test_generate_cancelled_out_dialog_runs_nothing(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    doc, run = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    monkeypatch.setattr(doc, "_ask_out", lambda: None)
    doc.on_generate()
    assert not run.calls


def test_nondefault_pitch_reaches_the_argv(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    doc, run = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.pitch.setValue(35)
    doc.canvas._commit_floor([(130, 250), (254, 250), (364, 440), (20, 440)])
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _ = run.calls[0]
    assert argv[-2:] == ["--pitch", "35"]


def test_retheme_and_scale_reach_the_canvas(app):
    doc, _ = _doc(app)
    doc.retheme(pick_palette("light"))
    assert doc.canvas.pal is doc.pal
    doc.set_scale(150)
    assert doc.canvas._scale == 150


# ---------------------------------------------------------------- Rung 2: occluder cut-outs

def _cutout(tmp_path, name="pillar.png"):
    from PIL import Image
    p = tmp_path / name
    Image.new("RGBA", (800, 600), (0, 0, 0, 0)).save(p)   # the photo's own frame -> no aspect warn
    return p


def _traced(app, tmp_path):
    doc, run = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    return doc, run


def test_contact_records_the_proven_z_and_asks_for_the_png(app, tmp_path, monkeypatch):
    """The in-game-proven pillar contact: (230,320) at the default camera -> overlay z 1073.
    One undoable gesture; the attach dialog answers; the marker + strip carry the z."""
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    png = _cutout(tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.fg_btn.setChecked(True)
    assert doc.canvas._contact_mode
    doc._on_contact(230.0, 320.0)
    f = doc._fg[0]
    assert f["contact"] == (230.0, 320.0) and f["image"] == str(png)
    assert f["kind"] == "full" and f["offset"] is None    # photo-frame aspect -> registered
    assert not doc.canvas._contact_mode and doc.canvas._trace_mode   # disarmed back to tracing
    assert "z 1073" in doc.status.text()
    assert "z 1073" in doc.fg_box.itemText(0) and "pillar.png" in doc.fg_box.itemText(0)
    (cut,) = doc.canvas._cutouts
    assert "z 1073" in cut["label"] and cut["rect"] is None and cut["locked"]
    assert doc.gen_btn.isEnabled()


def test_contact_guard_refuses_up_the_body(app, tmp_path, monkeypatch):
    """The Z_BASE guard reaches the GUI with the CLI's own message: a pixel high on the canvas
    computes z >= 4000 and refuses — still armed for the retry, nothing recorded."""
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: None)
    doc.fg_btn.setChecked(True)
    doc._on_contact(192.0, 30.0)
    assert doc._fg == [] and doc.canvas._contact_mode                # refused, still armed
    assert "MEETS THE FLOOR" in doc.status.text()


def test_unattached_cutout_blocks_generate(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    doc, run = _traced(app, tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: None)            # Cancel: no PNG yet
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    assert not doc.gen_btn.isEnabled()
    assert "PNG" in doc.gen_btn.toolTip()
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert not run.calls                                             # belt AND suspenders
    png = _cutout(tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.on_fg_attach()
    assert doc.gen_btn.isEnabled()


def test_pitch_rejudges_contacts_like_vertices(app, tmp_path, monkeypatch):
    """A pitch change re-derives every anchored z (never stored stale); a contact the new camera
    cannot anchor flags invalid and gates Generate off."""
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    png = _cutout(tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 150.0)                                    # valid at pitch 26 (z 1656)
    assert doc.gen_btn.isEnabled()
    z26 = doc._fg_state(doc._fg[0])[0]
    doc.pitch.setValue(45)
    z45 = doc._fg_state(doc._fg[0])[0]
    assert z45 is not None and z45 != z26                            # derived per camera
    doc.pitch.setValue(6)                                            # horizon y~175: y=150 is sky now
    assert doc._fg_state(doc._fg[0])[1] is not None
    assert not doc.gen_btn.isEnabled() and "invalid" in doc.status.text()
    doc.pitch.setValue(26)
    assert doc.gen_btn.isEnabled()


def test_generate_emits_the_tracer_foreground_form(app, tmp_path, monkeypatch):
    """Parity with the retired tracer's emitted command: each cut-out rides as
    --foreground path@cx,cy (the anchored form parse_foreground_spec decodes)."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, run = _traced(app, tmp_path)
    png = _cutout(tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _kw = run.calls[0]
    i = argv.index("--foreground")
    spec = IF.parse_foreground_spec(argv[i + 1])
    assert spec == {"image": str(png), "z": None, "contact": (230.0, 320.0)}


def test_undo_walks_contact_gestures_and_new_image_clears_them(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    png = _cutout(tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    doc.on_fg_remove()
    assert doc._fg == []
    doc.on_undo()                                                    # undo the remove
    assert len(doc._fg) == 1 and doc._fg[0]["image"] == str(png)
    doc.on_undo()                                                    # undo the add
    assert doc._fg == [] and doc.canvas._cutouts == []
    doc.load_image(_photo(tmp_path))                                 # new art -> contacts void
    assert doc._fg == [] and not doc._history


def _snip_doc(app, tmp_path, monkeypatch, snip_size=(531, 473)):
    """A 1536x1792 photo traced, a snip of ``snip_size`` attached at the (230,320) contact."""
    from PIL import Image
    doc, run = _doc(app)
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    doc.load_image(photo)
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    snip = tmp_path / "snip.png"
    Image.new("RGBA", snip_size, (10, 20, 30, 255)).save(snip)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(snip))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    return doc, run, snip


def test_a_snip_becomes_a_positionable_overlay(app, tmp_path, monkeypatch):
    """The first playtest's 531x473 object crop, as a FEATURE: a non-photo-aspect attachment is
    a SNIP — previewed at its natural photo scale (531/4 x 473/4 canvas px on a 4x photo), its
    base parked on the contact, draggable, labelled in the strip."""
    pytest.importorskip("PIL")
    doc, _, _ = _snip_doc(app, tmp_path, monkeypatch)
    f = doc._fg[0]
    assert f["kind"] == "snip" and f["size"] == (531, 473)
    (cut,) = doc.canvas._cutouts
    x, y, w, h = cut["rect"]
    assert abs(w - 531 / 4) < 0.3 and abs(h - 473 / 4) < 0.3   # natural scale, never screen-fit
    assert abs((x + w / 2) - 230.0) < 0.6 and abs((y + h) - 320.0) < 0.6   # base on the contact
    assert not cut["locked"] and "snip" in doc.fg_box.itemText(0)
    assert "drag it into place" in doc.status.text()
    assert doc.gen_btn.isEnabled()


def test_dragging_a_snip_moves_its_anchor_and_rederives_z(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    doc, _, _ = _snip_doc(app, tmp_path, monkeypatch)
    f = doc._fg[0]
    ox, oy = f["offset"]
    z0 = doc._fg_state(f)[0]
    doc._on_cutout_moved(0, ox + 20.0, oy + 40.0)        # the canvas's one-per-gesture callback
    assert f["offset"] == (round(ox + 20.0, 1), round(oy + 40.0, 1))
    assert f["contact"] == (250.0, 360.0)                # the anchor rode along by the same delta
    assert doc._fg_state(f)[0] != z0                     # deeper contact -> a new derived z
    doc.on_undo()
    assert doc._fg[0]["contact"] == (230.0, 320.0)       # one undoable gesture
    doc._on_contact_moved(0, 240.0, 330.0)               # re-anchor ALONE: the image stays put
    assert doc._fg[0]["contact"] == (240.0, 330.0)
    assert doc._fg[0]["offset"] == (ox, oy)


def test_generate_composes_a_placed_snip_to_the_full_frame(app, tmp_path, monkeypatch):
    """The CLI contract is untouched: Generate writes the snip onto a transparent 1536x1792
    frame at its dragged spot (beside the source image, so the command re-runs) and the argv
    references the COMPOSED file at the anchored form."""
    pytest.importorskip("PIL")
    from PIL import Image
    from ff9mapkit import imagefield as IF
    doc, run, _ = _snip_doc(app, tmp_path, monkeypatch)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _kw = run.calls[0]
    spec = IF.parse_foreground_spec(argv[argv.index("--foreground") + 1])
    composed = Path(spec["image"])
    assert composed == tmp_path / "room.fg0.png" and spec["contact"] == (230.0, 320.0)
    im = Image.open(composed)
    assert im.size == (1536, 1792)
    ox, oy = doc._fg[0]["offset"]
    bx0, by0, bx1, by1 = im.getchannel("A").getbbox()
    assert abs(bx0 - ox * 4) <= 1 and abs(by0 - oy * 4) <= 1     # pasted at the dragged spot
    assert abs((bx1 - bx0) - 531) <= 1 and abs((by1 - by0) - 473) <= 1   # at natural photo scale


def test_photo_aspect_cutout_registers_full_frame(app, tmp_path, monkeypatch):
    """Same frame at half resolution shares the aspect — registered (locked, fills the frame),
    and Generate passes the ORIGINAL path untouched."""
    pytest.importorskip("PIL")
    doc, run, snip = _snip_doc(app, tmp_path, monkeypatch, snip_size=(768, 896))
    f = doc._fg[0]
    assert f["kind"] == "full" and f["offset"] is None
    (cut,) = doc.canvas._cutouts
    assert cut["rect"] is None and cut["locked"]
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _kw = run.calls[0]
    assert argv[argv.index("--foreground") + 1].startswith(str(snip))


def test_generate_is_in_place_after_the_first_run(app, tmp_path, monkeypatch):
    """Set up once, then every Generate rebuilds the SAME project with no dialog (owner-asked):
    the second run must not even CALL _ask_out, and the button says so."""
    pytest.importorskip("PIL")
    doc, run = _traced(app, tmp_path)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert doc._project and doc._project["out"] == str(tmp_path / "photo-field")
    assert doc.gen_btn.text().startswith("Regenerate")
    monkeypatch.setattr(doc, "_ask_out",
                        lambda: (_ for _ in ()).throw(AssertionError("asked again")))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 445)])   # an edit
    doc.on_generate()
    assert len(run.calls) == 2
    a1, a2 = run.calls[0][0], run.calls[1][0]
    assert a1[a1.index("--out") + 1] == a2[a2.index("--out") + 1]   # the same project dir
    doc.load_image(_photo(tmp_path))                               # a new photo = a new project
    assert doc._project is None and doc.gen_btn.text().startswith("Generate")


def test_trace_sidecar_round_trips_the_session(app, tmp_path, monkeypatch):
    """Generate writes <out>/<stem>.trace.json; opening it on a FRESH tab restores the photo,
    floor, pitch, cut-outs (with their dragged offsets), name/id — and the project, so the
    next Generate goes straight in place."""
    pytest.importorskip("PIL")
    import json
    doc, run, snip = _snip_doc(app, tmp_path, monkeypatch)
    doc._on_cutout_moved(0, 100.0, 200.0)                          # a dragged spot to survive
    doc.pitch.setValue(21)
    doc.name_box.setText("HALL2")
    doc.id_box.setText("30778")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    side = tmp_path / "room-field" / "room.trace.json"
    assert side.is_file()
    data = json.loads(side.read_text(encoding="utf-8"))
    assert data["name"] == "HALL2" and data["id"] == "30778" and data["pitch"] == 21
    assert data["fg"][0]["offset"] == [100.0, 200.0]

    doc2, run2 = _doc(app)
    doc2.load_trace(side)
    assert doc2._floor == doc._floor and doc2.pitch.value() == 21
    assert doc2._fg[0]["kind"] == "snip" and doc2._fg[0]["offset"] == (100.0, 200.0)
    assert doc2.name_box.text() == "HALL2" and doc2.id_box.text() == "30778"
    assert doc2.gen_btn.text().startswith("Regenerate HALL2")
    monkeypatch.setattr(doc2, "_ask_out",
                        lambda: (_ for _ in ()).throw(AssertionError("asked on a reopen")))
    doc2.on_generate()
    argv, _kw = run2.calls[0]
    assert argv[argv.index("--out") + 1] == str(tmp_path / "room-field")


@pytest.fixture(autouse=True)
def _deterministic_qt_teardown(qt_drain):
    """Widgets die HERE, not in a forced GC pass (THE GC-CHILD LAW's teardown half)."""
    yield
    qt_drain()
