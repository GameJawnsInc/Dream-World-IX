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

pytest.importorskip("PySide6")

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


def _built_project(tmp_path, with_fg=True, **cam):
    """A REAL compiled image-field project (the offline builder itself), pre-sidecar.
    ``cam`` forwards pitch/fov/distance overrides to the builder (default pitch 21)."""
    from PIL import Image
    from ff9mapkit import imagefield as IF
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    fg = []
    if with_fg:
        fgp = tmp_path / "pillar.png"
        Image.new("RGBA", (1536, 1792), (0, 0, 0, 0)).save(fgp)
        fg = [f"{fgp}@159.2,202.9"]
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    man = IF.build_image_field(photo, floor, tmp_path / "proj", foreground=fg,
                               name="HALL3", field_id=30779, **{"pitch": 21, **cam})
    return Path(man["toml"]), floor


def test_open_field_toml_backfills_the_session(app, tmp_path, monkeypatch):
    """A PRE-SIDECAR project reopens from its field.toml alone: the floor comes back through
    the -48u outset inversion (within ~a pixel of the original trace), the pitch from the
    camera block, the contact from the generator's own comment, and in-place Generate is
    armed — the owner's 'why didn't it load my scene' gap."""
    pytest.importorskip("PIL")
    toml, floor = _built_project(tmp_path)
    doc, run = _doc(app)
    doc.load_project(toml)
    assert doc.pitch.value() == 21
    assert doc.name_box.text() == "HALL3" and doc.id_box.text() == "30779"
    assert len(doc._floor) == 4
    for ex, ey in floor:                             # order/start-vertex agnostic: nearest match
        assert min(abs(gx - ex) + abs(gy - ey) for gx, gy in doc._floor) < 1.5
    assert doc._fg[0]["contact"] == (159.2, 202.9)
    assert doc._fg[0]["kind"] == "full"              # the shipped fg is the composed full frame
    assert "z" in doc.fg_box.itemText(0)
    monkeypatch.setattr(doc, "_ask_out",
                        lambda: (_ for _ in ()).throw(AssertionError("asked on a reopen")))
    doc.on_generate()
    argv, _kw = run.calls[0]
    assert argv[argv.index("--out") + 1] == str(tmp_path / "proj")
    assert (tmp_path / "proj" / "base.trace.json").is_file()   # the record exists from now on


def test_open_field_toml_prefers_the_sidecar(app, tmp_path, monkeypatch):
    """With a session record present, the field.toml route loads IT (dragged offsets and all)
    instead of rebuilding from compiled artifacts."""
    pytest.importorskip("PIL")
    import json
    toml, _floor = _built_project(tmp_path, with_fg=False)
    photo = tmp_path / "room.png"
    (toml.parent / "room.trace.json").write_text(json.dumps({
        "image": str(photo), "pitch": 33, "floor": [[10, 300], [200, 300], [100, 430]],
        "fg": [], "name": "SIDECAR", "id": "30780"}), encoding="utf-8")
    doc, _run = _doc(app)
    doc.load_project(toml)
    assert doc.pitch.value() == 33 and doc.name_box.text() == "SIDECAR"
    assert doc._floor == [(10, 300), (200, 300), (100, 430)]


def test_offer_project_autoloads_when_pristine_and_offers_when_busy(app, tmp_path, monkeypatch):
    """The shell's tab-show feed: a PRISTINE tab auto-loads the open field's project (the
    owner-asked best case); a tab mid-session gets a one-click button instead of a clobber;
    a non-project toml is refused once and remembered."""
    pytest.importorskip("PIL")
    toml, _floor = _built_project(tmp_path)
    doc, _run = _doc(app)
    doc.offer_project(toml)                            # pristine -> straight in
    assert doc.name_box.text() == "HALL3" and len(doc._floor) == 4
    assert not doc.offer_btn.isVisible()

    doc2, _ = _doc(app)
    doc2.load_image(_photo(tmp_path))                  # mid-session now
    doc2.canvas._commit_floor([(100, 300), (200, 300), (150, 400)])
    doc2.show()
    doc2.offer_project(toml)
    assert doc2.offer_btn.isVisible() and "HALL3" in doc2.offer_btn.text()
    doc2.on_offer()                                    # the click loads it
    assert doc2.name_box.text() == "HALL3"

    doc3, _ = _doc(app)
    plain = tmp_path / "plain.field.toml"
    plain.write_text('[field]\nid = 4003\nname = "X"\narea = 11\n', encoding="utf-8")
    doc3.offer_project(plain)                          # not traceable -> quietly stays empty
    assert doc3._image is None and doc3._offer_rejected == str(plain)
    doc3.offer_project(plain)                          # remembered: no re-parse, still quiet
    assert doc3._image is None


