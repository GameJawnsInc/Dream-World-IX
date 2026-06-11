#!/usr/bin/env pythonw
"""FF9 Map Kit -- tiny build & deploy GUI (no terminal needed).

Double-click this file to launch (it runs windowless via pythonw), or:  py apps\\ff9_build_gui.pyw

Auto-detects what you picked -- a single field, a whole campaign, OR a battle map:

  * <name>.field.toml  -- ONE field. Build/deploy to:
      Test field  -- this worktree's pinned scratch slot (from .ff9deploy.toml; e.g. 30004), reachable
                      via F6 -> Warp. Reversible.
      Game mod folder  -- install at its real id in the game's FF9CustomMap.
      Other folder     -- build it anywhere.
    The build auto-merges a sibling <name>.scene.toml (Blender placement) with the field.toml (logic).

  * campaign.toml      -- a CHAIN of forked fields (from `ff9mapkit import-chain`). Build/deploy to:
      Deploy to game   -- reversibly install the whole chain into its own mod folder (reach each
                          screen via F6 -> Warp). Reversible with "Revert campaign".
      Build only       -- compile every member into the campaign's dist/ without touching the game.

  * battle.toml        -- a custom battle background / minted scene. Build/deploy reversibly into this
                          worktree's mod folder (from `.ff9deploy.toml`). A texture/FBX override needs
                          no relaunch; a minted BattleScene needs one. Optional "trigger field"
                          repoints a deployed field's encounter at the minted scene so you can fight
                          it immediately. Reversible with "Revert battle".
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tomllib
import traceback
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]        # repo root (holds tools/, apps/, .ff9deploy.toml)
sys.path.insert(0, str(KIT_ROOT))
DEPLOY = KIT_ROOT / "tools" / "deploy_field.py"
DEPLOY_CAMPAIGN = KIT_ROOT / "tools" / "deploy_campaign.py"
DEPLOY_BATTLE = KIT_ROOT / "tools" / "deploy_battle.py"
SCROLL_OUT = KIT_ROOT / "tools" / "scroll_out"
REVERT = SCROLL_OUT / "revert_deploy.py"
REVERT_CAMPAIGN = SCROLL_OUT / "revert_campaign.py"
NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

import tkinter as tk                                   # noqa: E402
from tkinter import ttk, filedialog, messagebox, scrolledtext   # noqa: E402
from ff9mapkit.editor.theme import apply_theme         # noqa: E402  (shared modern theme/palette)


def detect_game_mod():
    """The game's FF9CustomMap folder, or None if the install can't be found."""
    try:
        from ff9mapkit import config
        return config.find_game_path() / "FF9CustomMap"
    except Exception:
        return None


def detect_kind(path):
    """('campaign', plan) | ('battle', None) | ('field', None) for the picked file. A campaign.toml has a
    [campaign] table (load_campaign raises on anything else); a battle.toml has a [battlemap] table; else
    it's treated as a field.toml -- the cheap, exact discriminators."""
    try:
        from ff9mapkit.campaign import load_campaign
        return "campaign", load_campaign(path)
    except Exception:
        pass
    try:
        with open(path, "rb") as fh:
            if "battlemap" in tomllib.load(fh):
                return "battle", None
    except Exception:
        pass
    return "field", None


def detect_deploy_target():
    """(mod_folder, field_id) from this worktree's .ff9deploy.toml, or sane defaults. This is where
    `deploy_battle.py` (and the field test deploy) write."""
    mod, fid = "FF9CustomMap", None
    f = KIT_ROOT / ".ff9deploy.toml"
    if f.is_file():
        try:
            d = tomllib.loads(f.read_text(encoding="utf-8"))
            mod = d.get("mod_folder", mod) or mod
            fid = d.get("id")
        except Exception:
            pass
    return mod, fid


