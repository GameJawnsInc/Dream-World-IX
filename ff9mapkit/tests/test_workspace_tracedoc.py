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
    assert "3 vertices" in doc.ins_floor.text()         # the tally lives in the Inspector (T41)
    assert doc.status.text() == "Generate the field project."   # the status: the next step


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


_BOWTIE = [(100, 300), (280, 440), (280, 300), (100, 440)]


def test_a_crossed_outline_gates_generate_and_says_which_sides(app, tmp_path, monkeypatch):
    """Finding T5: a crossed outline walked through to a walkmesh over floor nobody traced. The tab
    asks the build's own rule and says which sides cross; Generate refuses with that sentence."""
    pytest.importorskip("PIL")
    doc, run = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor(_BOWTIE)
    assert not doc.gen_btn.isEnabled()
    want = "the side from vertex 0 to 1 crosses the side from vertex 2 to 3"
    assert want in doc.gen_btn.toolTip()
    assert doc.status.text().startswith("⚠") and want in doc.status.text()
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert run.calls == [] and want in doc.status.text()
    assert doc.status.property("state") == "error"
    doc.canvas._commit_floor([(100, 300), (280, 300), (280, 440), (100, 440)])   # untangled
    assert doc.gen_btn.isEnabled() and "crosses" not in doc.status.text()


def test_a_floor_too_narrow_to_walk_gates_generate_and_names_the_vertex(app, tmp_path,
                                                                        monkeypatch):
    """Final review of batch 4: the build refuses a notch narrower than the walk margin, and the
    canvas then draws no walk edge -- but the tab's gate asked only the crossed-outline rule, so
    the dashed ring vanished without a word and Generate failed in the job. One rule decides the
    ring, the gate and the status."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, run = _doc(app)
    doc.load_image(_photo(tmp_path))
    cam = doc.canvas.camera()
    slit = [(-600, 800), (600, 800), (600, 2000), (30, 2000), (30, 1000), (-30, 1000),
            (-30, 2000), (-600, 2000)]
    doc.canvas._commit_floor([IF.world_to_click(cam, p) for p in slit])
    assert not [it for it in doc.canvas._scene.items() if it.data(0) == "outset"]
    assert not doc.gen_btn.isEnabled(), "Generate is offered on a floor the build refuses"
    assert "too narrow near vertex" in doc.gen_btn.toolTip()
    assert doc.status.text().startswith("⚠") and "too narrow near vertex" in doc.status.text()
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert run.calls == []
    wide = [(-600, 800), (600, 800), (600, 2000), (200, 2000), (200, 1000), (-200, 1000),
            (-200, 2000), (-600, 2000)]
    doc.canvas._commit_floor([IF.world_to_click(cam, p) for p in wide])
    assert doc.gen_btn.isEnabled() and "narrow" not in doc.status.text()
    assert [it for it in doc.canvas._scene.items() if it.data(0) == "outset"]


def test_a_session_saved_with_a_crossed_outline_still_opens_to_be_repaired(app, tmp_path):
    """The new rule must not lock out a session recorded before it: it reopens, armed, and only
    Generate refuses -- with the sentence that says what to fix."""
    pytest.importorskip("PIL")
    import json
    photo = _photo(tmp_path)
    side = tmp_path / "proj" / "photo.trace.json"
    side.parent.mkdir()
    side.write_text(json.dumps({"image": str(photo), "upright": True, "pitch": 26,
                                "floor": [list(p) for p in _BOWTIE], "name": "OLD",
                                "id": "30790"}), encoding="utf-8")
    doc, _run = _doc(app)
    doc.load_trace(side)
    assert doc._floor == _BOWTIE and doc._project is not None
    assert "crosses" in doc.status.text() and not doc.gen_btn.isEnabled()


def test_an_off_frame_horizon_says_where_it_is(app, tmp_path):
    """Finding T27: at the default pitch the horizon sits just above the frame, so no dashed line
    is drawn -- while the pitch tooltip and the empty-state teach both pointed at one. The readout
    says how far off it is, the canvas marks the top edge with that distance, and the teach no
    longer presumes a visible line."""
    pytest.importorskip("PIL")
    from ff9mapkit.scene import cam as C
    doc, _ = _doc(app)
    doc.load_image(_photo(tmp_path))
    hy = C.horizon_canvas_y(doc.canvas.camera())
    assert hy < 0                                       # the premise: the default is above
    far = f"↑ horizon {max(1, round(-hy))} px"         # short: the plate sits on the art
    assert doc.pitch_label.text().endswith(f"horizon {max(1, round(-hy))} px above")
    tags = {it.data(0) for it in doc.canvas._scene.items()}
    assert "horizonedge" in tags and "horizon" not in tags
    assert any(far in lab["text"].text() for lab in doc.canvas._labels)
    assert "below the dashed horizon" not in doc.status.text()
    assert "readout" in doc.pitch.toolTip()
    doc.pitch.setValue(10)                              # on the frame: the line, not the mark
    tags = {it.data(0) for it in doc.canvas._scene.items()}
    assert "horizon" in tags and "horizonedge" not in tags
    assert "horizon y" in doc.pitch_label.text()


def test_the_undo_tooltip_says_a_pitch_change_is_not_undone(app):
    """Finding T11: Undo walks gestures, not the pitch slider -- moving the pitch and pressing
    Undo takes back the last vertex instead. The tooltip says so."""
    doc, _ = _doc(app)
    tip = doc.undo_btn.toolTip()
    assert "pitch" in tip.lower() and "not" in tip


def test_a_refused_region_reshape_says_why(app, tmp_path):
    """A reshape whose corner lands behind the camera keeps the old zone; it used to say nothing."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _traced_doc(app, tmp_path)
    doc.tools.set_current("regions")
    doc.gw_to.setValue(4005)
    cam = doc.canvas.camera()
    quad = [IF.click_to_world(cam, p) for p in
            [(60.0, 300.0), (140.0, 300.0), (140.0, 330.0), (60.0, 330.0)]]
    doc._on_region_drawn(quad)
    before, steps = [list(r["quad"]) for r in doc._regions], len(doc._history)
    behind = list(quad)
    behind[2] = (0.0, -1.0e7)                         # a corner far behind the camera
    doc._on_region_changed(0, behind)
    assert [r["quad"] for r in doc._regions] == before and len(doc._history) == steps
    assert "kept" in doc.status.text() and doc.status.property("state") == "warn"


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
                    "--name=HALLWAY", "--id", "30777"]
    assert kw["cwd"] == str(KIT)
    # finding T22: the next step is the app's own Deploy, not an unquoted terminal line (tools/
    # exists only in a checkout; the installed project folder has a space in it). The warp id is
    # the deploy verdict's to name: a Build-tab test slot overrides the field's own id.
    assert "Deploy (F9)" in kw["ok_next"] and "deploy_field.py" not in kw["ok_next"]
    assert "30777" not in kw["ok_next"]


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


def _fg_tip(doc, i):
    from PySide6.QtCore import Qt
    return str(doc.fg_box.itemData(i, Qt.ItemDataRole.ToolTipRole) or "")


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
    assert "pillar.png" in doc.fg_box.itemText(0) and "z 1073" in _fg_tip(doc, 0)
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


@pytest.mark.parametrize("name,size,full", [("snip@2x.png", (531, 473), False),
                                            ("frame@2x.png", (768, 896), True)])
def test_a_cut_out_named_at_2x_previews_at_its_real_size(app, tmp_path, monkeypatch, name, size,
                                                         full):
    """Finding V1: Qt loads a file named '...@2x.png' with device pixel ratio 2, so the canvas drew
    the snip at half its rect (a full frame at a quarter of the frame) while the build ships the
    file's real size. The preview must cover exactly the rect the build will use."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, _run, _ = _snip_doc(app, tmp_path, monkeypatch)
    png = tmp_path / name
    Image.new("RGBA", size, (10, 20, 30, 128)).save(png)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.on_fg_attach()
    f = doc._fg[0]
    assert f["pm"].devicePixelRatio() == 1
    (item,) = [it for it in doc.canvas._scene.items() if it.data(0) == "cutoutimg"]
    got = item.sceneBoundingRect()
    if full:
        want = (0.0, 0.0, 384.0, 448.0)
    else:
        (cut,) = doc.canvas._cutouts
        want = cut["rect"]
    assert all(abs(a - b) < 0.6 for a, b in
               zip((got.x(), got.y(), got.width(), got.height()), want)), (got, want)


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


@pytest.mark.parametrize("mode,fill", [("RGB", (90, 80, 70)), ("RGBA", (90, 80, 70, 255))])
def test_a_cut_out_with_no_transparent_pixels_is_warned_at_attach(app, tmp_path, monkeypatch,
                                                                  mode, fill):
    """Finding T21: an un-erased copy of the photo (no alpha, or alpha all 255) was accepted as a
    full-frame occluder: in the game it hides the actor everywhere behind the contact line."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, _ = _traced(app, tmp_path)
    png = tmp_path / "copy.png"
    Image.new(mode, (800, 600), fill).save(png)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    assert doc._fg[0]["image"] == str(png)             # attached (it may be meant), but said
    said = doc.status.text()
    assert said.startswith("⚠") and "no transparent pixels" in said
    assert doc.status.property("state") == "warn"
    doc.on_fg_attach()                                 # the Attach route says it too
    assert "no transparent pixels" in doc.status.text()
    assert doc.status.property("state") == "warn"


def test_a_cut_out_with_transparency_is_not_warned(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(_cutout(tmp_path)))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    assert "transparent" not in doc.status.text() and doc.status.property("state") != "warn"


def test_an_unreadable_cut_out_is_said_not_swallowed(app, tmp_path, monkeypatch):
    """Finding T20: Image.open on a corrupt PNG raised inside the Qt slot, with no hook to show it
    -- the contact stayed unattached and nothing was said. Both attach routes now say what failed,
    and Attach leaves no Undo step behind for a gesture that did nothing."""
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    bad = tmp_path / "broken.png"
    bad.write_bytes(b"not a png at all")
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(bad))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)                      # the contact itself is good: it stays
    assert len(doc._fg) == 1 and not doc._fg[0].get("image")
    assert "Could not read broken.png" in doc.status.text()
    assert doc.status.property("state") == "error"
    steps = len(doc._history)
    doc._project, doc._stamped = {"out": str(tmp_path), "name": "P", "fid": 30777}, True
    doc.on_fg_attach()                                 # (as if a Generate had just stamped it)
    assert len(doc._history) == steps and not doc._fg[0].get("image")
    assert "Could not read broken.png" in doc.status.text()
    assert doc.status.property("state") == "error"
    assert "not stamped" not in doc.status.text()      # a gesture that did nothing changed nothing