def test_unstamped_changes_warn_until_regenerate(app, tmp_path, monkeypatch):
    """Edits after a Generate flag the status until the project is re-stamped."""
    pytest.importorskip("PIL")
    doc, run = _traced(app, tmp_path)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert "not stamped" not in doc.status.text()
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 445)])
    assert "not stamped" in doc.status.text() and "Regenerate" in doc.status.text()
    doc.on_generate()
    assert "not stamped" not in doc.status.text()


# --------------------------------------------------------------------------- rung 4: regions
def _traced_doc(app, tmp_path):
    doc, run = _doc(app)
    doc.resize(760, 700)
    doc.show()                                       # visibility asserts need a shown top-level
    QApplication.processEvents()
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    return doc, run


def test_tool_strip_owns_the_click_semantics(app, tmp_path):
    pytest.importorskip("PIL")
    doc, _ = _traced_doc(app, tmp_path)
    assert doc.tools.current() == "floor" and doc.canvas._trace_mode
    doc.tools.set_current("cutout")
    assert doc.canvas._contact_mode and not doc.canvas._trace_mode
    doc.tools.set_current("regions")
    assert doc.canvas._region_mode and not doc.canvas._contact_mode
    assert doc.rkind_btns["gateway"].isVisible() and doc.gw_to.isVisible()
    doc.rkind_btns["event"].setChecked(True)
    assert not doc.gw_to.isVisible() and doc.ev_msg.isVisible()
    doc.tools.set_current("floor")
    assert doc.canvas._trace_mode and not doc.rkind_btns["event"].isVisible()


def test_a_drawn_region_is_stored_in_canvas_px_and_reaches_the_argv(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, run = _traced_doc(app, tmp_path)
    doc.tools.set_current("regions")
    doc.gw_to.setValue(4005)
    doc.gw_ent.setValue(2)
    cam = doc.canvas.camera()
    quad_px = [(60.0, 300.0), (140.0, 300.0), (140.0, 330.0), (60.0, 330.0)]
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in quad_px])
    assert len(doc._regions) == 1
    got = doc._regions[0]
    assert got["kind"] == "gateway" and got["to"] == 4005 and got["entrance"] == 2
    for (gx, gy), (ex, ey) in zip(got["quad"], quad_px):
        assert abs(gx - ex) < 0.2 and abs(gy - ey) < 0.2   # the px round-trip is the tripwire's
    assert len(doc.canvas._regions) == 1                   # fed back, judged
    doc.rkind_btns["event"].setChecked(True)
    doc.ev_msg.setText("Watch the ledge")
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(200.0, 340.0), (300.0, 340.0), (300.0, 380.0), (200.0, 380.0)]])
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _kw = run.calls[0]
    gi = argv.index("--gateway")
    assert argv[gi + 1] == "4005,2@60,300;140,300;140,330;60,330"
    ei = argv.index("--event-zone")
    assert argv[ei + 1] == "Watch the ledge@200,340;300,340;300,380;200,380"
    # the sidecar round-trips the whole region session
    doc2, _ = _doc(app)
    doc2.load_trace(tmp_path / "photo-field" / "photo.trace.json")
    assert [r["kind"] for r in doc2._regions] == ["gateway", "event"]
    assert doc2._regions[0]["quad"][0] == (60.0, 300.0)
    assert doc2._regions[1]["message"] == "Watch the ledge"