def latest_battle_revert():
    """The most recently written tools/scroll_out/revert_battle_*.py, or None."""
    scripts = sorted(SCROLL_OUT.glob("revert_battle_*.py"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    return scripts[0] if scripts else None


def detect_deployed_fields(mod_folder):
    """[(id, name), ...] of the FieldScene lines currently in the worktree mod folder's DictionaryPatch.
    These are the fields whose encounter a battle-mint can repoint (the valid 'trigger field' choices)."""
    out = []
    try:
        from ff9mapkit import config
        dp = config.find_game_path() / mod_folder / "DictionaryPatch.txt"
        if dp.is_file():
            for ln in dp.read_text(encoding="utf-8").splitlines():
                p = ln.split()
                if p[:1] == ["FieldScene"] and len(p) >= 5:
                    out.append((p[1], p[4]))
    except Exception:
        pass
    return out


class App:
    def __init__(self, parent):
        self.root = parent.winfo_toplevel()      # real Tk root (after/dialogs); the UI mounts on `parent`
        self.pal = apply_theme(self.root)        # shared modern palette (styles ttk globally too)
        self.busy = False
        self.kind = "field"                      # "field" | "campaign" | "battle" -- set from the picked file
        self.plan = None                         # the loaded CampaignPlan when kind == "campaign"
        self.game_mod = detect_game_mod()
        self.mod_folder, self.worktree_id = detect_deploy_target()
        pad = dict(padx=10, pady=5)

        # --- project file (a .field.toml, campaign.toml, or battle.toml) ---
        top = ttk.Frame(parent); top.pack(fill="x", **pad)
        ttk.Label(top, text="Project file  (<name>.field.toml,  campaign.toml,  or  battle.toml):").grid(
            row=0, column=0, sticky="w")
        self.field = tk.StringVar()
        ttk.Entry(top, textvariable=self.field).grid(row=1, column=0, sticky="we")
        ttk.Button(top, text="Browse...", command=self.browse_field).grid(row=1, column=1, padx=(6, 0))
        top.columnconfigure(0, weight=1)
        self.field.trace_add("write", lambda *_: self._on_field_change())

        # --- detected kind banner ---
        self.status = ttk.Label(parent, text="Pick a field, campaign, or battle file.",
                                foreground=self.pal["muted"])
        self.status.pack(fill="x", padx=10)

        # --- targets: a FIELD frame, a CAMPAIGN frame, and a BATTLE frame; only the matching one shows ---
        self.tgt_holder = ttk.Frame(parent); self.tgt_holder.pack(fill="x", **pad)

        self.field_tgt = ttk.LabelFrame(self.tgt_holder, text="Build to (field)")
        self.target = tk.StringVar(value="test")
        _tid = self.worktree_id or 4003                  # this worktree's pinned slot (.ff9deploy.toml), not 4003
        _test_lbl = (f"Test field {_tid}  -  reach via F6 -> Warp to {_tid}"
                     + ("  (or New Game -> hut door)" if _tid == 4003 else ""))
        ttk.Radiobutton(self.field_tgt, text=_test_lbl,
                        value="test", variable=self.target).pack(anchor="w", padx=6, pady=2)
        gtxt = (f"Game mod folder (install):  {self.game_mod}" if self.game_mod
                else "Game mod folder  -  (game install not found)")
        self.rb_game = ttk.Radiobutton(self.field_tgt, text=gtxt, value="game", variable=self.target)
        self.rb_game.pack(anchor="w", padx=6, pady=2)
        if not self.game_mod:
            self.rb_game.state(["disabled"])
        of = ttk.Frame(self.field_tgt); of.pack(fill="x", padx=6, pady=2)
        ttk.Radiobutton(of, text="Other folder:", value="other",
                        variable=self.target).pack(side="left")
        self.other = tk.StringVar()
        ttk.Entry(of, textvariable=self.other).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(of, text="Browse...", command=self.browse_other).pack(side="left")

        self.camp_tgt = ttk.LabelFrame(self.tgt_holder, text="Deploy campaign")
        self.camp_action = tk.StringVar(value="deploy")
        self.rb_camp_deploy = ttk.Radiobutton(
            self.camp_tgt, text="Deploy to game (reversible)", value="deploy", variable=self.camp_action)
        self.rb_camp_deploy.pack(anchor="w", padx=6, pady=2)
        ttk.Radiobutton(self.camp_tgt, text="Build only  -  compile every member to the campaign's dist/",
                        value="build", variable=self.camp_action).pack(anchor="w", padx=6, pady=2)
        self.wire_newgame = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.camp_tgt, variable=self.wire_newgame,
                        text="Wire New Game entry (experimental -- needs a non-crashing entry field; "
                             "off = reach the chain via F6 -> Warp)").pack(anchor="w", padx=24, pady=(0, 4))

        self.battle_tgt = ttk.LabelFrame(self.tgt_holder, text="Deploy battle map")
        ttk.Label(self.battle_tgt, text=f"This worktree's mod folder:  {self.mod_folder}").pack(
            anchor="w", padx=6, pady=(4, 0))
        ttk.Label(self.battle_tgt, foreground=self.pal["muted"], wraplength=560, justify="left",
                  text="A texture/FBX override is read at battle start (no relaunch). A minted "
                       "BattleScene or a BattlePatch line loads at launch -> relaunch once.").pack(
            anchor="w", padx=6, pady=(0, 4))
        bf = ttk.Frame(self.battle_tgt); bf.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(bf, text="Trigger field (optional):").pack(side="left")
        self.trigger = tk.StringVar()
        ttk.Entry(bf, textvariable=self.trigger, width=10).pack(side="left", padx=(6, 6))
        self.trigger_hint = ttk.Label(bf, foreground=self.pal["muted"], wraplength=420, justify="left")
        self.trigger_hint.pack(side="left")

        # --- buttons ---
        btns = ttk.Frame(parent); btns.pack(fill="x", **pad)
        self.chk = ttk.Button(btns, text="Check logic", command=self.on_check)
        self.chk.pack(side="left", padx=(0, 8))
        self.go = ttk.Button(btns, text="Build / Deploy", command=self.on_go)
        self.go.pack(side="left")
        self.rev = ttk.Button(btns, text="Revert test field", command=self.on_revert)
        self.rev.pack(side="left", padx=8)

        # --- log ---
        self.log = scrolledtext.ScrolledText(parent, height=16, state="disabled", wrap="word",
                                             borderwidth=0, bg=self.pal["log_bg"], fg=self.pal["log_fg"])
        self.log.pack(fill="both", expand=True, **pad)
        self._write("Pick a .field.toml (one field), a campaign.toml (a chain), or a battle.toml "
                    "(a battle map), choose a target, then Build / Deploy.\n")

        self.q: queue.Queue = queue.Queue()
        self.root.after(120, self._drain)
        self._render_targets()                   # show the field frame + set button labels for the default

    # ---- logging (post() is thread-safe; drained on the UI thread) ----
    def _write(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", str(msg).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def post(self, msg):
        self.q.put(msg)

    def _drain(self):
        try:
            while True:
                self._write(self.q.get_nowait())
        except queue.Empty:
            pass
        self.root.after(120, self._drain)

    # ---- kind detection + target swap ----
    def _on_field_change(self):
        """Re-detect field-vs-campaign-vs-battle whenever the path points at a real file, and re-skin."""
        path = self.field.get().strip().strip('"')
        kind, plan = ("field", None)
        if path and Path(path).is_file():
            kind, plan = detect_kind(path)
        if kind != self.kind or plan is not self.plan:
            self.kind, self.plan = kind, plan
            self._render_targets()

    def _render_targets(self):
        """Show the target frame for the current kind, relabel the action/revert buttons, and update the
        banner. Called on kind change (and once at startup)."""
        self.field_tgt.pack_forget()
        self.camp_tgt.pack_forget()
        self.battle_tgt.pack_forget()
        if self.kind == "campaign" and self.plan is not None:
            self.camp_tgt.pack(fill="x")
            self.rb_camp_deploy.config(text=f"Deploy to game (reversible)  ->  {self.plan.mod_folder}")
            ids = [m.new_id for m in self.plan.members]
            rng = f"{min(ids)}-{max(ids)}" if ids else "?"
            self.status.config(text=f"Campaign '{self.plan.name}':  {len(self.plan.members)} fields "
                                    f"(ids {rng})  ->  {self.plan.mod_folder}")
            self.chk.config(text="Check logic")
            self.go.config(text="Build / Deploy campaign")
            self.rev.config(text="Revert campaign")
        elif self.kind == "battle":
            self.battle_tgt.pack(fill="x")
            deployed = detect_deployed_fields(self.mod_folder)
            if deployed:
                avail = "deployed fields: " + ", ".join(f"{i} ({n})" for i, n in deployed) + " -- "
            else:
                avail = "no fields deployed here yet -- "
            self.trigger_hint.config(
                text=f"{avail}repoint a deployed field's encounter at the minted scene so you can "
                     "fight it now (mint only; leave blank otherwise).")
            path = self.field.get().strip()
            self.status.config(text=f"Battle map: {Path(path).name}  ->  {self.mod_folder}")
            self.chk.config(text="Check battle")
            self.go.config(text="Build / Deploy battle")
            self.rev.config(text="Revert battle")
        else:
            self.field_tgt.pack(fill="x")
            path = self.field.get().strip()
            self.status.config(text=(f"Field project: {Path(path).name}" if path
                                     else "Pick a field, campaign, or battle file."))
            self.chk.config(text="Check logic")
            self.go.config(text="Build / Deploy")
            self.rev.config(text="Revert test field")

    # ---- pickers ----
    @staticmethod
    def _initial(text):
        """(initialdir, initialfile) for a dialog from whatever is typed -- a file, a folder, or a
        partial/not-yet-existing path (falls back to the nearest existing ancestor folder)."""
        text = (text or "").strip().strip('"')
        if not text:
            return (None, None)
        p = Path(text)
        if p.is_dir():
            return (str(p), None)
        if p.is_file():
            return (str(p.parent), p.name)
        parent = p.parent                                  # nonexistent: climb to an existing folder
        while parent != parent.parent and not parent.is_dir():
            parent = parent.parent
        return (str(parent) if parent.is_dir() else None, p.name or None)

    def browse_field(self):
        idir, ifile = self._initial(self.field.get())
        kw = {}
        if idir:
            kw["initialdir"] = idir
        if ifile:
            kw["initialfile"] = ifile
        f = filedialog.askopenfilename(
            title="Pick a field.toml, campaign.toml, or battle.toml",
            filetypes=[("Field / campaign / battle", "*.toml"), ("Field project", "*.field.toml"),
                       ("Campaign manifest", "campaign.toml"), ("Battle map", "battle.toml"),
                       ("All files", "*.*")],
            **kw)
        if f:
            self.field.set(f)

    def browse_other(self):
        idir, _ = self._initial(self.other.get() or self.field.get())   # fall back to the field's folder
        kw = {"initialdir": idir} if idir else {}
        d = filedialog.askdirectory(title="Output folder", **kw)
        if d:
            self.other.set(d)
            self.target.set("other")

    # ---- run ----
    def _busy(self, b):
        self.busy = b
        st = ["disabled"] if b else ["!disabled"]
        self.go.state(st)
        self.chk.state(st)

    def _start(self, fn, *args):
        self._busy(True)
        threading.Thread(target=fn, args=args, daemon=True).start()

    def _picked_file(self):
        """The picked path if it's a real file, else None (with an error popup)."""
        f = self.field.get().strip().strip('"')
        if not f or not Path(f).is_file():
            messagebox.showerror("No file", "Pick a .field.toml, campaign.toml, or battle.toml first.")
            return None
        return f

    def on_check(self):
        if self.busy:
            return
        f = self._picked_file()
        if not f:
            return
        fn = {"campaign": self._check_campaign, "battle": self._battle_check}.get(self.kind, self._check)
        self._start(fn, f)

    def _check(self, field):
        try:
            from ff9mapkit.build import FieldProject, lint_logic, validate
            self.post(f"\n--- check {Path(field).name} (no build) ---")
            p = FieldProject.load(field)
            probs, lints = validate(p), lint_logic(p)
            for m in probs:
                self.post("  ERROR  " + m)
            for m in lints:
                self.post("  warn   " + m)
            self.post("  OK -- no problems." if not (probs or lints)
                      else f"  {len(probs)} error(s), {len(lints)} warning(s)")
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def _check_campaign(self, path):
        try:
            from ff9mapkit.campaign import load_campaign, lint_campaign
            self.post(f"\n--- lint campaign {Path(path).name} (no build) ---")
            plan = load_campaign(path)
            errs, warns = lint_campaign(plan, Path(path).parent)
            for m in errs:
                self.post("  ERROR  " + m)
            for m in warns:
                self.post("  warn   " + m)
            self.post("  OK -- no problems." if not (errs or warns)
                      else f"  {len(errs)} error(s), {len(warns)} warning(s)")
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def _battle_check(self, battle):
        try:
            from ff9mapkit.battle.build import BattleProject, validate_battle
            self.post(f"\n--- check {Path(battle).name} (battle, no deploy) ---")
            p = BattleProject.load(battle)
            probs = validate_battle(p)
            if p.is_mint:
                kind = f"MINT new BattleScene {p.scene_id} ({p.scene_name}) on {p.bbg}"
            elif p.bm.get("repoint_scene") is not None:
                kind = f"repoint scene {p.bm['repoint_scene']} -> {p.bbg}"
            else:
                kind = f"override slot {p.bbg} (texture/FBX, no relaunch)"
            self.post("  " + kind)
            for m in probs:
                self.post("  ERROR  " + m)
            self.post("  OK -- no problems." if not probs else f"  {len(probs)} problem(s)")
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def on_go(self):
        if self.busy:
            return
        f = self._picked_file()
        if not f:
            return
        if self.kind == "campaign":
            self._go_campaign(f)
        elif self.kind == "battle":
            self._go_battle(f)
        else:
            self._go_field(f)

    def _go_field(self, field):
        tgt = self.target.get()
        if tgt == "test":
            tid = self.worktree_id or 4003
            reach = ("New Game -> walk to the hut door (or F6 -> Warp)" if tid == 4003
                     else f"F6 -> Warp to field {tid}")
            if messagebox.askyesno(
                    f"Deploy to test field {tid}",
                    f"Build and deploy this field to this worktree's test slot {tid}  ({self.mod_folder})?\n\n"
                    f"It replaces whatever test field is there now and becomes reachable via {reach}. "
                    "This is reversible."):
                self._start(self._deploy_test, field)
        elif tgt == "game":
            if messagebox.askyesno(
                    "Install to game",
                    f"Build this field into the game mod folder?\n\n{self.game_mod}\n\n"
                    "Writes the field at its real id (may overwrite a field with the same id)."):
                self._start(self._build, field, str(self.game_mod))
        else:
            out = self.other.get().strip()
            if not out:
                messagebox.showerror("No folder", "Pick an output folder.")
                return
            self._start(self._build, field, out)

    def _go_campaign(self, path):
        if self.camp_action.get() == "build":
            self._start(self._build_campaign, path)
            return
        wire = self.wire_newgame.get()
        route = ("It also wires New Game to enter the chain (experimental)."
                 if wire else "Reach each screen in-game via F6 -> Warp.")
        if messagebox.askyesno(
                "Deploy campaign",
                f"Reversibly install campaign '{self.plan.name}' "
                f"({len(self.plan.members)} fields) into:\n\n{self.plan.mod_folder}\n\n"
                f"{route}\n\nThe previous contents are snapshotted first (revert with 'Revert campaign')."):
            self._start(self._deploy_campaign, path, wire)

    def _go_battle(self, battle):
        trig = self.trigger.get().strip()
        if trig and not trig.isdigit():
            messagebox.showerror("Bad trigger field", "Trigger field must be a field id number (or blank).")
            return
        tmsg = (f"\n\nAlso repoint field {trig}'s encounter at the minted scene." if trig else "")
        if messagebox.askyesno(
                "Deploy battle map",
                f"Build and deploy this battle map into:\n\n{self.mod_folder}\n\n"
                "It replaces any prior deploy of the same map (reversible). A minted scene or a "
                "BattlePatch line needs one relaunch." + tmsg):
            self._start(self._deploy_battle, battle, trig)

    def _build(self, field, out):
        try:
            from ff9mapkit.build import FieldProject, build_mod, validate
            self.post(f"\n--- building {Path(field).name}  ->  {out} ---")
            p = FieldProject.load(field)
            probs = validate(p)
            if probs:
                self.post("INVALID -- fix these:\n  - " + "\n  - ".join(probs))
                return
            info = build_mod([p], out, mod_name="FF9CustomMap")
            self.post("OK:  " + info["dictionary"][0])
            for w in info["warnings"]:
                self.post("  warning: " + w)
            self.post(f"done -> {out}")
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def _build_campaign(self, path):
        try:
            from ff9mapkit import campaign as C
            self.post(f"\n--- building campaign {Path(path).name} ---")
            info = C.build_campaign(path)
            for line in info.get("dictionary", []):
                self.post("  " + line)
            for w in info.get("warnings", []):
                self.post("  warning: " + w)
            self.post(f"done -> {info.get('out')}")
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def _deploy_test(self, field):
        tid = self.worktree_id or 4003
        try:
            self.post(f"\n--- deploy {Path(field).name}  ->  test field {tid}  ({self.mod_folder}) ---")
            r = subprocess.run([sys.executable, str(DEPLOY), field], cwd=str(KIT_ROOT),
                               capture_output=True, text=True, creationflags=NOWIN)
            if r.stdout:
                self.post(r.stdout)
            if r.returncode != 0:
                self.post("ERROR (deploy failed):\n" + (r.stderr or "(no detail)"))
                return
            if tid == 4003:
                self.post(">>> In-game: New Game -> walk to the hut door, or F6 -> Warp to field 4003.")
            else:
                self.post(f">>> In-game: F6 -> Warp to field -> {tid}.  "
                          "(First deploy of a NEW id? Relaunch the game once to register it.)")
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def _deploy_campaign(self, path, wire_newgame):
        try:
            self.post(f"\n--- deploy campaign {Path(path).name}  ->  {self.plan.mod_folder} ---")
            cmd = [sys.executable, str(DEPLOY_CAMPAIGN), path, "--apply"]
            if not wire_newgame:
                cmd.append("--no-warp")
            r = subprocess.run(cmd, cwd=str(KIT_ROOT), capture_output=True, text=True, creationflags=NOWIN)
            if r.stdout:
                self.post(r.stdout)
            if r.returncode != 0:
                self.post("ERROR (deploy failed):\n" + (r.stderr or "(no detail)"))
                return
            ids = [m.new_id for m in self.plan.members]
            entry = self.plan.members[0].new_id if self.plan.members else (min(ids) if ids else "?")
            self.post(f">>> Relaunch once (new DictionaryPatch), then F6 -> Warp -> {entry} to walk the chain.")
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def _deploy_battle(self, battle, trig):
        try:
            tf = f"  (trigger field {trig})" if trig else ""
            self.post(f"\n--- deploy {Path(battle).name}  ->  {self.mod_folder}{tf} ---")
            cmd = [sys.executable, str(DEPLOY_BATTLE), battle]
            if trig:
                cmd += ["--trigger-field", trig]
            r = subprocess.run(cmd, cwd=str(KIT_ROOT), capture_output=True, text=True,
                               creationflags=NOWIN)
            if r.stdout:
                self.post(r.stdout)
            if r.returncode != 0:
                self.post("ERROR (deploy failed):\n" + (r.stderr or "(no detail)"))
                return
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def on_revert(self):
        if self.kind == "battle":
            script, what = latest_battle_revert(), "battle"
        elif self.kind == "campaign":
            script, what = REVERT_CAMPAIGN, "campaign"
        else:
            script, what = REVERT, "test field"
        if script is None or not Path(script).exists():
            messagebox.showinfo("Nothing to revert", f"No {what} deploy to undo yet.")
            return
        if not messagebox.askyesno(f"Revert {what}",
                                   f"Restore the game to before the last {what} deploy?"):
            return

        def work():
            try:
                self.post(f"\n--- revert {what} ---")
                r = subprocess.run([sys.executable, str(script)], cwd=str(KIT_ROOT),
                                   capture_output=True, text=True, creationflags=NOWIN)
                self.post(r.stdout or "")
                if r.returncode != 0:
                    self.post("ERROR:\n" + (r.stderr or "(no detail)"))
            except Exception:
                self.post("ERROR:\n" + traceback.format_exc())
        threading.Thread(target=work, daemon=True).start()


def main():
    smoke = "--smoke" in sys.argv
    root = tk.Tk()
    root.title("FF9 Map Kit - Build & Deploy")
    root.minsize(660, 500)
    if smoke:
        root.withdraw()
    try:
        app = App(root)
    except Exception:
        if not smoke:
            messagebox.showerror("FF9 Map Kit", traceback.format_exc())
        raise
    if smoke:
        ok = all(hasattr(app, a) for a in ("field", "trigger", "go", "chk", "rev", "kind", "battle_tgt"))
        print(f"build gui smoke ok: field/campaign/battle picker built; mod folder = {app.mod_folder}; "
              f"all controls present: {ok}")
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