def test_a_placed_cut_out_that_cannot_be_written_beside_the_photo_is_said(app, tmp_path,
                                                                         monkeypatch):
    """Finding T20: Generate writes a placed snip's composed frame beside the photo. A folder it
    cannot write to (a mounted share) raised inside the slot: nothing started and nothing said."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, run, _ = _snip_doc(app, tmp_path, monkeypatch)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))

    def refuse(self, fp, *a, **k):
        raise PermissionError(13, "Access is denied", str(fp))
    monkeypatch.setattr(Image.Image, "save", refuse)
    doc.on_generate()
    assert run.calls == [] and doc._project is None
    assert "fg0" in doc.status.text() and "Access is denied" in doc.status.text()
    assert doc.status.property("state") == "error"


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


@pytest.mark.parametrize("size", [(1536, 1792), (384, 448)])
def test_a_cut_out_made_in_the_builds_frame_registers_full_frame(app, tmp_path, monkeypatch,
                                                                 size):
    """Finding T14: the picker, the CLI help and the old tracer all say to make the cut-out at
    the full canvas, and the build fills the frame with it 1:1 -- but on a 4:3 photo the tab read
    such a PNG as a snip and shrank it. The build's own 384:448 frame registers too; the photo's
    aspect still does (the owner's rule: same aspect as the photo = aligned)."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, run = _traced(app, tmp_path)                  # an 800x600 (4:3) photo
    png = tmp_path / "frame.png"
    Image.new("RGBA", size, (0, 0, 0, 0)).save(png)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    f = doc._fg[0]
    assert f["kind"] == "full" and f["offset"] is None
    (cut,) = doc.canvas._cutouts
    assert cut["rect"] is None and cut["locked"]
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv, _kw = run.calls[0]
    assert argv[argv.index("--foreground") + 1].startswith(str(png))   # passed through untouched


@pytest.mark.parametrize("size", [(60, 70), (120, 140), (385, 448), (400, 466)])
def test_a_small_crop_that_only_shares_the_frames_shape_stays_a_snip(app, tmp_path, monkeypatch,
                                                                     size):
    """Final review of T14: registering by ASPECT made a 60x70 crop of a lamp a full-frame layer
    that the build stretches over the whole room. Only a PNG of the frame's own size (384x448 or
    a whole multiple) is the frame; the photo-aspect rule is the owner's and is unchanged."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, _run = _traced(app, tmp_path)                 # an 800x600 (4:3) photo
    png = tmp_path / "lamp.png"
    Image.new("RGBA", size, (10, 20, 30, 128)).save(png)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(png))
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    f = doc._fg[0]
    assert f["kind"] == "snip" and f["offset"] is not None, f
    (cut,) = doc.canvas._cutouts
    assert cut["rect"] is not None and not cut["locked"]


def test_a_recorded_snip_reopens_where_it_was_dragged(app, tmp_path):
    """A record that carries an offset IS a snip, whatever the classifier would call the file
    today -- an old record never changes meaning (final review of T14: a frame-shaped snip
    reopened as a full frame, its dragged spot dropped, and the next Generate saved that)."""
    pytest.importorskip("PIL")
    import json
    from PIL import Image
    photo = _photo(tmp_path)                           # 800x600
    lamp = tmp_path / "lamp.png"
    Image.new("RGBA", (384, 448), (10, 20, 30, 128)).save(lamp)   # today's classifier: the frame
    side = tmp_path / "proj" / "photo.trace.json"
    side.parent.mkdir()
    side.write_text(json.dumps({
        "image": str(photo), "upright": True, "pitch": 26, "name": "OLD", "id": "30790",
        "floor": [[130, 200], [254, 200], [364, 440], [20, 440]],
        "fg": [{"contact": [230, 320], "image": str(lamp), "offset": [100.0, 150.0]}]}),
        encoding="utf-8")
    doc, _run = _doc(app)
    doc.load_trace(side)
    f = doc._fg[0]
    assert f["kind"] == "snip" and tuple(f["offset"]) == (100.0, 150.0), f
    (cut,) = doc.canvas._cutouts
    assert cut["rect"] is not None and abs(cut["rect"][0] - 100.0) < 0.1


def test_the_cut_out_wording_says_what_to_make(app):
    """The picker and tooltips said 'full canvas' -- a frame the tab then misread. They now say
    the two things that register (a copy of the photo, or of the 384x448 frame) and the snip."""
    from ff9mapkit.workspace import tracedoc as TD
    doc, _ = _doc(app)
    for tip in (doc.tools.button("cutout").toolTip(), doc.fg_attach_btn.toolTip(),
                TD._CUTOUT_PICKER_TITLE):
        assert "full canvas" not in tip.replace("-", " ")
        assert "copy of the photo" in tip and "crop" in tip


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
    assert "z " in _fg_tip(doc, 0)
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
    assert "--event-zone=Watch the ledge@200,340;300,340;300,380;200,380" in argv
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


def test_an_event_message_that_starts_with_a_dash_reaches_the_cli_intact(app, tmp_path,
                                                                         monkeypatch):
    """Finding T17: '--event-zone' '-Stop!@...' as two argv items made argparse read the message
    as an option ('expected one argument') and the Generate failed. The values the author types
    ride in the '--flag=value' form, which argparse never mistakes for an option."""
    pytest.importorskip("PIL")
    from ff9mapkit import cli
    from ff9mapkit import imagefield as IF
    doc, run = _traced_doc(app, tmp_path)
    doc.tools.set_current("regions")
    doc.rkind_btns["event"].setChecked(True)
    doc.ev_msg.setText("-Stop!")
    cam = doc.canvas.camera()
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(200.0, 340.0), (300.0, 340.0), (300.0, 380.0), (200.0, 380.0)]])
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    argv = run.calls[0][0]
    args = cli.build_parser().parse_args(argv[3:])     # past `python -m ff9mapkit`
    assert args.event_zone[0].startswith("-Stop!@")
    assert args.name == doc.name_box.text()


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


def _regionless_project_with_place_rows(tmp_path):
    """A project traced with NO regions, then given a door and a zone by the Place tab's OWN
    ops and saved through the Editor's model -- whatever names Place mints today, verbatim."""
    from PIL import Image
    from ff9mapkit import imagefield as IF
    from ff9mapkit.editor.model import FieldDoc
    from ff9mapkit.workspace import placedoc
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    man = IF.build_image_field(photo, floor, tmp_path / "proj", name="HALL5", field_id=30787)
    fd = FieldDoc.load(man["toml"])
    placedoc.place_gateway(fd.data, [(-500, 900), (-400, 900), (-400, 1000), (-500, 1000)], 301)
    placedoc.place_event(fd.data, [(100, 900), (200, 900), (200, 1000), (100, 1000)])
    fd.save()
    return photo, floor, Path(man["toml"]), [g["name"] for g in fd.data["gateway"]], \
        [e["name"] for e in fd.data["event"]]


def test_the_place_tabs_own_rows_survive_the_sessions_first_region(app, tmp_path):
    """Review finding T1, through the REAL ops on both sides: the Place tab mints the names, the
    Editor's model saves them, and the Trace lane's first region regenerates over them. The
    rows used to be deleted, with one 'removed' line in the Output panel as the only notice."""
    pytest.importorskip("PIL")
    import tomllib
    from ff9mapkit import imagefield as IF
    photo, floor, toml, doors, zones = _regionless_project_with_place_rows(tmp_path)
    man = IF.build_image_field(photo, floor, toml.parent, name="HALL5", field_id=30787,
                               events=["It creaks.@200,340;300,340;300,380;200,380"])
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert man["removed"] == []
    assert [g["name"] for g in data["gateway"]] == doors and data["gateway"][0]["to"] == 301
    assert [e["name"] for e in data["event"]] == ["traced_zone0"] + zones


def test_load_project_leaves_place_rows_file_side_on_a_regionless_project(app, tmp_path):
    """The absorb half of T1: reopening a sidecar-less project must not pull a Place door into
    the session -- an absorbed row is re-emitted as traced_door0 stripped to to/entrance/zone,
    and the original is then the generator's to delete."""
    pytest.importorskip("PIL")
    _photo_, _floor, toml, _doors, _zones = _regionless_project_with_place_rows(tmp_path)
    doc, _run = _doc(app)
    doc.load_project(toml)
    assert doc._regions == []


def test_load_project_refuses_a_traced_row_the_session_cannot_carry(app, tmp_path):
    """A hand-edited traced row with five DISTINCT corners is a legal zone the session cannot
    hold (its quads are four clicks). Absorbed, it made every Generate fail; skipped, the next
    Generate DELETED it and renumbered every traced row after it. So the session does not arm
    at all, and says the way out -- before any state lands."""
    pytest.importorskip("PIL")
    import tomllib
    from PIL import Image
    from ff9mapkit import imagefield as IF
    from ff9mapkit.editor import model as _model
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    man = IF.build_image_field(photo, floor, tmp_path / "proj", name="HALL6", field_id=30791,
                               gateways=["4005@60,300;140,300;140,330;60,330",
                                         "4006@250,300;330,300;330,330;250,330"])
    toml = Path(man["toml"])
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    z = data["gateway"][0]["zone"]
    data["gateway"][0]["zone"] = z + [[z[0][0] - 40, z[0][1] + 60]]      # a fifth, distinct corner
    toml.write_text(_model.dumps(data), encoding="utf-8", newline="\n")
    before = toml.read_bytes()
    doc, run = _doc(app)
    with pytest.raises(ValueError, match="not four corners"):
        doc.load_project(toml)
    assert doc._image is None and doc._project is None  # refused BEFORE any state landed
    doc.on_generate()                                  # ...so there is nothing to generate over it
    assert run.calls == [] and toml.read_bytes() == before


def test_first_generate_hands_the_project_to_the_shell_once(app, tmp_path, monkeypatch):
    """The Floorplan compose→open_campaign contract on the trace lane: a clean FIRST Generate
    opens the project in the Editor (which is what feeds Place, 7d); a REGENERATE never yanks
    the author off the canvas; a failed job opens nothing."""
    pytest.importorskip("PIL")
    opened = []
    run = _Run()
    doc = TraceDoc(pick_palette("dark"), KIT, run=run, on_generated=opened.append)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.id_box.setText("30785")
    doc.name_box.setText("PICTURE")          # (a new photo names itself; T13)
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    toml = tmp_path / "photo-field" / "PICTURE.field.toml"   # the session's name (the box default)
    run.calls[0][1]["on_finished"](1)                  # a FAILED first job opens nothing
    assert opened == []
    # Finding E16: this used to call the SAME launch's callback a second time, a path no user
    # takes -- the real retry is a second Generate, which must still count as the first one
    doc.on_generate()
    toml.parent.mkdir(parents=True, exist_ok=True)
    toml.write_text('[field]\nid = 30785\nname = "PICTURE"\narea = 11\n', encoding="utf-8")
    run.calls[1][1]["on_finished"](0)
    assert opened == [str(toml)]
    doc.on_generate()                                  # in place now
    run.calls[2][1]["on_finished"](0)                  # a clean REGENERATE stays put
    assert opened == [str(toml)]


@pytest.mark.parametrize("code", [0, 1, 2, 62097])     # done, failed, refused, killed by Stop
def test_the_status_never_stays_on_generating(app, tmp_path, monkeypatch, code):
    """Finding E14: the tab's status kept saying 'Generating ...' after the job had ended, until
    the next gesture. Every ending -- a first Generate or a regenerate, clean, failed or stopped
    (the tab sees a Stop as the kill's exit code) -- settles it."""
    pytest.importorskip("PIL")
    doc, run, toml = _armed(app, tmp_path, monkeypatch)
    doc.canvas._commit_floor([(120, 210), (254, 200), (364, 440), (20, 440)])
    doc.on_generate()
    assert "Generating" in doc.status.text()
    run.calls[-1][1]["on_finished"](code)
    assert "Generating" not in doc.status.text() and doc.status.text()
    fresh, run2 = _doc(app)                            # and a FIRST Generate that writes nothing
    fresh.load_image(_photo(tmp_path))
    fresh.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    fresh.id_box.setText("30786")
    monkeypatch.setattr(fresh, "_ask_out", lambda: str(tmp_path / "other"))
    fresh.on_generate()
    run2.calls[0][1]["on_finished"](code)
    assert "Generating" not in fresh.status.text() and fresh.status.text()


def test_a_failed_first_generate_leaves_the_tab_unarmed_and_the_retry_opens(app, tmp_path,
                                                                           monkeypatch):
    """Finding T8: Generate armed the project when the job STARTED. A first job that failed and
    wrote nothing left the button reading 'Regenerate PICTURE -- in place' for a project that does
    not exist, the status saying 'Generating...' forever, and the retry -- no longer 'first' --
    never opened the project in the Editor. A REAL second launch, not a second finish of one."""
    pytest.importorskip("PIL")
    opened = []
    run = _Run()
    doc = TraceDoc(pick_palette("dark"), KIT, run=run, on_generated=opened.append)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.id_box.setText("30785")
    doc.name_box.setText("PICTURE")          # (a new photo names itself; T13)
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert "Generating" in doc.status.text()
    run.calls[0][1]["on_finished"](2)                  # the CLI refused: no field.toml written
    toml = tmp_path / "photo-field" / "PICTURE.field.toml"
    assert not toml.exists()
    assert doc.gen_btn.text() == "Generate field project…"   # not armed over nothing
    assert "Generating" not in doc.status.text() and "failed" in doc.status.text()
    assert doc.status.property("state") == "error"
    doc.on_generate()                                  # the author fixes it and tries again
    argv = run.calls[1][0]
    assert Path(argv[argv.index("--out") + 1]) == toml.parent   # back where it started (E9's rule)
    toml.write_text('[field]\nid = 30785\nname = "PICTURE"\narea = 11\n', encoding="utf-8")
    run.calls[1][1]["on_finished"](0)
    assert opened == [str(toml)]                       # the retry IS the first Generate
    assert "Generated PICTURE" in doc.status.text() and "Generating" not in doc.status.text()
    assert doc.gen_btn.text().startswith("Regenerate PICTURE")


def test_the_status_settles_after_a_regenerate_and_a_failed_one_is_not_stamped(app, tmp_path,
                                                                               monkeypatch):
    """Every finish says how it ended. A regenerate that failed and left the project as it was
    must not claim the project matches the session: the 'not stamped' warning comes back."""
    pytest.importorskip("PIL")
    doc, run, toml = _armed(app, tmp_path, monkeypatch)
    doc.canvas._commit_floor([(120, 210), (254, 200), (364, 440), (20, 440)])
    doc.on_generate()
    toml.write_text('[field]\nid = 30789\nname = "PICTURE"\narea = 12\n', encoding="utf-8")
    run.calls[1][1]["on_finished"](0)
    assert "Regenerated PICTURE" in doc.status.text() and "not stamped" not in doc.status.text()
    doc.canvas._commit_floor([(110, 220), (254, 200), (364, 440), (20, 440)])
    doc.on_generate()
    run.calls[2][1]["on_finished"](2)                  # refused: the file did not move
    assert "failed" in doc.status.text() and "Generating" not in doc.status.text()
    assert "not stamped" in doc.status.text()
    # the job writes walkmesh.obj + art BEFORE the toml, so an unmoved toml proves nothing about
    # them: the status must not give the all-clear (review of T8)
    assert "was not changed" not in doc.status.text()
    assert "field.toml was not updated" in doc.status.text() and "may have been" in doc.status.text()
    doc.on_generate()                                  # a failure that DID write the file is
    toml.write_text('[field]\nid = 30789\nname = "PICTURE"\narea = 13\n', encoding="utf-8")
    run.calls[3][1]["on_finished"](1)                  # judged by the disk: it is stamped
    assert "not stamped" not in doc.status.text() and "Output panel" in doc.status.text()


def _hall(app, tmp_path):
    """A generated HALL with three traced doors, a Place-added key on the MIDDLE one and an
    author-placed start point at the far end; reopened in the tab, the FIRST door deleted and the
    far half traced away -- launched, with what the job would write already on disk."""
    pytest.importorskip("PIL")
    import re
    from PIL import Image
    from ff9mapkit import imagefield as IF
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    floor = [(130.0, 140.0), (254.0, 140.0), (364.0, 440.0), (20.0, 440.0)]
    doors = ["4005@60,300;100,300;100,330;60,330", "4006@160,300;200,300;200,330;160,330",
             "4007@260,300;300,300;300,330;260,330"]
    man = IF.build_image_field(photo, floor, tmp_path / "proj", name="HALL", field_id=30790,
                               gateways=doors)
    toml = Path(man["toml"])
    w = man["world_floor"]
    far = (int(0.9 * w[0][0] + 0.1 * w[2][0]), int(0.9 * w[0][1] + 0.1 * w[2][1]))
    text = re.sub(r"spawn = \[-?\d+, -?\d+\]", f"spawn = [{far[0]}, {far[1]}]",
                  toml.read_text(encoding="utf-8"), count=1)
    text = text.replace('name = "traced_door1"',
                        'name = "traced_door1"\nflag_gate = 8800\nrequires_flag = 8801', 1)
    toml.write_text(text, encoding="utf-8", newline="\n")
    doc, run = _doc(app)
    doc.load_project(toml)
    doc._on_region_deleted(0)                           # the FIRST door, deleted in Trace
    shorter = [(130.0, 300.0), (254.0, 300.0), (364.0, 440.0), (20.0, 440.0)]
    doc.canvas._commit_floor(shorter)                   # and the far half traced away
    doc.on_generate()
    assert len(run.calls) == 1
    IF.build_image_field(photo, shorter, tmp_path / "proj", name="HALL", field_id=30790,
                         gateways=doors[1:])            # what the job does on disk
    return doc, run, photo, shorter, doors


def test_a_regenerate_says_on_the_status_what_it_moved_or_removed(app, tmp_path):
    """Finding E13: what a regenerate takes back was named only in the Output console. The tab's
    own status now leads with it: a key dropped from a regenerated row and a start point the
    author placed that the new floor no longer covers. Review of E13: traced rows renumber by
    position, so deleting the FIRST of three named the wrong door as removed -- a traced row's
    going is not reported (the author deleted it here), and its key is judged against the row
    with the same zone, under that row's new name."""
    from ff9mapkit import imagefield as IF
    doc, run, photo, shorter, doors = _hall(app, tmp_path)
    run.calls[0][1]["on_finished"](0)
    said = doc.status.text()
    assert said.startswith("⚠") and "Regenerated HALL" in said
    assert "removed" not in said                        # not traced_door2, which still exists
    assert "traced_door0 lost “flag gate”" in said      # the middle door, renumbered to 0
    assert "flag_gate" not in said, "a raw key in the status"
    # a key the Editor form shows is named by the form's own label (without its format hint)
    assert "traced_door0 lost “Opens when flag set”" in said
    assert "requires_flag" not in said and "requires flag" not in said
    assert "spawn point moved" in said and "off the new floor" in said   # Place's own word
    assert doc.status.property("state") == "warn"
    # a second regenerate: the generator's own spawn follows the floor and names nothing
    doc.canvas._commit_floor([(132.0, 302.0)] + shorter[1:])
    doc.on_generate()
    IF.build_image_field(photo, [(132.0, 302.0)] + shorter[1:], tmp_path / "proj", name="HALL",
                         field_id=30790, gateways=doors[1:])
    run.calls[1][1]["on_finished"](0)
    assert doc.status.text().startswith("Regenerated HALL") and "⚠" not in doc.status.text()


def test_a_dropped_key_is_named_without_the_forms_format_hint():
    """'traced_event0 lost “Give item (id, count)”' quoted a hint for typing the value; the name
    of the thing is 'Give item'."""
    import tomllib
    from ff9mapkit.workspace.tracedoc import TraceDoc as TD
    old = {"event": [{"name": "traced_zone0", "zone": [[0, 0], [1, 0], [1, 1], [0, 1]],
                      "message": "hi", "give_item": [232, 1], "set_flag": ["boss_dead", 1]}]}
    new = "[[event]]\nname = \"traced_zone0\"\nmessage = \"hi\"\nzone = [[0, 0], [1, 0], [1, 1], [0, 1]]\n"
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        toml = Path(td) / "X.field.toml"
        toml.write_text(new, encoding="utf-8")
        assert tomllib.loads(new)["event"][0]["zone"] == old["event"][0]["zone"]
        said = TD._what_it_took(old, toml)
    assert "lost “Give item”" in said and "lost “Set flag”" in said, said
    assert "(" not in said, said


def test_a_written_file_whose_job_reported_an_error_still_says_what_it_took(app, tmp_path):
    """The job can rewrite the project and still exit non-zero (E10). That status leads with what
    the regenerate took too (the review's surviving mutation: its prefix could go unnoticed)."""
    doc, run, *_ = _hall(app, tmp_path)
    run.calls[0][1]["on_finished"](1)
    said = doc.status.text()
    assert said.startswith("⚠") and "traced_door0 lost “flag gate”" in said
    assert "but the job reported an error" in said and doc.status.property("state") == "warn"


def test_a_finish_after_the_author_moved_on_leaves_the_new_session_alone(app, tmp_path,
                                                                         monkeypatch):
    """The settle is the LAUNCH's: an author who opened another project while a first Generate
    ran must not have that project disarmed (or its status overwritten) by the old job failing."""
    pytest.importorskip("PIL")
    from PIL import Image
    from ff9mapkit import imagefield as IF
    run = _Run()
    doc = TraceDoc(pick_palette("dark"), KIT, run=run)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.id_box.setText("30785")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    man = IF.build_image_field(photo, [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)],
                               tmp_path / "proj", name="HALL9", field_id=30793)
    doc.load_project(Path(man["toml"]))                # another project, mid-job
    armed, said = doc._project, doc.status.text()
    run.calls[0][1]["on_finished"](2)                  # the OLD first job fails, writing nothing
    assert doc._project is armed and doc.gen_btn.text().startswith("Regenerate HALL9")
    assert doc.status.text() == said