def test_region_gestures_are_undoable_and_reshape_by_row(app, tmp_path):
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _traced_doc(app, tmp_path)
    doc.tools.set_current("regions")
    cam = doc.canvas.camera()
    px = [(60.0, 300.0), (140.0, 300.0), (140.0, 330.0), (60.0, 330.0)]
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in px])
    moved = [(70.0, 300.0), (150.0, 300.0), (150.0, 330.0), (70.0, 330.0)]
    doc._on_region_changed(0, [IF.click_to_world(cam, p) for p in moved])
    assert abs(doc._regions[0]["quad"][0][0] - 70.0) < 0.2
    doc.on_undo()                                          # back to the drawn spot
    assert abs(doc._regions[0]["quad"][0][0] - 60.0) < 0.2
    doc._on_region_deleted(0)
    assert doc._regions == []
    doc.on_undo()
    assert len(doc._regions) == 1                          # the delete walks back too


def test_open_field_toml_backfills_regions(app, tmp_path, monkeypatch):
    """A compiled photo project's [[gateway]]/[[event]] world zones invert to the session's
    canvas px through the project's own camera (the doubled 5th point dropped)."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    img = _photo(tmp_path)
    man = IF.build_image_field(
        img, [(130, 200), (254, 200), (364, 440), (20, 440)], tmp_path / "photo-field",
        gateways=["4005@60,300;140,300;140,330;60,330"],
        events=[{"message": "hi", "zone_px": [(200, 340), (300, 340), (300, 380), (200, 380)]}])
    doc, _ = _doc(app)
    doc.load_project(man["toml"])
    kinds = [r["kind"] for r in doc._regions]
    assert kinds == ["gateway", "event"]
    assert doc._regions[0]["to"] == 4005
    assert doc._regions[1]["message"] == "hi"
    gx, gy = doc._regions[0]["quad"][0]
    assert abs(gx - 60.0) < 1.0 and abs(gy - 300.0) < 1.0  # world ints -> sub-px inversion


def test_a_targetless_door_gates_generate_until_retargeted(app, tmp_path, monkeypatch):
    """The Field(0) black-screen playtest lesson: a door drawn before the 'to field' box was
    set (it feeds NEW draws only) blocks Generate until the quad's own menu retargets it."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, run = _traced_doc(app, tmp_path)
    doc.tools.set_current("regions")
    assert doc.gw_to.value() == 0                          # the box starts unset
    cam = doc.canvas.camera()
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(60.0, 300.0), (140.0, 300.0), (140.0, 330.0), (60.0, 330.0)]])
    assert "set its target field id" in doc.status.text()  # the immediate draw note teaches
    doc._refresh()
    assert "without a target" in doc.status.text()         # …and the standing count persists
    assert not doc.gen_btn.isEnabled()                     # the softlock never ships
    assert doc.canvas._regions[0]["warn"] and "NO TARGET" in doc.canvas._regions[0]["warn"]
    monkeypatch.setattr(doc, "_ask_field_id", lambda cur: 301)
    doc._on_region_retarget(0)                             # the quad menu's Set gateway target
    assert doc._regions[0]["to"] == 301
    assert doc.gen_btn.isEnabled()
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _kw = run.calls[0]
    assert argv[argv.index("--gateway") + 1].startswith("301@")
    doc.on_undo()                                          # the retarget is a normal gesture
    assert doc._regions[0]["to"] == 0


