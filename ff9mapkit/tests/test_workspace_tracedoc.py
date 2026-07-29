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
    assert doc._fg == [{"contact": (230.0, 320.0), "image": str(png), "frame_warn": None}]
    assert not doc.canvas._contact_mode and doc.canvas._trace_mode   # disarmed back to tracing
    assert "z 1073" in doc.status.text()
    assert "z 1073" in doc.fg_box.itemText(0) and "pillar.png" in doc.fg_box.itemText(0)
    assert len(doc.canvas._markers) == 1 and "z 1073" in doc.canvas._markers[0]["label"]
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
    assert doc._fg == [] and doc.canvas._markers == []
    doc.load_image(_photo(tmp_path))                                 # new art -> contacts void
    assert doc._fg == [] and not doc._history


def test_cutout_frame_mismatch_warns_the_playtest_case(app, tmp_path, monkeypatch):
    """The first playtest's exact miss: a 531x473 object snip attached over a 1536x1792 photo
    cover-crops to FILL the screen (a giant dog) — the attach warns with the re-export teach and
    the strip flags the row. Advisory, not a block (an equal-aspect vignette is legit)."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, _ = _doc(app)
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    doc.load_image(photo)
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    snip = tmp_path / "snip.png"
    Image.new("RGBA", (531, 473), (0, 0, 0, 255)).save(snip)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(snip))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    assert doc._fg[0]["frame_warn"] and "531x473" in doc._fg[0]["frame_warn"]
    assert "FILL the screen" in doc.status.text()
    assert "won't align" in doc.fg_box.itemText(0)
    assert doc.gen_btn.isEnabled()                       # advisory — Generate stays open


def test_equal_aspect_cutout_does_not_warn(app, tmp_path, monkeypatch):
    """Same frame at half resolution shares the aspect — cover-crop scales it back into perfect
    register, so no warn (the honest boundary of what the check can know)."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, _ = _doc(app)
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    doc.load_image(photo)
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    half = tmp_path / "half.png"
    Image.new("RGBA", (768, 896), (0, 0, 0, 0)).save(half)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(half))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    assert not doc._fg[0].get("frame_warn")
    assert "won't align" not in doc.fg_box.itemText(0)
