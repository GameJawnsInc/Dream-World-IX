"""The Battle document for the Workspace -- author a battle.toml ENCOUNTER-FIRST.

Open a battle.toml and tune it as an encounter: its ``[battlemap]`` identity, its ``[scene]`` FORMATION, and
each ``[[scene.enemy]]`` slot, edited as forms (the :mod:`ff9mapkit.editor.battle_forms` specs over the shared
``forms_qt`` builder -- the same machinery the field editor uses). ``Check`` runs ``validate_battle`` into the
Problems dock; deploying is the existing **Build & Deploy** battle path (open the same battle.toml there).

Modeled on :class:`~ff9mapkit.workspace.savedoc.ItemEquipDoc`: a self-contained document with a left NODE list
(Map / Formation / one per enemy slot) + a right form, over tk-free backends. A battle.toml is read with
``tomllib`` and written back with :func:`ff9mapkit.editor.model.dumps` (round-trip-safe for the battle schema).
Creating a battle.toml is the ``ff9mapkit battle-import`` CLI's job (like forking a field is the Import tab's);
this document TUNES one.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QSplitter, QVBoxLayout, QWidget,
)

from ..editor import battle_forms as bf
from ..editor import feedback as fb
from ..editor import forms
from ..editor import model as _model
from .forms_qt import build_form, read

_MAP, _SCENE, _ENEMY = "battlemap", "scene", "enemy"

# MonParm attribute -> compact label, for the read-only DONOR BASELINE shown above an enemy form: the forked
# enemy's CURRENT scalar stats, so an override reads against what it's changing FROM. Scalars only (the element
# / status masks need decoding -- a later pass); the keys line up with ENEMY_SPEC so the panel sits next to the
# matching form rows.
_BASELINE_FIELDS = [
    ("hp", "HP"), ("mp", "MP"), ("strength", "Str"), ("magic", "Mag"), ("speed", "Spd"), ("spirit", "Spr"),
    ("level", "Lv"), ("phys_def", "P.def"), ("phys_evade", "P.eva"), ("mag_def", "M.def"),
    ("mag_evade", "M.eva"), ("hit_rate", "Hit"), ("category", "Cat"), ("blue_magic", "Blue"),
    ("gil", "Gil"), ("exp", "EXP"), ("win_card", "Card"),
]


def donor_baseline(raw16: bytes, enemy: dict):
    """``(type_no, [(label, value)...])`` for an enemy slot's TYPE from a forked scene's raw16, or None when the
    type can't be resolved / the bytes don't parse. PURE (no I/O) so it unit-tests without Qt; the document
    wraps it with the file read. The type is the slot's explicit ``type``, else pattern-0's put at that slot."""
    try:
        from ..battle import scene_codec as _sc
        scene = _sc.parse_scene(raw16)
    except Exception:                                       # noqa: BLE001 -- a truncated / non-scene raw16
        return None
    t = enemy.get("type")
    if t is None:
        slot = enemy.get("slot")
        if scene.patterns and isinstance(slot, int) and 0 <= slot < 4:
            t = scene.patterns[0].puts[slot].type_no
    if not isinstance(t, int) or not (0 <= t < len(scene.monsters)):
        return None
    mon = scene.monsters[t]
    return t, [(label, getattr(mon, attr)) for attr, label in _BASELINE_FIELDS]


def donor_scene_facts(raw16: bytes):
    """[(label, value)...] of the forked scene's CURRENT encounter rules (flags decoded to names) + its
    pattern/type/attack counts, for a read-only hint above the Formation form. None if the bytes don't parse.
    Pure (no I/O). The decoded flag names match the `[scene] flags` vocabulary so the user can edit against them."""
    try:
        from ..battle import scene_codec as _sc
        scene = _sc.parse_scene(raw16)
    except Exception:                                       # noqa: BLE001
        return None
    on = [name for name, active in (("back_attack", scene.back_attack), ("preemptive", scene.preemptive),
                                    ("no_escape", not scene.can_escape), ("no_exp", scene.no_exp)) if active]
    return [("Current flags", ", ".join(on) or "(none)"), ("Patterns", scene.pat_count),
            ("Enemy types", scene.typ_count), ("Attacks", scene.atk_count)]


class BattleDoc(QWidget):
    """Author a battle.toml. ``output`` streams text to the bottom Output dock; ``problems`` posts the Check
    verdict + rows to the Problems dock (the same callbacks :class:`BuildDoc` takes)."""

    def __init__(self, palette, *, output=None, problems=None, run=None, kit_root=None):
        super().__init__()
        self.pal = palette
        self._output = output
        self._problems = problems
        self._run = run                  # shell.run_job: streams a CLI job (battle-import) to the Output dock
        self.kit = Path(kit_root) if kit_root else None    # `-m ff9mapkit` cwd (so the local pkg shadows)
        self.path = None                 # Path of the open battle.toml
        self.data = {}                   # the loaded dict (battlemap / scene / scene.enemy[])
        self._nodes = []                 # [(kind, idx)] parallel to the node-list rows
        self._ctx = None                 # {kind, idx, spec, getters} for the mounted form's Save
        self._install_lists = {}         # cache: install-gated BBG / scene lists (read p0data once per session)
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        self.open_btn = QPushButton("Open battle.toml…")
        self.open_btn.clicked.connect(self.browse)
        top.addWidget(self.open_btn)
        self.fork_btn = QPushButton("Fork battle…")
        self.fork_btn.setToolTip("Fork a real FF9 battle background into a new editable battle.toml, then open it")
        self.fork_btn.clicked.connect(self._fork_dialog)
        self.fork_btn.setEnabled(self._run is not None and self.kit is not None)
        top.addWidget(self.fork_btn)
        self.path_lbl = QLabel("No battle map open — Open a battle.toml, or Fork one from a real FF9 "
                               "battle background.")
        self.path_lbl.setStyleSheet(f"color:{self.pal['muted']};")
        top.addWidget(self.path_lbl, 1)
        outer.addLayout(top)

        split = QSplitter()
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.nodes = QListWidget()
        self.nodes.currentRowChanged.connect(self._on_node)
        lv.addWidget(self.nodes, 1)
        self.add_enemy_btn = QPushButton("Add enemy slot")
        self.add_enemy_btn.clicked.connect(self._add_enemy)
        self.add_enemy_btn.setEnabled(False)
        lv.addWidget(self.add_enemy_btn)
        self.add_player_btn = QPushButton("Add party/ability tuning…")
        self.add_player_btn.setToolTip("Tune a PLAYER-side table (stats / abilities / status / leveling) — "
                                       "mod-global, deployed with this battle")
        self.add_player_btn.clicked.connect(self._add_player)
        self.add_player_btn.setEnabled(False)
        lv.addWidget(self.add_player_btn)
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        self.host_scroll = QScrollArea()
        self.host_scroll.setWidgetResizable(True)
        self.host_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.host = QWidget()
        self.host_lay = QVBoxLayout(self.host)
        self.host_scroll.setWidget(self.host)
        rv.addWidget(self.host_scroll, 1)
        btns = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        self.check_btn = QPushButton("Check")
        self.check_btn.clicked.connect(self._check)
        self.check_btn.setEnabled(False)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.check_btn)
        btns.addStretch(1)
        rv.addLayout(btns)
        hint = QLabel("→ deploy on the Build & Deploy tab (open this same battle.toml there).")
        hint.setStyleSheet(f"color:{self.pal['muted']};")
        rv.addWidget(hint)
        split.addWidget(right)
        split.setSizes([200, 520])
        outer.addWidget(split, 1)
        self._placeholder("Open a battle.toml to tune its encounter.")

    def _clear(self):
        while self.host_lay.count():
            it = self.host_lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.deleteLater()

    def _placeholder(self, text):
        self._clear()
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{self.pal['muted']};")
        lbl.setWordWrap(True)
        self.host_lay.addWidget(lbl)
        self.host_lay.addStretch(1)

    # ------------------------------------------------------------------ load
    def browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open a battle.toml", "", "TOML (*.toml)")
        if f:
            self.load(f)

    def load(self, path) -> bool:
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        except Exception as e:                             # noqa: BLE001
            QMessageBox.warning(self, "Couldn't open", f"{Path(path).name}: {e}")
            return False
        if "battlemap" not in data:
            QMessageBox.warning(self, "Not a battle map", f"{Path(path).name} has no [battlemap] table.")
            return False
        self.path = Path(path)
        self.data = data
        bm = data.get("battlemap", {})
        is_mint = bm.get("scene_id") is not None and bool(bm.get("scene_name"))
        mode = (f"minted scene {bm.get('scene_id')} — [scene] tuning applies" if is_mint
                else "MAP-ONLY override — [scene] tuning (stats/camera/flags) needs a Fork scene to apply")
        self.path_lbl.setText(f"{self.path}    ·    {mode}")
        self.path_lbl.setStyleSheet(f"color:{self.pal['muted' if is_mint else 'warn']};")
        self._ctx = None
        self._rebuild_nodes()
        self.add_enemy_btn.setEnabled(True)
        self.add_player_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        if self.nodes.count():
            self.nodes.setCurrentRow(0)
        return True

    def _enemies(self):
        return (self.data.get("scene") or {}).get("enemy", []) or []

    def _add_header(self, text):
        """A non-selectable separator row in the node list (a tree-section header)."""
        item = QListWidgetItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.nodes.addItem(item)
        self._nodes.append((None, None))                   # keep _nodes parallel to the list rows

    def _player_rows(self):
        """[(table_key, index, entry)] for every player/ability tuning entry the battle.toml carries."""
        return [(key, i, e) for key in bf.PLAYER_SPECS for i, e in enumerate(self.data.get(key) or [])]

    def _rebuild_nodes(self):
        self.nodes.blockSignals(True)
        self.nodes.clear()
        self._nodes = []
        self.nodes.addItem("Map  ·  [battlemap]")
        self._nodes.append((_MAP, None))
        self.nodes.addItem("Formation  ·  [scene]")
        self._nodes.append((_SCENE, None))
        for i, e in enumerate(self._enemies()):
            self.nodes.addItem(f"Enemy slot {e.get('slot', i)}")
            self._nodes.append((_ENEMY, i))
        player = self._player_rows()
        if player:                                         # the mod-global PLAYER side, under its own header
            self._add_header("— Party & abilities (mod-global) —")
            for key, i, e in player:
                self.nodes.addItem(f"{bf.PLAYER_LABEL[key]}  ·  {e.get(bf.PLAYER_SELECTOR[key], i)}")
                self._nodes.append((key, i))
        self.nodes.blockSignals(False)

    # ------------------------------------------------------------------ node -> form
    def _on_node(self, row):
        if not (0 <= row < len(self._nodes)):
            return
        self._commit_active()                              # fold any pending edit before switching
        kind, idx = self._nodes[row]
        if kind == _MAP:
            self._mount(_MAP, None, bf.BATTLEMAP_SPEC, self.data.setdefault("battlemap", {}))
        elif kind == _SCENE:
            self._mount(_SCENE, None, bf.SCENE_SPEC, self.data.setdefault("scene", {}))
        elif kind == _ENEMY:
            if 0 <= idx < len(self._enemies()):
                self._mount(_ENEMY, idx, bf.ENEMY_SPEC, self._enemies()[idx])
        elif kind in bf.PLAYER_SPECS:                      # a player/ability tuning row
            lst = self.data.get(kind) or []
            if 0 <= idx < len(lst):
                self._mount(kind, idx, bf.PLAYER_SPECS[kind], lst[idx])
        # kind is None -> a separator header: nothing to mount

    def _mount(self, kind, idx, spec, entity):
        self._clear()
        if kind == _ENEMY:
            base = self._donor_baseline(entity)             # read-only "what you're tuning from" panel
            if base is not None:
                self.host_lay.addWidget(self._baseline_panel(*base))
        elif kind == _SCENE:
            facts = self._donor_scene_facts()               # the donor's current rules + counts
            if facts is not None:
                self.host_lay.addWidget(self._facts_panel("Donor scene (the fork you're tuning)", facts))
        form, getters = build_form(spec, forms.entity_to_values(spec, entity), self.pal)
        self.host_lay.addWidget(form)
        self.host_lay.addStretch(1)
        self._ctx = {"kind": kind, "idx": idx, "spec": spec, "getters": getters}
        self.save_btn.setEnabled(True)

    # ------------------------------------------------------------------ donor baseline (read-only)
    def _donor_scene_path(self):
        """The forked scene's raw16 (the donor enemy stats), or None for an override/repoint battle.toml that
        has no forked ``scene/`` dir. Mirrors ``BattleProject.scene_dir`` = the toml's folder / ``scene``."""
        if not self.path:
            return None
        return self.path.parent / "scene" / "dbfile0000.raw16.bytes"

    def _donor_baseline(self, enemy):
        p = self._donor_scene_path()
        if not p or not p.is_file():
            return None
        try:
            return donor_baseline(p.read_bytes(), enemy)
        except OSError:
            return None

    def _donor_scene_facts(self):
        p = self._donor_scene_path()
        if not p or not p.is_file():
            return None
        try:
            return donor_scene_facts(p.read_bytes())
        except OSError:
            return None

    def _baseline_panel(self, type_no, pairs):
        return self._facts_panel(f"Donor baseline — enemy type {type_no} (the forked stats you're tuning from)", pairs)

    def _facts_panel(self, title, pairs, per_row=6):
        """A read-only grid of (label, value) facts in a titled box (the donor enemy baseline / scene rules)."""
        box = QGroupBox(title)
        grid = QGridLayout(box)
        grid.setContentsMargins(8, 4, 8, 4)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(2)
        for i, (label, val) in enumerate(pairs):
            r, c = divmod(i, per_row)
            cell = QLabel(f"{label} <b>{val}</b>")
            cell.setStyleSheet(f"color:{self.pal['muted']};")
            grid.addWidget(cell, r, c)
        return box

    def _target(self, kind, idx):
        if kind == _MAP:
            return self.data.setdefault("battlemap", {})
        if kind == _SCENE:
            return self.data.setdefault("scene", {})
        if kind == _ENEMY:
            return self._enemies()[idx]
        return self.data[kind][idx]                        # a player/ability tuning table row

    def _fold(self, ctx) -> bool:
        """Apply the form's values to its target dict in place (pop the spec keys, keep any non-spec keys --
        e.g. the [scene] form must not drop the enemy list). Returns False on an invalid value (no change)."""
        try:
            entity = forms.build_entity(ctx["spec"], read(ctx["getters"]))
        except ValueError:
            return False
        tgt = self._target(ctx["kind"], ctx["idx"])
        for f in ctx["spec"]:
            tgt.pop(f.key, None)
        tgt.update(entity)
        return True

    def _commit_active(self) -> bool:
        return self._fold(self._ctx) if self._ctx else True

    # ------------------------------------------------------------------ save / add / check
    def _save(self):
        if not self._ctx:
            return
        if not self._fold(self._ctx):
            self._post(["Invalid value — not saved (fix the highlighted field)."], [], "Save")
            return
        if not self._write():
            return
        self._rebuild_nodes()                              # a slot's number may have changed
        self._post([], [], "Save", clean=f"Saved {self.path.name}")

    def _add_enemy(self):
        if not self.data:
            return
        self._commit_active()
        enemies = self.data.setdefault("scene", {}).setdefault("enemy", [])
        used = {e.get("slot") for e in enemies}
        enemies.append({"slot": next((s for s in range(4) if s not in used), len(enemies))})
        self._rebuild_nodes()
        # land on the new enemy's form (the last ENEMY row, before any player header/rows)
        self._select_node(_ENEMY, len(enemies) - 1)

    def _add_player(self):
        if not self.data:
            return
        self._commit_active()
        key = self._pick_player_table()
        if not key:
            return
        self.data.setdefault(key, []).append(dict(bf.PLAYER_DEFAULT[key]))
        self._rebuild_nodes()
        self._select_node(key, len(self.data[key]) - 1)    # land on the new row's form

    def _select_node(self, kind, idx):
        for r, node in enumerate(self._nodes):
            if node == (kind, idx):
                self.nodes.setCurrentRow(r)
                return

    def _pick_player_table(self):
        """A small dialog to pick which player/ability table to add a row to. Returns its key, or None."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Add party / ability tuning")
        lay = QVBoxLayout(dlg)
        lbl = QLabel("Tune which player-side table? It's mod-GLOBAL — deployed with this battle and applied "
                     "to the whole game.")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        combo = QComboBox()
        for key, label, *_ in bf.PLAYER_TABLES:
            combo.addItem(label, key)
        lay.addWidget(combo)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        return combo.currentData()

    def _write(self) -> bool:
        try:
            self.path.write_text(_model.dumps(self.data), encoding="utf-8", newline="\n")
            return True
        except Exception as e:                             # noqa: BLE001
            self._post([f"Save failed: {e}"], [], "Save")
            return False

    def _check(self):
        if not self.path:
            return
        self._commit_active()
        if not self._write():                              # Check implies persisting the current form first
            return
        errs = []
        try:
            from ..battle.build import BattleProject, validate_battle
            errs = list(validate_battle(BattleProject.load(self.path)))
        except Exception as e:                             # noqa: BLE001
            errs = [f"{type(e).__name__}: {e}"]
        self._post(errs, [], f"Check {self.path.name}", clean=f"{self.path.name} — no problems")

    def _post(self, errs, warns, subject, clean=None):
        """Route a Check/Save result to the Problems dock (verdict + rows), or the Output console if undocked."""
        errs, warns = list(errs), list(warns)
        if self._problems is not None:
            v = fb.classify(errs, warns, subject=subject, clean_headline=clean or f"{subject} — OK")
            self._problems(v, fb.problems(errs, warns))
        elif self._output is not None:
            body = "\n".join(errs + warns)
            self._output(f"{clean or subject}{(chr(10) + body) if body else ''}\n")

    # ------------------------------------------------------------------ fork a real battle background
    def _fork_argv(self, bbg, out, fork_scene=None):
        """The ``ff9mapkit battle-import`` argv that forks a real BBG's geometry into an editable battle.toml."""
        a = [sys.executable, "-m", "ff9mapkit", "battle-import", str(bbg), "--out", str(out)]
        if fork_scene:
            a += ["--fork-scene", str(fork_scene)]
        return a

    def _run_fork(self, bbg, out, fork_scene=None):
        """Shell out battle-import (streams to the Output dock) and AUTO-OPEN the result on success."""
        if not self._run or not self.kit:
            return
        Path(out).mkdir(parents=True, exist_ok=True)
        self._run(self._fork_argv(bbg, out, fork_scene), cwd=self.kit, subject=f"Fork battle {bbg}",
                  ok_headline=f"Forked {bbg} → {out}", ok_next="Opening the new battle.toml…",
                  fail_hint="Forking a battle needs UnityPy + your FF9 install (like forking a field).",
                  on_finished=lambda code: self._after_fork(code, out))

    def _after_fork(self, code, out):
        """battle-import done -> open the battle.toml it wrote (only on a clean exit)."""
        toml = Path(out) / "battle.toml"
        if code == 0 and toml.is_file():
            self.load(str(toml))

    def _pick_out(self, line_edit):
        d = QFileDialog.getExistingDirectory(self, "Folder to write the battle into")
        if d:
            line_edit.setText(d)

    @staticmethod
    def _browse_row(line_edit, on_browse):
        """A line edit + a 'Browse…' button in one row (for the install-gated BBG / scene pickers)."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(line_edit, 1)
        b = QPushButton("Browse…")
        b.clicked.connect(on_browse)
        h.addWidget(b)
        return row

    def _pick_install_list(self, title, loader, target, cache_key):
        """Browse an INSTALL-gated list (BBGs / battle scenes, read from p0data via UnityPy) into ``target``.
        Reads the install on first use (a brief wait), cached per session; a clean warning if the install /
        UnityPy is absent (so a no-install workstation degrades gracefully instead of tracing back)."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        rows = self._install_lists.get(cache_key)
        if rows is None:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                rows = list(loader())
            except Exception as e:                         # noqa: BLE001 -- no install / no UnityPy / read error
                QApplication.restoreOverrideCursor()
                return QMessageBox.warning(self, title, f"Couldn't read {title.lower()} — forking a battle "
                                           f"needs UnityPy + your FF9 install.\n\n{type(e).__name__}: {e}")
            finally:
                QApplication.restoreOverrideCursor()
            self._install_lists[cache_key] = rows
        if not rows:
            return QMessageBox.information(self, title, f"No {title.lower()} found in your install.")
        name = self._choose(title, rows)
        if name:
            target.setText(name)

    def _choose(self, title, rows):
        """A simple searchable single-pick list dialog over ``rows`` (names); the chosen name, or None."""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(360, 460)
        lay = QVBoxLayout(dlg)
        q = QLineEdit()
        q.setPlaceholderText("Filter…")
        lay.addWidget(q)
        lst = QListWidget()
        lst.addItems(rows)
        lay.addWidget(lst, 1)
        q.textChanged.connect(lambda t: (lst.clear(), lst.addItems([r for r in rows if t.lower() in r.lower()])))
        lst.itemDoubleClicked.connect(lambda _i: dlg.accept())
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        it = lst.currentItem()
        return it.text() if it else None

    def _fork_dialog(self):
        if not self._run or not self.kit:
            return
        from ..battle import extract as _ex
        dlg = QDialog(self)
        dlg.setWindowTitle("Fork a battle background")
        form = QFormLayout(dlg)
        bbg = QLineEdit()
        bbg.setPlaceholderText("BBG_B013  (Browse… to pick from your install)")
        form.addRow("Background (BBG)", self._browse_row(
            bbg, lambda: self._pick_install_list("Battle backgrounds", _ex.list_battle_maps, bbg, "bbg")))
        donor = QLineEdit()
        donor.setPlaceholderText("optional — e.g. EF_R007 (mints a brand-new, separately-triggerable scene)")
        form.addRow("Fork scene", self._browse_row(
            donor, lambda: self._pick_install_list("Battle scenes", _ex.list_battle_scenes, donor, "scene")))
        outrow = QWidget()
        oh = QHBoxLayout(outrow)
        oh.setContentsMargins(0, 0, 0, 0)
        out = QLineEdit(str(Path.home() / "ff9field" / "fight"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(lambda: self._pick_out(out))
        oh.addWidget(out, 1)
        oh.addWidget(browse)
        form.addRow("Write to", outrow)
        hint = QLabel("Forks the real BBG's geometry into an editable battle.toml (needs UnityPy + your FF9 "
                      "install). A bare BBG OVERRIDES that real map; add a Fork scene to mint a new one. The "
                      "result opens here when it's done.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{self.pal['muted']};")
        form.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        b, o = bbg.text().strip(), out.text().strip()
        if not b or not o:
            QMessageBox.warning(self, "Fork battle", "Enter a BBG name and an output folder.")
            return
        self._run_fork(b, o, donor.text().strip() or None)