def test_a_drawn_event_rewords_in_place(app, tmp_path, monkeypatch):
    """The photo lane regenerates its toml, so a drawn zone's words live in the SESSION —
    the quad menu's Set message is the only editor for them."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _traced_doc(app, tmp_path)
    doc.tools.set_current("regions")
    doc.rkind_btns["event"].setChecked(True)
    cam = doc.canvas.camera()
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(200.0, 340.0), (300.0, 340.0), (300.0, 380.0), (200.0, 380.0)]])
    assert doc._regions[0]["message"] == "..."             # the default placeholder
    assert doc.canvas._regions[0]["warn"] and "placeholder" in doc.canvas._regions[0]["warn"]
    monkeypatch.setattr(doc, "_ask_message", lambda cur: "It creaks underfoot.")
    doc._on_region_reword(0)
    assert doc._regions[0]["message"] == "It creaks underfoot."
    assert doc.canvas._regions[0]["warn"] is None          # the warn clears with the words
    doc.on_undo()                                          # a normal, undoable gesture
    assert doc._regions[0]["message"] == "..."


# ---------------------------------------------------------------------------- the session rig
# A project generated at a non-default distance/fov used to reopen through the DEFAULT rig --
# tracedoc._camera hardcoded DEFAULT_DISTANCE/DEFAULT_FOV -- so every inverted coordinate was
# wrong with no exception (PLAN.md rung 7's standing bug). The session now carries the pose.

def test_load_project_restores_the_projects_own_rig(app, tmp_path, monkeypatch):
    """A project shot at distance 6000 / fov 39 reopens through ITS camera: the floor inversion
    still lands on the original trace, and a Regenerate passes the rig back to the CLI."""
    pytest.importorskip("PIL")
    toml, floor = _built_project(tmp_path, with_fg=False, distance=6000.0, fov=39.0)
    doc, run = _doc(app)
    doc.load_project(toml)
    assert doc._distance == 6000.0 and doc._fov == 39.0
    for ex, ey in floor:                             # wrong-rig inversion misses by tens of px
        assert min(abs(gx - ex) + abs(gy - ey) for gx, gy in doc._floor) < 1.5
    assert "distance 6000" in doc.pitch_label.text() and "fov 39" in doc.pitch_label.text()
    monkeypatch.setattr(doc, "_ask_out",
                        lambda: (_ for _ in ()).throw(AssertionError("asked on a reopen")))
    doc.on_generate()
    argv, _kw = run.calls[0]
    assert argv[argv.index("--fov") + 1] == "39"
    assert argv[argv.index("--distance") + 1] == "6000"


def test_a_fresh_photo_resets_to_the_default_rig(app, tmp_path, monkeypatch):
    """Opening a NEW image after a custom-rig project must not leak the old pose into the new
    project -- and a default-rig session emits no --fov/--distance at all (argv parity with
    the retired HTML tracer)."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    toml, _floor = _built_project(tmp_path, with_fg=False, distance=6000.0, fov=39.0)
    doc, run = _doc(app)
    doc.load_project(toml)
    doc.load_image(_photo(tmp_path))
    assert doc._distance == IF.DEFAULT_DISTANCE and doc._fov == IF.DEFAULT_FOV
    doc.canvas._commit_floor([(100, 300), (200, 300), (150, 400)])
    doc.id_box.setText("30781")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _kw = run.calls[-1]
    assert "--fov" not in argv and "--distance" not in argv


def test_trace_sidecar_round_trips_the_rig(app, tmp_path, monkeypatch):
    """The .trace.json records distance/fov and a reopen restores them; a LEGACY sidecar
    without the keys falls back to the defaults instead of crashing."""
    pytest.importorskip("PIL")
    import json
    from ff9mapkit import imagefield as IF
    doc, run = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc._distance, doc._fov = 5200.0, 40.0             # as a custom-rig reopen would set
    doc.canvas._commit_floor([(100, 300), (200, 300), (150, 400)])
    doc.id_box.setText("30782")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    side = tmp_path / "photo-field" / "photo.trace.json"
    data = json.loads(side.read_text(encoding="utf-8"))
    assert data["distance"] == 5200.0 and data["fov"] == 40.0
    doc2, _run2 = _doc(app)
    doc2.load_trace(side)
    assert doc2._distance == 5200.0 and doc2._fov == 40.0
    del data["distance"], data["fov"]                  # a pre-rig sidecar
    side.write_text(json.dumps(data), encoding="utf-8")
    doc3, _run3 = _doc(app)
    doc3.load_trace(side)
    assert doc3._distance == IF.DEFAULT_DISTANCE and doc3._fov == IF.DEFAULT_FOV