def _armed(app, tmp_path, monkeypatch, **hooks):
    """A session whose FIRST Generate finished cleanly: the next Generate is an in-place
    regenerate. Returns (doc, run, the project's field.toml)."""
    run = _Run()
    doc = TraceDoc(pick_palette("dark"), KIT, run=run, **hooks)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.id_box.setText("30789")
    doc.name_box.setText("PICTURE")          # (a new photo names itself; T13)
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    toml = tmp_path / "photo-field" / "PICTURE.field.toml"
    toml.parent.mkdir(parents=True, exist_ok=True)
    toml.write_text('[field]\nid = 30789\nname = "PICTURE"\narea = 11\n', encoding="utf-8")
    run.calls[0][1]["on_finished"](0)
    return doc, run, toml


def test_a_clean_regenerate_tells_the_shell_which_file_it_rewrote(app, tmp_path, monkeypatch):
    """The other half of the hand-off (review finding T38): the FIRST Generate opens the project;
    every later one rewrites the same file in place and must SAY so, or the shell's open buffer
    goes stale and the next Save All writes it back over the regenerated file."""
    pytest.importorskip("PIL")
    opened, rewrote = [], []
    doc, run, toml = _armed(app, tmp_path, monkeypatch, on_generated=opened.append,
                            on_regenerated=rewrote.append)
    assert opened == [str(toml)] and rewrote == []     # a first Generate is not a "regenerate"
    doc.on_generate()
    finish = run.calls[1][1]["on_finished"]
    finish(0)
    assert rewrote == [str(toml)] and opened == [str(toml)]   # told; and never re-opened
    finish(1)                                          # told on a FAILED finish too: the job writes
    assert rewrote == [str(toml)] * 2                  # before it reports, so only the disk knows
    assert opened == [str(toml)]                       # (a failure still never opens anything)


def test_generate_asks_first_and_a_refusal_starts_nothing(app, tmp_path, monkeypatch):
    """``can_generate`` is asked before EVERY Generate with the file it would write; a refusal
    launches no job, rewrites no session record, and puts the reason on the status line."""
    pytest.importorskip("PIL")
    asked, verdict = [], {"why": None}

    def can(toml):
        asked.append(toml)
        return verdict["why"]

    doc, run, toml = _armed(app, tmp_path, monkeypatch, can_generate=can)
    assert asked == [str(toml)]                        # the FIRST Generate asked too
    side = toml.parent / "photo.trace.json"
    before = side.read_bytes()
    doc.canvas._commit_floor([(120, 210), (254, 200), (364, 440), (20, 440)])   # a new session state
    verdict["why"] = "PICTURE has unsaved edits — Save All first."
    doc.on_generate()
    assert len(run.calls) == 1 and asked[-1] == str(toml)
    assert side.read_bytes() == before                 # the record still matches the project
    assert doc.status.text().startswith("PICTURE has unsaved edits")
    verdict["why"] = None
    doc.on_generate()
    assert len(run.calls) == 2 and side.read_bytes() != before


