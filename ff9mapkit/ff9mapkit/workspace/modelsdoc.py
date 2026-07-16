"""The Models tab -- the custom-3D-models pillar's front door in the Workspace.

Browser (left): every GEO model the kit knows (catalog.models), searchable + group-filtered, with
REAL rendered thumbnails (models/preview.py via thumbs.ModelThumbService -- per-user disk cache;
a machine without the install degrades to text rows). Detail (right): the preview still, catalog
facts + the render's counts sidecar, the model->animation join, appearance caveats (story-evolved
forms / the Garnet hair-swap), overworld actor identity, and a ready snippet. Actions: the whole
DLL-free round-trip in ONE place -- export a Blender-editable .glb, import the edited .glb back,
mint a new id (>=6000), dump editable .anim clips -- each streaming ``py -m ff9mapkit model-*``
through the shell's job runner. (Moved here from the Import tab, which now points at this tab.)

Same doc conventions as ImportDoc/BuildDoc: constructor injection (pal, kit root, run/problems
callbacks), a ``_kit`` streamer, ``_busy`` button-disable, ``crumb_label()`` for the breadcrumb.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QScrollArea, QSplitter, QVBoxLayout, QWidget)

from .. import catalog
from ..models.appearance import appearance_notes
from . import thumbs as thumbs_mod, widgets

_ICON = 56                                       # list-row icon size (px)
_DETAIL_IMG = 224                                # detail-pane preview size (px)
_THUMB_BATCH = 96                                # thumbnails auto-requested per filter result (top of list)

_GROUPS = [                                      # combo label -> catalog.models(group=...) arg (None = all)
    ("All groups", None),
    ("Characters (MAIN)", "MAIN"),
    ("NPCs", "NPC"),
    ("Monsters", "MON"),
    ("Sub && world (SUB)", "SUB"),
    ("Weapons (WEP)", "WEP"),
    ("Accessories (ACC)", "ACC"),
]


class ModelsDoc(QWidget):
    """Browse every FF9 model with rendered previews + run the whole edit round-trip on the selection."""

    def __init__(self, pal, kit_root, *, run, problems=None, model_thumbs=None, parent=None):
        super().__init__(parent)
        self.pal = pal
        self.kit = str(kit_root)
        self._run = run
        self._problems = problems
        self.thumbs = model_thumbs if model_thumbs is not None else thumbs_mod.ModelThumbService(self)
        self.thumbs.ready.connect(self._thumb_ready)
        self._current = None                     # the selected catalog.Model (or None)
        self._items = {}                         # geo name -> QListWidgetItem (the CURRENT filter's rows)
        self._blank = QPixmap(_ICON, _ICON)      # constant-size placeholder so rows never shift
        self._blank.fill(Qt.GlobalColor.transparent)
        self._build()
        self._refill()

    # ------------------------------------------------------------------ layout
    def _build(self):
        muted = f"color:{self.pal['muted']};"
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        split = QSplitter()
        root.addWidget(split)

        # ---- left: the browser ----
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 6, 0)
        srow = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setAccessibleName("Search models")
        self.search.setPlaceholderText("Search by name, token, or a friendly name — vivi, GRN, MON_B3…")
        self.search.textChanged.connect(self._refill)
        srow.addWidget(self.search, 1)
        lv.addLayout(srow)
        frow = QHBoxLayout()
        self.group = QComboBox()
        self.group.setAccessibleName("Filter models by group")
        for label, _arg in _GROUPS:
            self.group.addItem(label)
        self.group.currentIndexChanged.connect(self._refill)
        frow.addWidget(self.group)
        self.field_only = QCheckBox("Field-placeable only")
        self.field_only.setToolTip("Keep the field-form (F*) models — the ones an [[npc]] can wear.")
        self.field_only.toggled.connect(self._refill)
        frow.addWidget(self.field_only)
        frow.addStretch(1)
        lv.addLayout(frow)
        self.listw = QListWidget()
        self.listw.setAccessibleName("Model catalog")
        self.listw.setIconSize(QSize(_ICON, _ICON))
        self.listw.setUniformItemSizes(True)
        self.listw.currentItemChanged.connect(self._on_select)
        lv.addWidget(self.listw, 1)
        self.count_lbl = QLabel("")
        self.count_lbl.setProperty("role", "muted")
        lv.addWidget(self.count_lbl)
        split.addWidget(left)

        # ---- right: detail + actions (scrolled) ----
        right_host = QWidget()
        rv = QVBoxLayout(right_host)
        rv.setContentsMargins(10, 0, 0, 0)
        self.d_title = QLabel("Pick a model")
        self.d_title.setTextFormat(Qt.TextFormat.PlainText)
        self.d_title.setProperty("role", "head")
        rv.addWidget(self.d_title)
        self.d_sub = QLabel("")
        self.d_sub.setProperty("role", "muted")
        self.d_sub.setWordWrap(True)
        rv.addWidget(self.d_sub)

        img_row = QHBoxLayout()
        self.d_img = QLabel()
        self.d_img.setFixedSize(_DETAIL_IMG, _DETAIL_IMG)
        self.d_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # BOTH of this round's traps in one expression, and it survived the SPEND census because that
        # census grepped `background:{...}` -- this rule's background is `transparent` and the hex rode on
        # `border`. `'border'` is in all 8 palettes, so the `.get` default could never fire (dead), and
        # `#444` is a palette-blind grey that no theme switch can reach (loaded). Index it.
        self.d_img.setStyleSheet("background:transparent;"          # was pal.get('panel', ...) -- 'panel' is not a token
                                 f"border:1px solid {self.pal['border']};border-radius:6px;")
        img_row.addWidget(self.d_img)
        facts_col = QVBoxLayout()
        self.d_facts = QLabel("")
        self.d_facts.setWordWrap(True)
        facts_col.addWidget(self.d_facts)
        self.d_notes = widgets.caption("")   # appearance caveats -> a small cautionary note
        self.d_notes.setProperty("state", "warn")
        facts_col.addWidget(self.d_notes)
        self.d_anims = QLabel("")
        self.d_anims.setWordWrap(True)
        self.d_anims.setProperty("role", "muted")
        facts_col.addWidget(self.d_anims)
        facts_col.addStretch(1)
        img_row.addLayout(facts_col, 1)
        rv.addLayout(img_row)
        copy_row = QHBoxLayout()
        self.copy_name_btn = QPushButton("Copy name")
        self.copy_name_btn.clicked.connect(self._copy_name)
        copy_row.addWidget(self.copy_name_btn)
        self.copy_snip_btn = QPushButton("Copy [[npc]] snippet")
        self.copy_snip_btn.clicked.connect(self._copy_snippet)
        copy_row.addWidget(self.copy_snip_btn)
        copy_row.addStretch(1)
        rv.addLayout(copy_row)

        rv.addWidget(self._actions_box())
        rv.addWidget(self._playable_box())
        rv.addWidget(self._deployed_box())
        rv.addStretch(1)

        right = QScrollArea()
        # NoFrame like the other 7: Qt draws its own frame here otherwise, in a colour taken from the
        # STYLE palette rather than ours -- it is in no palette, never re-tints on a theme switch, and
        # measured #eaebee/1.011 in light and ~1.24 in the darks. Quiet, but un-chosen. 7 of 10 already
        # set this; these were the stragglers.
        right.setFrameShape(QFrame.Shape.NoFrame)
        right.setWidgetResizable(True)
        # vertical-only: wrappable labels + shrinkable line edits must re-flow, never clip sideways
        right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right.setWidget(right_host)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        split.setSizes([340, 640])

    def _actions_box(self):
        """The DLL-free round-trip, keyed on the selected model. Same argv shapes the Import tab's old
        models box streamed -- the object names (mdl_*) are kept so the smoke + muscle memory carry."""
        muted = f"color:{self.pal['muted']};"
        box = widgets.section("Edit this model")
        v = box.content_layout

        dep = QHBoxLayout()
        _l_dep = QLabel("Deploy into:")
        dep.addWidget(_l_dep)
        from ..editor import jobs
        gm = jobs.detect_game_mod()
        self.mdl_mod = QLineEdit(str(gm) if gm else "")
        self.mdl_mod.setPlaceholderText("a mod folder, e.g. <game>/FF9CustomMap")
        _l_dep.setBuddy(self.mdl_mod)          # see the buddy note in coopdoc
        dep.addWidget(self.mdl_mod, 1)
        mb = QPushButton("Browse…")
        mb.clicked.connect(self.browse_model_mod)
        dep.addWidget(mb)
        v.addLayout(dep)

        exp = QHBoxLayout()
        self.mdl_gltf_btn = QPushButton("Export .glb…")
        self.mdl_gltf_btn.setToolTip("Write the selected model as a Blender-openable glTF "
                                     "(File ▸ Import ▸ glTF 2.0): mesh + rig + textures + animations.")
        self.mdl_gltf_btn.clicked.connect(self.on_model_gltf)
        exp.addWidget(self.mdl_gltf_btn)
        _l_anims = QLabel("anims:")
        exp.addWidget(_l_anims)
        self.mdl_anims = QComboBox()
        _l_anims.setBuddy(self.mdl_anims)
        self.mdl_anims.addItems(["auto", "all", "none"])
        self.mdl_anims.setToolTip("Which clips to embed in the .glb: auto = idle/walk/run/turns; "
                                  "all = the model's whole folder; none = mesh only.")
        exp.addWidget(self.mdl_anims)
        exp.addStretch(1)
        v.addLayout(exp)

        clips = QHBoxLayout()
        self.mdl_anim_btn = QPushButton("Dump editable clips…")
        self.mdl_anim_btn.setToolTip("Write the model's animation clips as hand-editable .anim JSON "
                                     "(model-anim). Deploy an edited clip by copying it into a mod folder's "
                                     "StreamingAssets/Assets/Resources/Animations/<id>/.")
        self.mdl_anim_btn.clicked.connect(self.on_model_anim)
        clips.addWidget(self.mdl_anim_btn)
        clips.addStretch(1)
        v.addLayout(clips)

        rsk = QHBoxLayout()
        self.mdl_tex_btn = QPushButton("Export textures…")
        self.mdl_tex_btn.setToolTip("The CHEAPEST edit — no Blender: write the model's textures as "
                                    "editable PNGs (any editor, any size, keep the names).")
        self.mdl_tex_btn.clicked.connect(self.on_model_textures)
        rsk.addWidget(self.mdl_tex_btn)
        self.mdl_reskin_btn = QPushButton("Deploy reskin PNG(s)…")
        self.mdl_reskin_btn.setToolTip("Ship edited {name}.png file(s) into the mod folder — the engine "
                                       "probes them by NAME and swaps the texture, mesh untouched.")
        self.mdl_reskin_btn.clicked.connect(self.on_model_reskin)
        rsk.addWidget(self.mdl_reskin_btn)
        rsk.addStretch(1)
        v.addLayout(rsk)

        imp = QHBoxLayout()
        _l_glb = QLabel("Edited .glb:")
        imp.addWidget(_l_glb)
        self.mdl_glb = QLineEdit()
        _l_glb.setBuddy(self.mdl_glb)
        self.mdl_glb.setPlaceholderText("the .glb you exported from Blender (drag-and-drop works too)")
        imp.addWidget(self.mdl_glb, 1)
        gb = QPushButton("Browse…")
        gb.clicked.connect(self.browse_model_glb)
        imp.addWidget(gb)
        self.mdl_import_btn = QPushButton("Import model")
        self.mdl_import_btn.setToolTip("Splice the edited geometry back over the pristine rig (auto-detected "
                                       "from the kit's glTF stamp) + write any CHANGED animation clips.")
        self.mdl_import_btn.clicked.connect(self.on_model_import)
        imp.addWidget(self.mdl_import_btn)
        v.addLayout(imp)

        mint = QHBoxLayout()
        _l_mint = QLabel("Mint new id:")
        mint.addWidget(_l_mint)
        self.mdl_mint_id = QLineEdit("6000")
        _l_mint.setBuddy(self.mdl_mint_id)
        self.mdl_mint_id.setFixedWidth(70)
        self.mdl_mint_id.setToolTip("The new model id — ≥ 6000 (clear of every real id).")
        mint.addWidget(self.mdl_mint_id)
        self.mdl_mint_btn = QPushButton("Mint from model")
        self.mdl_mint_btn.setToolTip("Re-export the selected model to a brand-new id + register it in "
                                     "DictionaryPatch.txt (3DModel line). Place it with [[npc]] model = <id>.")
        self.mdl_mint_btn.clicked.connect(self.on_model_mint)
        mint.addWidget(self.mdl_mint_btn)
        mint.addStretch(1)
        v.addLayout(mint)

        hint = QLabel("Mesh edits show on F6 → Reload; edited ANIMATIONS and newly MINTED ids need a game "
                      "relaunch (clips + DictionaryPatch load at startup).")
        hint.setWordWrap(True)
        hint.setProperty("role", "muted")
        v.addWidget(hint)
        self._buttons = [self.mdl_gltf_btn, self.mdl_anim_btn, self.mdl_import_btn, self.mdl_mint_btn,
                         self.mdl_tex_btn, self.mdl_reskin_btn]
        return box

    def _playable_box(self):
        """The 13th-character battle-animset loop (`playable-anims`): export the donor's battle model
        with Blender Actions NAMED by battle motion, edit, route the edits onto the character's OWN
        minted animset (donor untouched). Field-toml-scoped -- the [[playable]] block must carry
        custom_battle_anims = true (editable in the field editor's Playables section)."""
        muted = f"color:{self.pal['muted']};"
        box = widgets.section("Custom playable's battle animset")
        v = box.content_layout
        frow = QHBoxLayout()
        _l_pa = QLabel("field.toml:")
        frow.addWidget(_l_pa)
        self.pa_field = QLineEdit()
        _l_pa.setBuddy(self.pa_field)
        self.pa_field.setPlaceholderText("the field.toml carrying the [[playable]] custom_battle_anims block")
        frow.addWidget(self.pa_field, 1)
        fb = QPushButton("Browse…")
        fb.clicked.connect(self.browse_pa_field)
        frow.addWidget(fb)
        v.addLayout(frow)
        brow = QHBoxLayout()
        self.pa_export_btn = QPushButton("Export donor .glb…")
        self.pa_export_btn.setToolTip("Write the donor battle model with each Action NAMED by battle "
                                      "motion (23_attack, …) — edit any of them in Blender.")
        self.pa_export_btn.clicked.connect(self.on_pa_export)
        brow.addWidget(self.pa_export_btn)
        self.pa_edit_btn = QPushButton("Route edited .glb…")
        self.pa_edit_btn.setToolTip("Splice the edited clips onto the character's OWN minted animset "
                                    "(Animations/<mintId>/) — the donor stays untouched. RELAUNCH to see it.")
        self.pa_edit_btn.clicked.connect(self.on_pa_edit)
        brow.addWidget(self.pa_edit_btn)
        brow.addStretch(1)
        v.addLayout(brow)
        hint = QLabel("For a [[playable]] with custom_battle_anims = true (edit the block in the field "
                      "editor's Playables section). Also survives re-deploys via its anim_edits key.")
        hint.setWordWrap(True)
        hint.setProperty("role", "muted")
        v.addWidget(hint)
        self._buttons += [self.pa_export_btn, self.pa_edit_btn]
        return box

    def browse_pa_field(self):
        f, _ = QFileDialog.getOpenFileName(self, "The field.toml with the [[playable]] block", "",
                                           "field.toml (*.toml)")
        if f:
            self.pa_field.setText(f)

    def _pa_field_arg(self):
        f = self.pa_field.text().strip().strip('"')
        if not f or not Path(f).is_file():
            self._warn("No field.toml", "Pick the field.toml carrying the [[playable]] block first.")
            return None
        return f

    def on_pa_export(self):
        field = self._pa_field_arg()
        if field is None:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Export the donor battle model", "playable_anims.glb",
                                             "glTF binary (*.glb)")
        if not out:
            return
        self._kit(["playable-anims", field, "--export", out], subject="Export donor .glb",
                  ok_next=f"Wrote {out} — Actions are named by battle motion (23_attack, …). Edit in "
                          "Blender (active action only!), then Route edited .glb.")

    def on_pa_edit(self):
        field = self._pa_field_arg()
        if field is None:
            return
        mod = self._model_mod_arg()
        if mod is None:
            return
        glb, _ = QFileDialog.getOpenFileName(self, "The Blender-edited donor .glb", "",
                                             "glTF (*.glb *.gltf)")
        if not glb:
            return
        self._kit(["playable-anims", field, "--edit", glb, "--deploy", mod], subject="Route animset edits",
                  ok_next="Edited clips spliced onto the character's OWN animset (donor untouched). "
                          "RELAUNCH FF9 to see them; add anim_edits = \"<the .glb>\" to the [[playable]] "
                          "block so re-deploys keep the edit.")

    def _deployed_box(self):
        """What's actually deployed model-wise in the 'Deploy into' folder -- overrides / reskins /
        mints / anim overrides / dangling 3DModel lines -- with a confirm-first per-entry revert.
        The loose-override system is write-only; this is the read side."""
        muted = f"color:{self.pal['muted']};"
        box = widgets.section("Deployed in this mod folder")
        v = box.content_layout
        self.dep_list = QListWidget()
        self.dep_list.setAccessibleName("Models deployed in this mod folder")   # no visible label to buddy
        self.dep_list.setMaximumHeight(170)
        v.addWidget(self.dep_list)
        row = QHBoxLayout()
        self.dep_refresh_btn = QPushButton("Refresh")
        self.dep_refresh_btn.clicked.connect(self.on_deployed_refresh)
        row.addWidget(self.dep_refresh_btn)
        self.dep_revert_btn = QPushButton("Revert selected…")
        self.dep_revert_btn.setToolTip("Delete this entry's loose files (a mint also loses its "
                                       "3DModel line). The bundled original takes over again.")
        self.dep_revert_btn.clicked.connect(self.on_deployed_revert)
        row.addWidget(self.dep_revert_btn)
        row.addStretch(1)
        v.addLayout(row)
        self.dep_hint = QLabel("Pick a mod folder above, then Refresh.")
        self.dep_hint.setWordWrap(True)
        self.dep_hint.setProperty("role", "muted")
        v.addWidget(self.dep_hint)
        return box

    def on_deployed_refresh(self):
        from ..models import deployed
        mod = self.mdl_mod.text().strip().strip('"')
        self.dep_list.clear()
        if not mod or not Path(mod).is_dir():
            self.dep_hint.setText("Pick a mod folder above (Deploy into:), then Refresh.")
            return
        try:
            entries = deployed.scan_mod(mod)
        except OSError as e:
            self.dep_hint.setText(f"Scan failed: {e}")
            return
        for e in entries:
            it = QListWidgetItem(deployed.describe(e))
            it.setData(Qt.ItemDataRole.UserRole, e)
            self.dep_list.addItem(it)
        self.dep_hint.setText(f"{len(entries)} deployed entr{'y' if len(entries) == 1 else 'ies'}."
                              if entries else "No loose model overrides in this folder.")

    def on_deployed_revert(self):
        from ..models import deployed
        it = self.dep_list.currentItem()
        if it is None:
            return self._warn("Nothing selected", "Pick a deployed entry to revert first.")
        e = it.data(Qt.ItemDataRole.UserRole)
        mod = self.mdl_mod.text().strip().strip('"')
        detail = deployed.describe(e)
        if QMessageBox.question(self, "Revert this entry?",
                                f"Delete:\n\n{detail}\n\nfrom {mod}?\n\nThe bundled original takes "
                                "over again. A registered mint id needs a game RELAUNCH to unregister.") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            r = deployed.revert_entry(mod, e)
        except (OSError, ValueError) as err:
            return self._warn("Revert failed", str(err))
        bits = [f"removed {len(r['removed'])} folder(s)"]
        if r["directive_removed"]:
            bits.append("stripped the 3DModel line (relaunch to unregister)")
        self.dep_hint.setText(f"Reverted {e['name'] or e['geo_id']}: " + ", ".join(bits) + ".")
        self.on_deployed_refresh()

    # ------------------------------------------------------------------ browser
    def _refill(self, *_a):
        q = self.search.text().strip()
        grp = _GROUPS[self.group.currentIndex()][1]
        entries = catalog.models(q or None, group=grp, field_only=self.field_only.isChecked())
        self.listw.clear()
        self._items = {}
        for m in entries:
            label = m.name + (f"  ·  id {m.id}" if m.id is not None else "")
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, m.name)
            png = self.thumbs.cached(m.name)
            it.setIcon(QPixmap(png) if png else self._blank)
            self.listw.addItem(it)
            self._items[m.name] = it
        self.count_lbl.setText(f"{len(entries)} model(s)"
                               + ("" if thumbs_mod.enabled() else "  ·  previews off"))
        # warm the visible top of the list (the rest render on selection; all cache forever)
        if thumbs_mod.enabled():
            for m in entries[:_THUMB_BATCH]:
                if self.thumbs.cached(m.name) is None:
                    self.thumbs.request(m.name)

    def _thumb_ready(self, name, png):
        it = self._items.get(name)
        if it is not None:
            it.setIcon(QPixmap(png))
        if self._current is not None and self._current.name == name:
            self._set_detail_image(png)

    def _on_select(self, item, _prev=None):
        if item is None:
            return
        m = catalog.model(item.data(Qt.ItemDataRole.UserRole))
        if m is None:
            return
        self._current = m
        self.d_title.setText(f"{m.name}  ·  id {m.id}")
        world = catalog.world_character(m.name)
        sub = f"{m.kind}  ·  group {m.group} / form {m.form}"
        if world:
            sub += f"  ·  OVERWORLD actor — {world}"
        if m.field:
            sub += "  ·  field-placeable"
        self.d_sub.setText(sub)
        absent = self._refresh_facts(m)
        png = None if absent else (self.thumbs.cached(m.name) or self.thumbs.request(m.name))
        if png:
            self._set_detail_image(png)
        else:
            self.d_img.setPixmap(QPixmap())
            self.d_img.setText("no geometry" if absent else
                               ("rendering…" if thumbs_mod.enabled() else "previews off"))

    def _refresh_facts(self, m) -> bool:
        """Fill the facts/notes labels; True if the model is a known UNSHIPPED id (no geometry on disc)."""
        meta = thumbs_mod.model_thumb_meta(m.id)
        acts = catalog.animations_for_model(m.id)
        facts = []
        absent = bool(meta and meta.get("absent"))
        if absent:
            facts.append("UNSHIPPED id: no geometry on disc (a PSX-era catalog leftover) — "
                         "nothing to preview, export, or reskin")
            meta = None
        if meta:
            facts.append(f"{meta.get('bones', '?')} bones · {meta.get('meshes', '?')} mesh part(s) · "
                         f"{meta.get('verts', '?')} verts · {len(meta.get('textures') or [])} texture(s)")
        facts.append(f"{len(acts)} animation action(s)")
        self.d_facts.setText("\n".join(facts))
        notes = appearance_notes(m.name, minted=False)
        self.d_notes.setText("\n".join(notes))
        self.d_notes.setVisible(bool(notes))
        if acts:
            labels = sorted(acts)
            head = ", ".join(labels[:14])
            more = f"  (+{len(labels) - 14} more)" if len(labels) > 14 else ""
            self.d_anims.setText(f"Actions: {head}{more}")
        else:
            self.d_anims.setText("Actions: none catalogued (a numbered battle-only token or a static prop)")
        return absent

    def _set_detail_image(self, png):
        pm = QPixmap(png)
        if not pm.isNull():
            self.d_img.setText("")
            self.d_img.setPixmap(pm.scaled(_DETAIL_IMG, _DETAIL_IMG, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))

    # ------------------------------------------------------------------ copy helpers
    def _copy_name(self):
        if self._current:
            QGuiApplication.clipboard().setText(self._current.name)

    def _copy_snippet(self):
        m = self._current
        if not m:
            return
        if m.group == "WEP":
            text = (f"# {m.name} is a battle WEAPON (a static mesh, id {m.id}).\n"
                    f"# Reskin it with Export textures… → edit the PNG → Deploy reskin PNG(s)…\n"
                    f"# (it lands at BattleMap/BattleModel/6/{m.id}/ in the mod folder)\n")
        else:
            text = (f'[[npc]]\nname = "my_npc"\nmodel = "{m.name}"\npos = [0, 0]\n'
                    f'dialogue = "Hello!"\n')
            if not m.field:
                text = f"# NOTE: {m.name} is a battle/world form — field NPCs usually wear an F* model.\n" + text
        QGuiApplication.clipboard().setText(text)

    # ------------------------------------------------------------------ actions
    def set_glb(self, path):
        """Drag-and-drop entry point (the shell routes a dropped .glb here)."""
        self.mdl_glb.setText(str(path))

    def _warn(self, title, text):
        QMessageBox.warning(self, title, text)

    def _busy(self, b):
        for btn in self._buttons:
            btn.setEnabled(not b)

    def _kit(self, args, *, subject, ok_next=""):
        self._busy(True)

        def _done(_code):
            self._busy(False)

        started = self._run([sys.executable, "-m", "ff9mapkit", *args], cwd=self.kit, subject=subject,
                            ok_headline=f"{subject} — done", ok_next=ok_next,
                            fail_hint="See the Output panel (model commands need UnityPy + your FF9 install).",
                            on_finished=_done)
        if not started:
            self._busy(False)

    def _sel_token(self):
        if self._current is None:
            self._warn("No model", "Pick a model in the list first.")
            return None
        return self._current.name

    def _model_mod_arg(self):
        m = self.mdl_mod.text().strip().strip('"')
        if not m:
            self._warn("No mod folder", "Pick the mod folder to deploy into (Deploy into:).")
            return None
        return m

    def on_model_gltf(self):
        token = self._sel_token()
        if token is None:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Export for Blender", f"{token}.glb",
                                             "glTF binary (*.glb)")
        if not out:
            return
        anims = ["auto", "all", "none"][self.mdl_anims.currentIndex()]
        self._kit(["model-gltf", token, "--out", out, "--anims", anims], subject="Export .glb",
                  ok_next=f"Wrote {out} — Blender: File ▸ Import ▸ glTF 2.0. Edit, export a .glb, then "
                          "Import model below.")

    def on_model_anim(self):
        token = self._sel_token()
        if token is None:
            return
        d = QFileDialog.getExistingDirectory(self, "Folder to write the Animations/<id>/ clip JSONs into")
        if not d:
            return
        self._kit(["model-anim", token, "--out", d], subject="Dump clips",
                  ok_next=f"Wrote editable .anim JSON under {d}. Edit values, then copy the file into a mod "
                          "folder's StreamingAssets/Assets/Resources/Animations/<id>/ and RELAUNCH.")

    def on_model_import(self):
        glb = self.mdl_glb.text().strip().strip('"')
        if not glb or not Path(glb).is_file():
            return self._warn("No .glb", "Pick the edited .glb you exported from Blender.")
        mod = self._model_mod_arg()
        if mod is None:
            return
        self._kit(["model-import", glb, "--deploy", mod], subject="Import model",
                  ok_next="Override deployed. Mesh edits: F6 → Reload on a field using the model. "
                          "Edited animations need a game RELAUNCH.")

    def on_model_mint(self):
        token = self._sel_token()
        if token is None:
            return
        mod = self._model_mod_arg()
        if mod is None:
            return
        mid = self.mdl_mint_id.text().strip()
        if not mid.isdigit() or int(mid) < 6000:
            return self._warn("Bad id", "The mint id must be a number ≥ 6000 (below is the real-model band).")
        self._kit(["model-mint", token, "--id", mid, "--deploy", mod], subject="Mint model",
                  ok_next=f"Minted id {mid} + registered it in DictionaryPatch.txt. RELAUNCH FF9, then "
                          f"place it with [[npc]] model = {mid} (its animations came along from the source).")

    def on_model_textures(self):
        token = self._sel_token()
        if token is None:
            return
        d = QFileDialog.getExistingDirectory(self, "Folder to write the editable texture PNGs into")
        if not d:
            return
        self._kit(["model-reskin", token, "--export-textures", d], subject="Export textures",
                  ok_next=f"Wrote the pristine PNGs to {d}. Edit them in any image editor (any size "
                          "works), KEEP THE NAMES, then Deploy reskin PNG(s)…")

    def on_model_reskin(self):
        token = self._sel_token()
        if token is None:
            return
        mod = self._model_mod_arg()
        if mod is None:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "The edited {name}.png file(s)", "",
                                                "PNG images (*.png)")
        if not files:
            return
        self._kit(["model-reskin", token, "--deploy", mod, "--texture", *files], subject="Deploy reskin",
                  ok_next="Reskin deployed. Field models: F6 → Reload field. Battle/weapon models load "
                          "on battle entry — a RELAUNCH is the sure path.")

    def browse_model_mod(self):
        d = QFileDialog.getExistingDirectory(self, "Mod folder to deploy models into")
        if d:
            self.mdl_mod.setText(d)

    def browse_model_glb(self):
        f, _ = QFileDialog.getOpenFileName(self, "The Blender-edited glTF", "", "glTF (*.glb *.gltf)")
        if f:
            self.mdl_glb.setText(f)

    # ------------------------------------------------------------------ shell hooks
    def crumb_label(self):
        return self._current.name if self._current else "browse 3D models"