def test_load_project_refuses_a_composed_floorplan_room(app, tmp_path):
    """A floorplan-composed room's shape is owned by its plan -- re-tracing it would fork the
    truth, so the load refuses NAMING the owning tab, and the shell's auto-load offer stays a
    quiet rejection (the pristine-tab path swallows the message by design)."""
    pytest.importorskip("PIL")
    from PIL import Image
    from ff9mapkit import floorplan as FP
    room = tmp_path / "dungeon" / "ROOM1"
    (room / "art").mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(room / "art" / "back.png")
    (room / "room1.field.toml").write_text(
        '[field]\nid = 30500\nname = "ROOM1"\narea = 11\n'
        '[camera]\npitch = 48.0\ndistance = 2200\nfov = 42.2\nrange = [384, 448]\n'
        '[walkmesh]\nobj = "walkmesh.obj"\nframe = "world"\n'
        '[[layers]]\nimage = "art/back.png"\nz = 4000\n', encoding="utf-8")
    (tmp_path / "dungeon" / FP.SIDECAR).write_text("{}", encoding="utf-8")
    doc, _run = _doc(app)
    with pytest.raises(ValueError, match="Floorplan"):
        doc.load_project(room / "room1.field.toml")
    assert doc._image is None                          # refused BEFORE any state landed
    doc.offer_project(room / "room1.field.toml")       # the shell feed: quiet, remembered
    assert doc._image is None
    assert doc._offer_rejected == str(room / "room1.field.toml")


def test_load_project_refuses_scrolling_rooms_and_poseless_forks(app, tmp_path):
    """A scrolling room's frame is wider than the Trace canvas's fixed 384x448; a fork with no
    [camera] pose would re-project through a camera it never had. Both refuse with the teach."""
    pytest.importorskip("PIL")
    from PIL import Image
    proj = tmp_path / "wide"
    (proj / "art").mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(proj / "art" / "back.png")
    head = ('[walkmesh]\nobj = "walkmesh.obj"\nframe = "world"\n'
            '[[layers]]\nimage = "art/back.png"\nz = 4000\n')
    wide = proj / "wide.field.toml"
    wide.write_text('[field]\nid = 30501\nname = "WIDE"\narea = 11\n'
                    '[camera]\npitch = 48.0\ndistance = 2200\nfov = 42.2\n'
                    'range = [960, 448]\nwindow_width = 384\n'
                    '[camera.scroll]\nenabled = true\n' + head, encoding="utf-8")
    doc, _run = _doc(app)
    with pytest.raises(ValueError, match="scrolling"):
        doc.load_project(wide)
    fork = proj / "fork.field.toml"
    fork.write_text('[field]\nid = 30502\nname = "FORK"\narea = 11\n' + head, encoding="utf-8")
    with pytest.raises(ValueError, match="pose"):
        doc.load_project(fork)


def test_load_project_absorbs_only_the_generators_own_regions(app, tmp_path):
    """A Place-drawn door on a generated project stays FILE-side (the regenerate merge
    preserves it verbatim); only traced_ rows join the editable session -- one claim rule,
    owned by imagefield.is_generated_region, spent by both the merge and this absorb."""
    pytest.importorskip("PIL")
    from PIL import Image
    from ff9mapkit import imagefield as IF
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    man = IF.build_image_field(photo, floor, tmp_path / "proj", name="HALL4", field_id=30783,
                               gateways=["4005@60,300;140,300;140,330;60,330"])
    toml = Path(man["toml"])
    toml.write_text(toml.read_text(encoding="utf-8") + (
        '\n[[gateway]]\nname = "door0"\nto = 301\nzone = [[-500, 900], [-400, 900], '
        '[-400, 1000], [-500, 1000]]\n'), encoding="utf-8")
    doc, _run = _doc(app)
    doc.load_project(toml)
    assert len(doc._regions) == 1                      # the traced door alone
    assert doc._regions[0]["to"] == 4005