def test_renaming_an_armed_project_is_refused_not_written_beside_it(app, tmp_path, monkeypatch):
    """The folder holds ONE floor and ONE set of art. A regenerate under a new Name wrote a
    second field.toml beside the first and replaced the walkmesh and art under it: the first
    field kept its old [camera] over a floor that no longer matched, and nothing was told."""
    pytest.importorskip("PIL")
    doc, run, toml = _armed(app, tmp_path, monkeypatch)
    doc.name_box.setText("ATTIC")
    doc.on_generate()
    assert len(run.calls) == 1                         # nothing launched under the new name
    assert "PICTURE.field.toml" in doc.status.text() and "one field per folder" in doc.status.text()
    doc.name_box.setText("PICTURE")
    doc.on_generate()
    assert len(run.calls) == 2 and "--name=PICTURE" in run.calls[1][0]


def test_a_field_renamed_in_the_editor_cannot_regenerate_into_a_second_file(app, tmp_path):
    """The project file is HALL7.field.toml but its [field] name is now GREAT (renamed in the
    Editor). The session arms from the NAME, so Generate aimed at GREAT.field.toml -- a second
    file over the same floor and art, past the unsaved-edits guard (which was asked about a file
    that did not exist). One field per folder, whatever the Name box says."""
    pytest.importorskip("PIL")
    from PIL import Image
    from ff9mapkit import imagefield as IF
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    man = IF.build_image_field(photo, floor, tmp_path / "proj", name="HALL7", field_id=30792)
    toml = Path(man["toml"])
    toml.write_text(toml.read_text(encoding="utf-8").replace('name = "HALL7"', 'name = "GREAT"'),
                    encoding="utf-8")
    doc, run = _doc(app)
    doc.load_project(toml)
    assert doc.name_box.text() == "GREAT"
    doc.on_generate()
    assert run.calls == [] and "HALL7.field.toml" in doc.status.text()
    doc.name_box.setText("HALL7")
    doc.on_generate()
    assert len(run.calls) == 1


# ---------------------------------------------------------------------------- the first Generate's folder
# The folder used to be <parent>/<photo stem>-field, unconditionally. The walkmesh, the base art
# and the session record are each ONE file in it, so a second photo with the same file name
# (image.png, photo.jpg, IMG_0001.jpg) silently replaced the first project's art and sidecar
# (review finding E9). One project per folder; the fences below pin who may reuse one.

def _first_generate(app, photo, parent, monkeypatch, name=None):
    """A fresh session's FIRST Generate into ``parent``; returns (doc, the --out it chose)."""
    doc, run = _doc(app)
    doc.load_image(photo)
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.id_box.setText("30788")
    if name:
        doc.name_box.setText(name)
    monkeypatch.setattr(doc, "_ask_out", lambda: str(parent))
    doc.on_generate()
    argv, _kw = run.calls[-1]
    return doc, Path(argv[argv.index("--out") + 1])


def _as_generated(out, name):
    """What the job writes beside the sidecar the tab already wrote at launch."""
    (out / "art").mkdir(parents=True, exist_ok=True)
    (out / "art" / "base.png").write_bytes(b"first project's art")
    (out / "walkmesh.obj").write_text("v 0 0 0\n", encoding="utf-8")
    (out / f"{name}.field.toml").write_text(
        f'[field]\nid = 30788\nname = "{name}"\narea = 11\n', encoding="utf-8")


def _two_photos_named_alike(tmp_path):
    for d in ("day1", "day2", "projects"):
        (tmp_path / d).mkdir()
    return (_photo(tmp_path / "day1"), _photo(tmp_path / "day2", size=(640, 480)),
            tmp_path / "projects")


def test_a_second_photo_with_the_same_file_name_gets_its_own_folder(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    import json
    photo_a, photo_b, parent = _two_photos_named_alike(tmp_path)
    _doc_a, out_a = _first_generate(app, photo_a, parent, monkeypatch, name="CELLAR")
    assert out_a == parent / "photo-field"
    _as_generated(out_a, "CELLAR")
    side_a = out_a / "photo.trace.json"
    before = side_a.read_bytes()
    doc_b, out_b = _first_generate(app, photo_b, parent, monkeypatch, name="ATTIC")
    assert out_b == parent / "photo-field-2"           # NOT the first project's folder
    assert side_a.read_bytes() == before               # its session record is untouched
    assert json.loads(side_a.read_text(encoding="utf-8"))["name"] == "CELLAR"
    assert json.loads((out_b / "photo.trace.json").read_text(encoding="utf-8"))["name"] == "ATTIC"
    assert doc_b.status.text().startswith("photo-field is already in use")
    _as_generated(out_b, "ATTIC")
    _doc_c, out_c = _first_generate(app, photo_b.parent.parent / "day1" / "photo.png", parent,
                                    monkeypatch, name="LOFT")
    assert out_c == parent / "photo-field-3"           # ...and the next one counts on


def test_a_same_named_photo_does_not_merge_into_the_default_named_project(app, tmp_path,
                                                                          monkeypatch):
    """The likeliest collision of all: BOTH sessions keep the default name. The second photo
    would MERGE into the first project's PICTURE.field.toml, keeping its hand content while
    swapping the art and the floor under it."""
    pytest.importorskip("PIL")
    photo_a, photo_b, parent = _two_photos_named_alike(tmp_path)
    _doc_a, out_a = _first_generate(app, photo_a, parent, monkeypatch)
    _as_generated(out_a, "PICTURE")
    _doc_b, out_b = _first_generate(app, photo_b, parent, monkeypatch)
    assert out_b == parent / "photo-field-2"


def test_a_fresh_session_never_writes_into_this_photos_own_existing_project(app, tmp_path,
                                                                             monkeypatch):
    """Not even the SAME photo under the SAME name. A fresh session knows nothing of that
    project's doors, zones and cut-outs: regenerating over it would strip every traced_ row,
    replace the floor and overwrite the session record -- and the file may be open in the
    Editor, where this path would also slip past the regenerate's reload. To update a project
    you open the project; a photo opened fresh starts a new one."""
    pytest.importorskip("PIL")
    (tmp_path / "projects").mkdir()
    photo = _photo(tmp_path)
    _doc_a, out_a = _first_generate(app, photo, tmp_path / "projects", monkeypatch, name="CELLAR")
    _as_generated(out_a, "CELLAR")
    before = {q.name: q.read_bytes() for q in out_a.rglob("*") if q.is_file()}
    doc_b, out_b = _first_generate(app, photo, tmp_path / "projects", monkeypatch, name="CELLAR")
    assert out_b == tmp_path / "projects" / "photo-field-2"
    assert {q.name: q.read_bytes() for q in out_a.rglob("*") if q.is_file()} == before
    assert doc_b.status.text().startswith("photo-field is already in use")


@pytest.mark.parametrize("record", [
    '{"image": "%s", "name": "ATTIC"}',                # this photo's failed attempt, ANOTHER name
    '{"image": 7, "name": "PICTURE"}',                 # not a path at all
    '["not", "an", "object"]',
    '{ this is not json',
], ids=["other-name", "image-not-a-path", "not-an-object", "not-json"])
def test_a_folder_holding_someone_elses_record_is_not_ours(app, tmp_path, monkeypatch, record):
    """A sidecar-only folder is reused ONLY for this very session's retry; any other record --
    another name's, a malformed one -- is not ours to overwrite, and never raises."""
    pytest.importorskip("PIL")
    photo = _photo(tmp_path)
    parent = tmp_path / "projects"
    (parent / "photo-field").mkdir(parents=True)
    side = parent / "photo-field" / "photo.trace.json"
    if "%s" in record:                                 # a VALID record of this very photo: only
        import json                                    # the name differs (or the case is vacuous)
        record = json.dumps({"image": str(photo), "name": "ATTIC"})
        assert json.loads(record)["image"] == str(photo)
    side.write_text(record, encoding="utf-8")
    before = side.read_bytes()
    _doc_a, out = _first_generate(app, photo, parent, monkeypatch)
    assert out == parent / "photo-field-2" and side.read_bytes() == before


def test_a_file_squatting_on_the_folder_name_is_stepped_over(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    photo = _photo(tmp_path)
    parent = tmp_path / "projects"
    parent.mkdir()
    (parent / "photo-field").write_text("a file, not a folder", encoding="utf-8")
    _doc_a, out = _first_generate(app, photo, parent, monkeypatch)
    assert out == parent / "photo-field-2"


def test_the_same_photo_under_a_new_name_does_not_share_a_folder(app, tmp_path, monkeypatch):
    """One walkmesh.obj and one base.png per folder: a second FIELD traced from the same photo
    into the same folder would replace the floor under the first field's toml."""
    pytest.importorskip("PIL")
    (tmp_path / "projects").mkdir()
    photo = _photo(tmp_path)
    _doc_a, out_a = _first_generate(app, photo, tmp_path / "projects", monkeypatch, name="CELLAR")
    _as_generated(out_a, "CELLAR")
    _doc_b, out_b = _first_generate(app, photo, tmp_path / "projects", monkeypatch, name="ATTIC")
    assert out_b == tmp_path / "projects" / "photo-field-2"


def test_a_folder_that_is_not_this_photos_project_is_never_written_into(app, tmp_path,
                                                                        monkeypatch):
    pytest.importorskip("PIL")
    photo = _photo(tmp_path)
    parent = tmp_path / "projects"
    (parent / "photo-field").mkdir(parents=True)
    (parent / "photo-field" / "notes.txt").write_text("mine", encoding="utf-8")
    _doc_a, out = _first_generate(app, photo, parent, monkeypatch)
    assert out == parent / "photo-field-2"
    assert sorted(p.name for p in (parent / "photo-field").iterdir()) == ["notes.txt"]


def test_an_empty_folder_and_a_failed_first_attempt_are_reused(app, tmp_path, monkeypatch):
    """No litter: an empty folder is free, and a first Generate that FAILED left only this
    photo's sidecar behind -- the retry goes back into the same folder, not into -2."""
    pytest.importorskip("PIL")
    photo = _photo(tmp_path)
    parent = tmp_path / "projects"
    (parent / "photo-field").mkdir(parents=True)
    _doc_a, out_a = _first_generate(app, photo, parent, monkeypatch)
    assert out_a == parent / "photo-field"             # empty -> free
    assert (out_a / "photo.trace.json").is_file()      # the launch wrote the session record
    _doc_b, out_b = _first_generate(app, photo, parent, monkeypatch)
    assert out_b == out_a                              # only OUR sidecar in it -> ours to retry


def test_after_generate_opens_the_toml_captured_at_launch(app, tmp_path, monkeypatch):
    """The on_finished payload is resolved AT LAUNCH: an author who switches projects while
    the job runs must not have the NEW project's path opened by the OLD job's finish."""
    pytest.importorskip("PIL")
    opened = []
    run = _Run()
    doc = TraceDoc(pick_palette("dark"), KIT, run=run, on_generated=opened.append)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.id_box.setText("30786")
    doc.name_box.setText("PICTURE")          # (a new photo names itself; T13)
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    _argv, kw = run.calls[0]
    launched = tmp_path / "photo-field" / "PICTURE.field.toml"
    launched.parent.mkdir(parents=True, exist_ok=True)
    launched.write_text('[field]\nid = 30786\nname = "PICTURE"\narea = 11\n', encoding="utf-8")
    (tmp_path / "elsewhere").mkdir()
    doc.load_image(_photo(tmp_path / "elsewhere", size=(640, 480)))   # a NEW session mid-job
    kw["on_finished"](0)
    assert opened == [str(launched)]                   # the launched project, never the new one


def test_an_unrepresentable_pitch_is_said_not_swallowed(app, tmp_path):
    """The slider is integer and banded 6-48; a sidecar pitch it cannot represent used to
    clamp silently -- and a Regenerate would then MOVE the floor. The load now warns."""
    pytest.importorskip("PIL")
    import json
    photo = _photo(tmp_path)
    side = tmp_path / "photo.trace.json"
    side.write_text(json.dumps({"image": str(photo), "pitch": 52,
                                "floor": [[100, 300], [200, 300], [150, 400]]}),
                    encoding="utf-8")
    doc, _run = _doc(app)
    doc.load_trace(side)
    assert doc.pitch.value() == 48                     # the slider's own cap
    assert "pitch 52" in doc.status.text() and "MOVES the floor" in doc.status.text()
    assert doc.status.text().startswith("⚠ pitch 52")  # it LEADS (T23): never the clipped tail


# ------------------------------------------------------------------ T23: the page's rows and status
# Widths here are RELATIVE (offscreen fonts are fiction): a fence compares the tab against itself.

def test_a_long_status_wraps_and_never_widens_the_tab(app, tmp_path):
    """Finding T23: the status line did not wrap, so its full text width WAS the page minimum --
    one long status floored the window past 1280 px at 150% and clipped its own tail."""
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    base = doc.minimumSizeHint().width()
    doc._refresh("a status that runs on and on " * 30, "warn")
    assert doc.minimumSizeHint().width() == base


def test_the_warning_the_author_must_act_on_comes_first(app, tmp_path, monkeypatch):
    """The 'not stamped' and 'door without a target' clauses used to be APPENDED after the counts,
    so they were the part cut off the right edge."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _run = _traced(app, tmp_path)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    doc.tools.set_current("regions")
    cam = doc.canvas.camera()
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(60.0, 300.0), (140.0, 300.0), (140.0, 330.0), (60.0, 330.0)]])
    doc._refresh()
    text = doc.status.text()
    assert text.startswith("⚠ not stamped"), text
    # the tally moved to the Inspector (T41): what is left after the stamp is the warning
    assert text.split(" · ")[1].startswith("⚠ 1 door without a target"), text


def test_a_tool_switch_that_spills_the_row_keeps_the_frame_in_view_and_the_authors_zoom(app, tmp_path):
    """Review of T23: switching to Regions spilled Undo/Clear onto a second line; the canvas lost
    that height but kept its old fit, so the drawn zones at the bottom of the art fell out of view.
    The CANVAS owns that re-fit (it follows its own resize while the view is still at the fit).
    The tab once forced a second one of its own on every flip of the row, which threw away a zoom
    the author had chosen (final review of batch 3) -- so this pins the OUTCOME both ways: at the
    fit the whole frame stays in view; a zoomed view stays where the author put it. The width is
    chosen BETWEEN the row's one-line asks in the two states, read at runtime."""
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.tools.set_current("regions")
    doc.rkind_btns["gateway"].setChecked(True)
    QApplication.processEvents()
    wide = doc.tool_row._one_line_width()
    doc.tools.set_current("floor")
    QApplication.processEvents()
    narrow = doc.tool_row._one_line_width()
    assert narrow < wide                               # the premise: Regions asks for more
    pad = doc.width() - doc.tool_row.width()
    doc.resize(pad + (narrow + wide) // 2, 900)
    doc.show()
    c = doc.canvas

    def settle():
        for _ in range(4):
            QApplication.processEvents()
        c.viewport().repaint()                         # a pending first fit runs in a real paint
        QApplication.processEvents()

    def frame_in_view():
        r = c.mapFromScene(c._scene.sceneRect()).boundingRect()
        return c.viewport().rect().adjusted(-1, -1, 1, 1).contains(r)

    settle()
    assert not doc.tool_row.spilled() and c._zoom == c._fit_zoom and frame_in_view()
    doc.tools.set_current("regions")
    settle()
    assert doc.tool_row.spilled() and c._zoom == c._fit_zoom and frame_in_view()
    doc.tools.set_current("floor")
    settle()
    assert not doc.tool_row.spilled() and c._zoom == c._fit_zoom and frame_in_view()
    c.scale(1.5, 1.5)                                  # the author zooms in on a far corner...
    c._zoom *= 1.5
    zoomed = c._zoom
    doc.tools.set_current("regions")                   # ...and picks another tool
    settle()
    assert doc.tool_row.spilled() and c._zoom == zoomed, "a tool switch threw the zoom away"
    doc.tools.set_current("floor")
    settle()
    assert not doc.tool_row.spilled() and c._zoom == zoomed
    doc.hide()


def test_the_cut_out_strip_shares_the_tools_row_when_it_fits(app, tmp_path, monkeypatch):
    """The strip was a row of its own, so marking the first contact took a whole row of height
    from the canvas. When the width allows, it now sits on the tools row."""
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.resize(2400, 900)
    doc.show()
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    QApplication.processEvents()
    before = doc.canvas.height()
    monkeypatch.setattr(doc, "_ask_cutout", lambda: None)
    doc.tools.set_current("cutout")
    doc._on_contact(230.0, 320.0)
    QApplication.processEvents()
    assert doc.fg_box.isVisible() and not doc.tool_row.spilled()
    # no new row (a combo may stand a pixel or two taller than the buttons beside it)
    assert before - doc.canvas.height() < doc.fg_box.sizeHint().height() // 2


def test_unsaved_trace_work_is_what_the_last_generate_has_not_seen(app, tmp_path, monkeypatch):
    """Finding T25: the session lives only in memory until Generate writes it. has_unsaved is
    the ONE predicate both guards (Open over it, the app closing) spend."""
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    assert not doc.has_unsaved()                       # nothing loaded
    doc.load_image(_photo(tmp_path))
    assert not doc.has_unsaved()                       # a photo alone is no work
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    assert doc.has_unsaved()
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert not doc.has_unsaved()                       # the record + project now hold it
    doc.canvas._commit_floor([(120, 210), (254, 200), (364, 440), (20, 440)])
    assert doc.has_unsaved()                           # an edit the project lacks


def test_drawn_regions_alone_are_unsaved_work(app, tmp_path):
    """Doors and event messages with the floor cleared are still work a close would discard."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _traced(app, tmp_path)
    doc.tools.set_current("regions")
    cam = doc.canvas.camera()
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(60.0, 300.0), (140.0, 300.0), (140.0, 330.0), (60.0, 330.0)]])
    doc.tools.set_current("floor")
    doc.clear_btn.click()
    assert doc._floor == [] and doc._fg == [] and len(doc._regions) == 1
    assert doc.has_unsaved()


def test_opening_another_image_over_unsaved_work_asks_first(app, tmp_path, monkeypatch):
    """Open (and the 'Load <open field>' offer) used to clear the floor, regions and Undo history
    with no question at all."""
    pytest.importorskip("PIL")
    doc, _ = _traced(app, tmp_path)
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.setattr(doc, "_ask_image", lambda: str(_photo(other)))
    asked = []
    answer = {"v": False}

    def ask():
        asked.append(1)
        return answer["v"]

    monkeypatch.setattr(doc, "_ask_discard", ask)
    floor = list(doc._floor)
    doc.on_open()
    assert asked and doc._floor == floor and doc._history   # declined: nothing touched
    toml, _f = _built_project(tmp_path)
    doc._offer_path = str(toml)
    doc.on_offer()
    assert len(asked) == 2 and doc._floor == floor          # the offer asks too
    answer["v"] = True
    doc.on_open()
    assert doc._floor == [] and doc._image.parent == other  # accepted: the new photo
    asked.clear()
    doc.on_open()                                           # nothing unsaved now: no question
    assert not asked


def test_a_region_lifted_above_the_horizon_says_how_to_get_it_back(app, tmp_path):
    """Finding T6: a pitch change that puts a zone's corner above the horizon takes the quad off
    the canvas, yet the Generate tooltip said to right-click it. It stays in the session (Generate
    stays off, nothing is dropped) and the pitch brings it back -- so that is what is said."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _traced(app, tmp_path)
    doc.tools.set_current("regions")
    doc.rkind_btns["event"].setChecked(True)
    cam = doc.canvas.camera()
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(60.0, 100.0), (140.0, 100.0), (140.0, 140.0), (60.0, 140.0)]])
    assert len(doc.canvas._regions) == 1
    doc.pitch.setValue(10)
    assert doc.canvas._regions == [] and len(doc._regions) == 1   # hidden, never dropped
    assert not doc.gen_btn.isEnabled()
    tip = doc.gen_btn.toolTip()
    assert "right-click" not in tip and "pitch" in tip and "Undo" in tip
    assert "slide the pitch back" in doc.status.text()
    doc.pitch.setValue(26)
    assert len(doc.canvas._regions) == 1                          # the pitch restores it


def test_a_bad_name_is_refused_on_the_status_line_before_anything_runs(app, tmp_path,
                                                                       monkeypatch):
    """Finding T7, the tab half: the Name box went straight to --name. The backend now refuses,
    and the tab says why without launching a job or writing a session record."""
    pytest.importorskip("PIL")
    doc, run = _traced(app, tmp_path)
    doc.id_box.setText("30777")
    doc.name_box.setText("Room?")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert run.calls == [] and not list(tmp_path.glob("*-field"))
    assert "letters, digits" in doc.status.text()
    assert doc.status.property("state") == "error"


def test_a_zone_drawn_beyond_the_int16_world_is_refused_at_the_click(app, tmp_path):
    """Finding T9, the tab half: a door in the top rows of the photo at the default pitch lies
    past |z| 32767. It is refused when drawn, not after a Generate."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _traced(app, tmp_path)
    doc.tools.set_current("regions")
    cam = doc.canvas.camera()
    far = [IF.click_to_world(cam, p) for p in [(60.0, 2.0), (140.0, 2.0), (140.0, 30.0), (60.0, 30.0)]]
    assert any(abs(z) > 32767 for _x, z in far)        # the premise: really out of bound
    hist = len(doc._history)
    doc._on_region_drawn(far)
    assert doc._regions == [] and len(doc._history) == hist   # no gesture recorded
    assert "too far" in doc.status.text() and doc.status.property("state") == "warn"
    assert "Int16" not in doc.status.text()            # the author's words, not the packer's


def _project_whose_photo_is_gone(tmp_path):
    """A built project + its session record, then the source photo deleted (moved, another PC)."""
    import json
    toml, floor = _built_project(tmp_path, with_fg=False)
    photo = tmp_path / "room.png"
    side = toml.parent / "room.trace.json"
    side.write_text(json.dumps({"image": str(photo), "pitch": 21, "floor": [list(p) for p in floor],
                                "fg": [], "regions": [], "name": "HALL3", "id": "30779"}),
                    encoding="utf-8")
    photo.unlink()
    return toml, side


@pytest.mark.parametrize("route", ["trace", "toml", "offer"])
def test_a_project_whose_photo_is_gone_reopens_from_its_own_art(app, tmp_path, route):
    """Finding T10: the session record names the photo by its absolute path; once it moved, every
    reopen failed ('Could not open X.field.toml: No such file ... photo') -- and the open-field
    offer failed silently -- although art/base.png, the exact crop, sat in the project."""
    pytest.importorskip("PIL")
    toml, side = _project_whose_photo_is_gone(tmp_path)
    doc, _ = _doc(app)
    if route == "trace":
        doc.load_trace(side)
    elif route == "toml":
        doc.load_project(toml)
    else:
        doc.offer_project(toml)
    assert doc._image == toml.parent / "art" / "base.png"
    assert doc._project and doc._project["out"] == str(toml.parent) and len(doc._floor) == 4
    assert "room.png" in doc.status.text() and "missing" in doc.status.text()
    assert doc.status.text().startswith("⚠")          # the warning LEADS the status
    assert doc.status.property("state") == "warn"


def test_a_regenerate_after_the_photo_went_missing_rewrites_the_one_record(app, tmp_path,
                                                                            monkeypatch):
    """Review of T10: the fallback session's image is art/base.png, so the next Generate wrote a
    SECOND record (base.trace.json) and left <photo>.trace.json holding the old floor. Reopening
    picks sorted()[0] -- for a photo stem sorting before 'base' that is the STALE record, armed as
    in sync, and its next Generate reverts the project. One project per folder, one record: the
    write goes to the record the folder already has."""
    pytest.importorskip("PIL")
    import json
    toml, side = _project_whose_photo_is_gone(tmp_path)
    doc, _ = _doc(app)
    doc.load_trace(side)
    moved = [(120.0, 210.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    doc.canvas._commit_floor(moved)
    doc._write_trace_sidecar(toml.parent)
    assert sorted(p.name for p in toml.parent.glob("*.trace.json")) == ["room.trace.json"]
    rec = json.loads(side.read_text(encoding="utf-8"))
    assert [tuple(p) for p in rec["floor"]] == moved
    assert rec["image"] == str(toml.parent / "art" / "base.png")

def test_a_missing_photo_with_nothing_to_rebuild_from_names_the_photo(app, tmp_path):
    pytest.importorskip("PIL")
    import json
    side = tmp_path / "x.trace.json"
    side.write_text(json.dumps({"image": str(tmp_path / "gone.png"), "floor": []}), encoding="utf-8")
    doc, _ = _doc(app)
    with pytest.raises(ValueError, match="gone.png"):
        doc.load_trace(side)
    assert doc._image is None


def test_a_broken_project_is_refused_before_any_state_lands(app, tmp_path):
    """Finding T16: load_project showed the project's art BEFORE reading walkmesh.obj, so a missing
    obj left the art on the canvas with an empty trace and no project -- and on the auto-offer
    path, with no word at all. Every refusal now comes first, and the offer says why."""
    pytest.importorskip("PIL")
    toml, _floor = _built_project(tmp_path, with_fg=False)
    (toml.parent / "walkmesh.obj").unlink()
    doc, _ = _doc(app)
    with pytest.raises(OSError):
        doc.load_project(toml)
    assert doc._image is None and doc._project is None
    doc2, _ = _doc(app)
    doc2.offer_project(toml)
    assert doc2._image is None and doc2._offer_rejected == str(toml)
    assert "HALL3" in doc2.status.text() and "walkmesh.obj" in doc2.status.text()


def test_clear_acts_on_the_active_tool_and_says_so(app, tmp_path, monkeypatch):
    """Finding T12: Clear emptied the FLOOR whatever tool was showing -- with the Regions tool
    active it wiped the floor and left every zone. It now clears what the tool owns, its tip
    says which, and it is one undoable gesture. The LABEL stays one fixed word: 'Clear regions'
    spilled the tools row in Regions mode and pushed the drawn zones off the canvas (review)."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _traced(app, tmp_path)
    assert doc.clear_btn.text() == "Clear" and "floor" in doc.clear_btn.toolTip()
    doc.tools.set_current("regions")
    cam = doc.canvas.camera()
    doc._on_region_drawn([IF.click_to_world(cam, p) for p in
                          [(60.0, 300.0), (140.0, 300.0), (140.0, 330.0), (60.0, 330.0)]])
    assert doc.clear_btn.text() == "Clear" and doc.clear_btn.isEnabled()
    assert doc.clear_btn.toolTip().startswith("Clear regions")
    floor = list(doc._floor)
    doc.clear_btn.click()
    assert doc._regions == [] and doc.canvas._regions == [] and doc._floor == floor
    doc.on_undo()
    assert len(doc._regions) == 1
    monkeypatch.setattr(doc, "_ask_cutout", lambda: None)
    doc.tools.set_current("cutout")
    doc._on_contact(230.0, 320.0)                      # (the tool returns to Floor after a contact)
    doc.tools.set_current("cutout")
    assert doc.clear_btn.toolTip().startswith("Clear cut-outs")
    doc.clear_btn.click()
    assert doc._fg == [] and len(doc._regions) == 1 and doc._floor == floor
    assert "region" in doc.undo_btn.toolTip()


def test_a_new_photo_does_not_inherit_the_last_projects_name_and_id(app, tmp_path, monkeypatch):
    """Finding T13: load_image reset the trace and the project but not the Name and Field id, so
    a second room traced after generating the first went out under the first one's name and id --
    and deploying it replaced the first room in the game."""
    pytest.importorskip("PIL")
    doc, run = _traced(app, tmp_path)
    doc.name_box.setText("ROOMA")
    doc.id_box.setText("30500")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    (tmp_path / "b").mkdir()
    from PIL import Image
    photo_b = tmp_path / "b" / "attic-2 view.png"
    Image.new("RGB", (800, 600), (90, 80, 70)).save(photo_b)
    doc.load_image(photo_b)
    assert doc.name_box.text() == "ATTIC_2_VIEW"        # the photo's own name, as a field token
    assert doc.id_box.text() == ""                      # never the last project's id...
    assert "30500" in doc.status.text() and "Field id" in doc.status.text()   # ...and it says why
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.on_generate()
    assert len(run.calls) == 1                          # no id: refused, nothing launched


def test_generate_while_another_job_runs_says_so(app, tmp_path, monkeypatch):
    """Finding T30: run_job refuses (returns False) while another job runs, and Generate had no
    else -- the click did nothing at all, with no word."""
    pytest.importorskip("PIL")
    doc, run = _traced(app, tmp_path)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_run", lambda argv, **kw: False)
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert doc._project is None
    assert "Another job is running" in doc.status.text()
    assert doc.status.property("state") == "warn"


def test_the_event_message_box_is_labelled_and_tells_the_truth(app, tmp_path):
    """Finding T31: a bare box pre-filled with '...' (shipped as a literal ellipsis popup when
    left alone), capped at 180 px, with no label -- and a tooltip saying the words were not
    written to the file, when Generate writes them into [[event]] and the session record."""
    pytest.importorskip("PIL")
    doc, _ = _traced_doc(app, tmp_path)
    doc.tools.set_current("regions")
    doc.rkind_btns["event"].setChecked(True)
    QApplication.processEvents()
    # its placeholder + accessible name are the label: a visible 'Message' label spilled the
    # tools row in Regions mode and pushed the drawn zones off the canvas (review of T23)
    assert doc.ev_msg.text() == "" and doc.ev_msg.placeholderText()
    assert doc.ev_msg.accessibleName()
    assert doc.ev_msg.maximumWidth() > 180
    tip = doc.ev_msg.toolTip()
    assert "not in the file" not in tip and "field.toml" in tip


def test_a_cut_out_entry_leads_with_what_the_author_must_know(app, tmp_path, monkeypatch):
    """Finding T32: each entry read 'fg0 @ (cx,cy) · z N · <png> · snip' in a fixed-width combo,
    so the PNG (or that it is missing) and snip-vs-full were the part cut off. The state leads;
    the pixel and z (already on the canvas label) move to the item's tooltip."""
    pytest.importorskip("PIL")
    from PIL import Image
    doc, _ = _traced(app, tmp_path)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: None)
    doc.fg_btn.setChecked(True)
    doc._on_contact(230.0, 320.0)
    assert doc.fg_box.itemText(0) == "fg0 · ⚠ needs its PNG"
    snip = tmp_path / "pillar_snip.png"
    Image.new("RGBA", (40, 180), (68, 60, 82, 255)).save(snip)
    monkeypatch.setattr(doc, "_ask_cutout", lambda: str(snip))
    doc.on_fg_attach()
    assert doc.fg_box.itemText(0) == "fg0 · snip · pillar_snip.png"   # free-length name last
    tip = _fg_tip(doc, 0)
    assert "(230,320)" in tip and "z 1073" in tip


def test_the_tab_reads_the_photo_through_the_builds_one_reader(app, tmp_path, monkeypatch):
    """Findings T19 + E11, the tab half: 'the build uses the exact crop shown here' holds only if
    the canvas and the build read the photo through ONE function (upright, 16-bit scaled)."""
    pytest.importorskip("PIL")
    from PIL import Image
    from ff9mapkit import imagefield as IF
    p = tmp_path / "phone.jpg"
    im = Image.new("RGB", (800, 400), (200, 30, 30))
    exif = Image.Exif()
    exif[0x0112] = 6
    im.save(p, exif=exif)
    seen = []
    real = IF.open_rgb
    monkeypatch.setattr(IF, "open_rgb", lambda path: seen.append(str(path)) or real(path))
    doc, _ = _doc(app)
    doc.load_image(p)
    assert seen == [str(p)]                            # the build's own reader, spent
    assert doc._img_size == (400, 800)                 # upright: the cut-out frame and snip scale


def test_the_canvas_keeps_a_usable_minimum(app):
    """The canvas had no minimum of its own (66 px, the scroll area's). A floor ABOVE what the
    window can give overpaints the rows below, so it is modest: 96 px (measured natively, the
    canvas has ~100 px at 1024x720 and 125% with every row showing)."""
    doc, _ = _doc(app)
    assert 96 <= doc.canvas.minimumHeight() <= 100


# --------------------------------------------------------------- batch 3, the final review
def _sideways_jpeg(tmp_path, name="IMG_0001.jpg"):
    """A phone photo: 1200x800 raw pixels carrying EXIF Orientation 6 (shown upright it is 800
    wide, 1200 tall). The raw frame has a green band along its BOTTOM."""
    from PIL import Image
    im = Image.new("RGB", (1200, 800), (40, 90, 160))
    im.paste((40, 170, 40), (0, 500, 1200, 800))
    exif = Image.Exif()
    exif[0x0112] = 6
    p = tmp_path / name
    im.save(p, exif=exif)
    return p


def _project_traced_on_the_raw_frame(tmp_path):
    """A project as the kit BEFORE open_rgb built it: art cropped from the photo's raw, unturned
    pixels, and a session record (no 'upright' key) whose floor is in that raw frame."""
    import json
    from PIL import Image
    from ff9mapkit import imagefield as IF
    photo = _sideways_jpeg(tmp_path)
    raw = tmp_path / "raw.png"
    with Image.open(photo) as src:
        src.convert("RGB").save(raw)                   # the pixels as stored: no EXIF turn
    floor = [(60.0, 330.0), (320.0, 330.0), (364.0, 440.0), (20.0, 440.0)]
    man = IF.build_image_field(raw, floor, tmp_path / "proj", name="PHONE", field_id=30779, pitch=21)
    toml = Path(man["toml"])
    side = toml.parent / "IMG_0001.trace.json"
    side.write_text(json.dumps({"image": str(photo), "pitch": 21, "floor": [list(q) for q in floor],
                                "fg": [], "regions": [], "name": "PHONE", "id": "30779"}),
                    encoding="utf-8")
    raw.unlink()
    return toml, side, photo, floor


def test_a_project_traced_before_photos_were_turned_upright_reopens_on_its_own_art(app, tmp_path):
    """The kit now turns a phone photo upright (T19). A record written BEFORE that holds its floor
    in the photo's raw, sideways frame: loading the turned photo under it put the old floor over
    the sky, armed as in sync, and the next Generate rotated the art under an unchanged walkmesh.
    Such a record reopens from the project's own art -- the exact frame it was traced on -- and
    says why; the record a new Generate writes says which frame it is in."""
    pytest.importorskip("PIL")
    import json
    toml, side, photo, floor = _project_traced_on_the_raw_frame(tmp_path)
    doc, _ = _doc(app)
    doc.load_project(toml)
    assert doc._image == toml.parent / "art" / "base.png", doc._image
    assert [tuple(q) for q in doc._floor] != [] and doc._project is not None
    text = doc.status.text()
    assert text.startswith("\u26a0") and "orientation" in text and "sideways" not in text, text
    assert doc.status.property("state") == "warn"      # (true for a mirrored or upside-down photo too)
    px = doc._pixmap.toImage().pixelColor(doc._pixmap.width() // 2, doc._pixmap.height() - 8)
    assert px.green() > px.blue(), "the floor band is not under the floor: the photo was turned"
    doc._write_trace_sidecar(toml.parent)              # what the next Generate records
    rec = json.loads(side.read_text(encoding="utf-8"))
    assert rec["upright"] is True and rec["image"] == str(toml.parent / "art" / "base.png")


def test_a_record_written_now_reopens_its_turned_photo(app, tmp_path):
    """The other half: a session traced on the upright photo records that, and reopens the PHOTO
    (not the built art) however the photo is stored."""
    pytest.importorskip("PIL")
    import json
    photo = _sideways_jpeg(tmp_path)
    doc, _ = _doc(app)
    doc.load_image(photo)
    assert doc._pixmap.height() > doc._pixmap.width()  # upright: 800 wide, 1200 tall, cover-cropped
    doc.canvas._commit_floor([(60.0, 330.0), (320.0, 330.0), (364.0, 440.0), (20.0, 440.0)])
    out = tmp_path / "proj"
    doc._write_trace_sidecar(out)
    side = next(out.glob("*.trace.json"))
    assert json.loads(side.read_text(encoding="utf-8"))["upright"] is True
    (out / "IMG.field.toml").write_text("[field]\nid = 30779\n", encoding="utf-8")
    doc2, _ = _doc(app)
    doc2.load_trace(side)
    assert doc2._image == photo and not doc2.status.text().startswith("\u26a0")


def _hyphen_named_project(tmp_path):
    """A project the kit built before it checked names: attic-room.field.toml."""
    toml, floor = _built_project(tmp_path, with_fg=False)
    old = toml.with_name("attic-room.field.toml")
    text = toml.read_text(encoding="utf-8")
    assert text.count('name = "HALL3"') == 1
    old.write_text(text.replace('name = "HALL3"', 'name = "attic-room"'), encoding="utf-8")
    toml.unlink()
    return old, floor


def test_a_project_named_before_the_name_rule_still_regenerates(app, tmp_path):
    """T7 refuses a field name that is not letters, digits and underscores -- but a project may
    already carry one (the kit never checked before). Its Generate refused the name, and the
    renamed one was refused too ('this folder already holds attic-room.field.toml'): no Name
    worked. The rule guards the mint of a NEW file; a name that already is a file is past it."""
    pytest.importorskip("PIL")
    toml, _floor = _hyphen_named_project(tmp_path)
    doc, run = _doc(app)
    doc.load_project(toml)
    assert doc.name_box.text() == "attic-room"
    doc.on_generate()
    assert len(run.calls) == 1, doc.status.text()
    argv = run.calls[0][0]
    assert "--name=attic-room" in argv
    doc.name_box.setText("attic room")                 # a NEW bad name is still refused
    doc.on_generate()
    assert len(run.calls) == 1 and doc.status.property("state") == "error"


def test_an_undo_across_a_generate_is_unsaved_work(app, tmp_path):
    """T25's check read 'in sync' after an Undo that took the canvas back past the last Generate:
    the project on disk held the newer floor, and closing the app or opening another photo threw
    the undone state away without asking. Undo is a gesture the project does not have."""
    pytest.importorskip("PIL")
    toml, floor = _built_project(tmp_path, with_fg=False)
    doc, run = _doc(app)
    doc.load_project(toml)
    doc.canvas._commit_floor([(120.0, 210.0)] + [tuple(q) for q in floor[1:]])
    doc.on_generate()
    assert len(run.calls) == 1 and not doc.has_unsaved()
    doc.on_undo()
    assert doc.has_unsaved()


def test_an_event_drawn_with_an_empty_message_box_says_so(app, tmp_path):
    """T31 took the '...' pre-fill out of the message box, but a zone drawn with the box empty
    still ships a literal '...' popup -- and the status said only 'drew an event zone'."""
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.load_image(_photo(tmp_path))
    doc.tools.set_current("regions")
    doc.rkind_btns["event"].setChecked(True)
    quad = [(-200.0, 900.0), (200.0, 900.0), (200.0, 1300.0), (-200.0, 1300.0)]
    doc.ev_msg.setText("")
    doc._on_region_drawn(quad)
    assert "no words yet" in doc.status.text(), doc.status.text()
    doc.ev_msg.setText("The floor creaks.")
    doc._on_region_drawn([(x + 500.0, z) for x, z in quad])
    assert "no words yet" not in doc.status.text()


def test_a_renamed_field_in_a_folder_named_before_the_rule_still_regenerates(app, tmp_path):
    """The exemption asked whether the Name box equals the armed [field] name. An author who had
    already renamed the field in the Editor (attic_room, in attic-room.field.toml) was back in
    the circle: every valid name was refused by 'this folder already holds attic-room.field.toml',
    and attic-room by the name rule. The exemption is the backend's own: the name already names
    a file in the folder."""
    pytest.importorskip("PIL")
    toml, _floor = _hyphen_named_project(tmp_path)
    toml.write_text(toml.read_text(encoding="utf-8").replace('name = "attic-room"',
                                                             'name = "attic_room"'), encoding="utf-8")
    doc, run = _doc(app)
    doc.load_project(toml)
    assert doc.name_box.text() == "attic_room"
    doc.on_generate()
    assert len(run.calls) == 0 and "attic-room" in doc.status.text()   # told which name works...
    doc.name_box.setText("attic-room")
    doc.on_generate()
    assert len(run.calls) == 1, doc.status.text()                      # ...and it does


def test_the_regions_tool_says_zone_and_how_to_cancel(app, tmp_path):
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    tip = doc.tools.button("regions").toolTip()
    assert "zones" in tip and "quad" not in tip and "Esc" in tip, tip
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 440)])
    doc.tools.set_current("regions")
    doc.rkind_btns["event"].setChecked(True)
    doc.ev_msg.setText("The floor creaks.")
    doc._on_region_drawn([(-200.0, 900.0), (200.0, 900.0), (200.0, 1300.0), (-200.0, 1300.0)])
    doc._refresh()
    assert "Zones: 1" in doc.ins_zones.text() and "region" not in doc.status.text(), \
        doc.status.text()


# --------------------------------------------------------------------------- T33: Detect floor
def _room_photo(tmp_path):
    """A photo with a floor auto_floor can find: a lit trapezoid on a dark room."""
    from PIL import Image, ImageDraw
    p = tmp_path / "room-photo.png"
    im = Image.new("RGB", (1200, 900), (60, 60, 90))
    ImageDraw.Draw(im).polygon([(360, 450), (840, 450), (1200, 900), (0, 900)], fill=(150, 120, 80))
    im.save(p)
    return p


def test_detect_floor_seeds_an_empty_floor_as_one_undoable_gesture(app, tmp_path):
    """Finding T33: the tab never called imagefield.auto_floor, the seed the CLI tracer had."""
    pytest.importorskip("numpy")
    doc, _run = _doc(app)
    assert not doc.detect_btn.isEnabled()                # nothing to detect on yet
    doc.load_image(_room_photo(tmp_path))
    assert doc.detect_btn.isEnabled() and "starting outline" in doc.detect_btn.toolTip().lower()
    doc.detect_btn.click()
    assert len(doc._floor) >= 3 and doc.canvas.floor() == doc._floor
    assert all(0 <= x <= 384 and 0 <= y <= 448 for x, y in doc._floor)
    assert len(doc._history) == 1 and doc.gen_btn.isEnabled()   # the hand trace's own gate
    assert "starting outline" in doc.status.text() and "drag" in doc.status.text()
    doc.on_undo()
    assert doc._floor == [] and doc.canvas.floor() == []


def test_detect_floor_never_replaces_a_traced_floor(app, tmp_path):
    pytest.importorskip("numpy")
    doc, _run = _doc(app)
    doc.load_image(_room_photo(tmp_path))
    mine = [(100.0, 300.0), (280.0, 300.0), (190.0, 430.0)]
    doc.canvas._commit_floor(mine)
    doc.detect_btn.click()
    assert doc._floor == mine and len(doc._history) == 1
    assert "Clear the floor first" in doc.status.text()
    assert doc.status.property("state") == "warn"


def test_detect_floor_says_why_in_the_tabs_words_when_it_finds_none(app, tmp_path):
    pytest.importorskip("numpy")
    doc, _run = _doc(app)
    doc.load_image(_photo(tmp_path))                     # one flat colour: no floor boundary
    doc.detect_btn.click()
    said = doc.status.text()
    assert said.startswith("⚠ No floor found") and doc.status.property("state") == "warn", said
    assert "--" not in said and "auto floor-seed" not in said, said
    assert "trace it by hand" in said, said
    from PySide6.QtGui import QGuiApplication
    assert QGuiApplication.overrideCursor() is None     # the busy cursor ends with a refusal too
    assert doc._floor == [] and doc._history == []


def test_detect_floor_without_numpy_is_disabled_and_says_why(app, tmp_path, monkeypatch):
    import importlib.util
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda name, *a: None if name == "numpy" else real(name, *a))
    doc, _run = _doc(app)
    doc.load_image(_photo(tmp_path))
    assert not doc.detect_btn.isEnabled() and "numpy" in doc.detect_btn.toolTip()


def test_detect_floor_is_a_floor_tool_control(app, tmp_path):
    pytest.importorskip("PIL")
    doc, _ = _traced_doc(app, tmp_path)
    assert doc.detect_btn.isVisible()
    doc.tools.set_current("regions")
    assert not doc.detect_btn.isVisible()


def test_a_field_that_is_not_a_trace_project_keeps_the_opening_teach_first(app, tmp_path):
    """Batch 4 left (T39): with nothing loaded, selecting a field in the tree replaced the opening
    teach with '<field> was not loaded here'. The teach stays; the note follows it."""
    doc, _ = _doc(app)
    teach = doc.status.text()
    plain = tmp_path / "plain.field.toml"
    plain.write_text('[field]\nid = 4003\nname = "X"\narea = 11\n', encoding="utf-8")
    doc.offer_project(plain)
    said = doc.status.text()
    assert said.startswith(teach) and "plain.field.toml (the open field) was not loaded here" in said, said


def test_a_stopped_regenerate_says_stopped(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    stop = []
    doc, run, toml = _armed(app, tmp_path, monkeypatch, was_stopped=lambda: bool(stop))
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 445)])
    doc.on_generate()
    stop.append(1)
    run.calls[-1][1]["on_finished"](1)                 # the file is as it was
    said = doc.status.text()
    assert "Regenerate stopped" in said and "failed" not in said, said
    assert doc.status.property("state") == "warn" and not doc._stamped


# --------------------------------------------------------------------------- T35: the empty canvas
def test_the_bare_tab_asks_for_a_photo_where_the_canvas_will_be(app, tmp_path):
    """Finding T35: with nothing loaded the canvas was an empty frame over a muted one-liner. A
    centred prompt stands in for it until a photo opens."""
    pytest.importorskip("PIL")
    doc, _ = _doc(app)
    doc.resize(760, 700)
    doc.show()
    QApplication.processEvents()
    assert doc.empty_msg.isVisible() and not doc.canvas.isVisible()
    assert "Open or drop a photo" in doc.empty_msg.text()
    assert doc.empty_msg.property("role") == "muted"         # an existing role, no new style
    doc.load_image(_photo(tmp_path))
    assert doc.canvas.isVisible() and not doc.empty_msg.isVisible()


# --------------------------------------------------------------------------- T34: the floor's size
def test_the_inspector_says_how_big_the_traced_floor_is_in_world_units(app, tmp_path):
    """Finding T34: nothing said how large the traced floor will be in the game. The Inspector's
    floor line gives its world extent, re-judged with the pitch; with a vertex above the horizon
    there is no size to give."""
    pytest.importorskip("PIL")
    from ff9mapkit import imagefield as IF
    doc, _ = _doc(app)
    doc.load_image(_photo(tmp_path))
    pts = [(100, 300), (280, 300), (280, 430), (100, 430)]
    doc.canvas._commit_floor(pts)
    world = [IF.click_to_world(doc.canvas.camera(), p) for p in pts]
    w = max(x for x, _ in world) - min(x for x, _ in world)
    d = max(z for _, z in world) - min(z for _, z in world)

    def about(v):
        return int(round(v, -2 if v >= 1000 else -1))
    assert f"floor about {about(w)} × {about(d)} units" in doc.ins_floor.text(), doc.ins_floor.text()
    doc.pitch.setValue(40)                               # a steeper camera: a smaller floor
    assert f"about {about(w)} × {about(d)}" not in doc.ins_floor.text()
    doc.canvas._commit_floor([(100, 50)] + pts[1:])      # above the horizon: no honest size
    doc.pitch.setValue(6)
    assert "units" not in doc.ins_floor.text()


# --------------------------------------------------------------------------- T41: the Inspector summary
def test_the_inspector_summary_follows_the_session(app, tmp_path, monkeypatch):
    """Finding T41: the Inspector was empty on Trace while one status line carried every count.
    The docked summary names the photo, the pitch, each tally with its warning, the project
    folder, whether the last Generate has seen the session, and the next step."""
    pytest.importorskip("PIL")
    doc, run = _doc(app)
    assert doc.ins_photo.fullText() == "No photo open" and "Open or drop a photo" in doc.ins_next.text()
    doc.load_image(_photo(tmp_path))
    doc.canvas._commit_floor([(100, 100), (280, 100), (280, 430), (100, 430)])
    assert doc.ins_photo.fullText() == "Photo: photo.png"
    assert doc.ins_pitch.text().startswith(f"Pitch {doc.pitch.value()}°")
    assert doc.ins_floor.text().startswith("Floor: 4 vertices")
    assert doc.ins_proj.fullText() == "Not generated yet"
    doc.pitch.setValue(6)                                # two vertices go above the horizon
    assert "⚠ 2 above the horizon" in doc.ins_floor.text()
    assert doc.ins_floor.property("state") == "warn"
    assert doc.ins_next.text() == doc.gen_btn.toolTip()  # not ready: why, in the button's words
    assert doc.status.text().startswith("⚠ 2 above the horizon"), doc.status.text()
    doc.pitch.setValue(26)
    assert doc.ins_floor.property("state") == ""
    doc.tools.set_current("regions")
    doc._on_region_drawn([(-200.0, 900.0), (200.0, 900.0), (200.0, 1300.0), (-200.0, 1300.0)])
    assert doc.ins_zones.text().startswith("Zones: 1 · ⚠ 1 door without a target")
    doc._on_region_deleted(0)
    doc.id_box.setText("30777")
    monkeypatch.setattr(doc, "_ask_out", lambda: str(tmp_path))
    doc.on_generate()
    assert doc.ins_proj.fullText() == "Folder: photo-field"
    assert doc.ins_proj.toolTip() == str(tmp_path / "photo-field")
    assert doc.ins_stamp.text() == "The last Generate has seen every change."
    assert "Deploy (F9)" in doc.ins_next.text()
    doc.canvas._commit_floor([(100, 110), (280, 100), (280, 430), (100, 430)])
    assert doc.ins_stamp.text().startswith("⚠ Changed since") and "Regenerate" in doc.ins_next.text()
    said = doc.status.text()                             # the stamp IS the next step: said once
    assert said.startswith("⚠ not stamped") and said.count("Regenerate") == 1, said


# --------------------------------------------------------------------------- E12: the project's own rows
def _ctx_rows(doc):
    """The canvas rows that are the project's own (fed for context), by the row the tab holds."""
    return [r for r, back in zip(doc._region_rows_cache, doc._region_back)
            if any(back is c for c in doc._context)]


def test_the_projects_own_doors_and_zones_are_drawn_as_context(app, tmp_path):
    """Finding E12: a door and a zone drawn in the Place tab were not on the Trace canvas at all,
    so the author drew new doors blind to them. They are drawn now, named as the project's own,
    and they are NOT session rows: never counted, never unsaved work, never in the argv."""
    pytest.importorskip("PIL")
    _photo_, _floor, toml, doors, zones = _regionless_project_with_place_rows(tmp_path)
    doc, run = _doc(app)
    doc.load_project(toml)
    assert doc._regions == []                          # still file-side (T1)
    ctx = _ctx_rows(doc)
    assert sorted(r["kind"] for r in ctx) == ["event", "gateway"], doc._region_rows_cache
    assert len(doc.canvas._regions) == 2               # on the canvas
    assert all("(project)" in r["label"] for r in ctx), [r["label"] for r in ctx]
    assert any(r["label"].startswith(doors[0]) for r in ctx)
    assert not doc.has_unsaved()
    doc._refresh()
    assert "zone" not in doc.status.text(), doc.status.text()   # never counted as the trace's
    doc.on_generate()
    argv, _kw = run.calls[0]
    assert "--gateway" not in argv and not any(a.startswith("--event-zone") for a in argv)


def test_a_traced_door_over_the_projects_own_is_judged_by_the_overlap_law(app, tmp_path):
    pytest.importorskip("PIL")
    _photo_, _floor, toml, _doors, _zones = _regionless_project_with_place_rows(tmp_path)
    doc, _run = _doc(app)
    doc.load_project(toml)
    doc.tools.set_current("regions")
    doc.gw_to.setValue(4005)
    over = [(-480.0, 920.0), (-420.0, 920.0), (-420.0, 980.0), (-480.0, 980.0)]   # inside door0
    doc._on_region_drawn(over)
    ctx = _ctx_rows(doc)
    mine = [r for r in doc._region_rows_cache if not any(r is c for c in ctx)]
    assert len(mine) == 1 and "overlaps" in (mine[0]["warn"] or ""), mine
    assert all(r["warn"] is None for r in ctx)          # judged for overlap, nothing else
    doc._refresh()
    assert "1 with law warnings" in doc.status.text(), doc.status.text()


def test_the_projects_own_rows_refuse_every_gesture_and_say_where(app, tmp_path, monkeypatch):
    pytest.importorskip("PIL")
    _photo_, _floor, toml, _doors, _zones = _regionless_project_with_place_rows(tmp_path)
    doc, _run = _doc(app)
    doc.load_project(toml)
    monkeypatch.setattr(doc, "_ask_field_id", lambda cur: (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(doc, "_ask_message", lambda cur: (_ for _ in ()).throw(AssertionError))
    assert len(_ctx_rows(doc)) == 2
    for row in list(_ctx_rows(doc)):
        i = row["i"]
        quad = list(row["quad"])
        moved = [(x + 40, z) for x, z in quad]
        for gesture in (lambda: doc._on_region_deleted(i), lambda: doc._on_region_changed(i, moved),
                        lambda: doc._on_region_retarget(i), lambda: doc._on_region_reword(i)):
            gesture()
            said = doc.status.text()
            assert "Place tab" in said and "Editor" in said, said
            assert doc.status.property("state") == "warn"
            assert doc._history == [] and doc._regions == []
            assert len(_ctx_rows(doc)) == 2
            back = next(r for r in doc.canvas._regions if r["i"] == i)
            assert back["quad"] == quad                     # a drag snaps back to the file's


def test_the_projects_own_rows_are_reread_with_the_project(app, tmp_path, monkeypatch):
    """The finding's own path: Generate, add a door in Place and save, come back to Trace. The
    shell feeds the open field on every show; for the armed project that re-reads its own rows.
    A regenerate's finish re-reads them too."""
    pytest.importorskip("PIL")
    from ff9mapkit.editor.model import FieldDoc
    from ff9mapkit.workspace import placedoc
    doc, run, toml = _armed(app, tmp_path, monkeypatch)
    assert _ctx_rows(doc) == []
    fd = FieldDoc.load(toml)
    placedoc.place_gateway(fd.data, [(-500, 900), (-400, 900), (-400, 1000), (-500, 1000)], 301)
    fd.save()                                          # Place, then Save
    doc.offer_project(str(toml))                       # back on Trace
    assert len(_ctx_rows(doc)) == 1 and not doc.has_unsaved()
    doc.canvas._commit_floor([(130, 200), (254, 200), (364, 440), (20, 445)])
    doc.on_generate()
    fd = FieldDoc.load(toml)
    placedoc.place_event(fd.data, [(100, 900), (200, 900), (200, 1000), (100, 1000)])
    fd.save()                                          # what the merge keeps, on disk
    run.calls[-1][1]["on_finished"](0)
    assert len(_ctx_rows(doc)) == 2


def test_a_project_file_that_cannot_be_read_is_said_not_shown_as_no_rows(app, tmp_path,
                                                                        monkeypatch):
    pytest.importorskip("PIL")
    doc, _run, toml = _armed(app, tmp_path, monkeypatch)
    good = toml.read_text(encoding="utf-8")
    toml.write_text(good + "\n[[gateway]\n", encoding="utf-8")      # broken by hand
    doc.offer_project(str(toml))
    assert "could not read the project's own doors and zones" in doc.status.text()
    toml.write_text(good, encoding="utf-8")
    doc.offer_project(str(toml))
    assert "could not read" not in doc.status.text(), doc.status.text()


def test_a_project_row_out_of_view_at_this_pitch_is_said(app, tmp_path):
    pytest.importorskip("PIL")
    _photo_, _floor, toml, _doors, _zones = _regionless_project_with_place_rows(tmp_path)
    toml.write_text(toml.read_text(encoding="utf-8") + (
        '\n[[gateway]]\nname = "behind"\nto = 302\nzone = [[-100, -9000], [100, -9000], '
        '[100, -8800], [-100, -8800]]\n'), encoding="utf-8")
    doc, _run = _doc(app)
    doc.load_project(toml)
    assert "1 of the project's own" in doc.status.text(), doc.status.text()
    doc._refresh()
    assert "1 of the project's own" in doc.status.text(), doc.status.text()


def test_a_pre_prefix_door_the_session_reemits_is_not_drawn_twice(app, tmp_path):
    """A project from before the traced_ prefix calls its traced door door0. Reopened from its
    record, the session holds that door; the regenerate merge replaces the file's door0 with it
    (the same quad), so it is the session's, not the project's own context."""
    pytest.importorskip("PIL")
    import json
    from PIL import Image
    from ff9mapkit import imagefield as IF
    photo = tmp_path / "room.png"
    Image.new("RGB", (1536, 1792), (90, 80, 70)).save(photo)
    floor = [(130.0, 200.0), (254.0, 200.0), (364.0, 440.0), (20.0, 440.0)]
    man = IF.build_image_field(photo, floor, tmp_path / "proj", name="OLD", field_id=30795,
                               gateways=["4005@60,300;140,300;140,330;60,330"])
    toml = Path(man["toml"])
    toml.write_text(toml.read_text(encoding="utf-8").replace('"traced_door0"', '"door0"'),
                    encoding="utf-8")
    (toml.parent / "room.trace.json").write_text(json.dumps({
        "image": str(photo), "upright": True, "pitch": int(IF.DEFAULT_PITCH),
        "floor": [list(p) for p in floor], "fg": [],
        "regions": [{"kind": "gateway", "to": 4005, "entrance": 0, "message": "...",
                     "quad": [[60, 300], [140, 300], [140, 330], [60, 330]]}],
        "name": "OLD", "id": "30795"}), encoding="utf-8")
    doc, _run = _doc(app)
    doc.load_project(toml)
    assert len(doc._regions) == 1 and _ctx_rows(doc) == []
