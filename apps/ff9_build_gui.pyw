#!/usr/bin/env pythonw
"""FF9 Map Kit -- tiny build & deploy GUI (no terminal needed).

Double-click this file to launch (it runs windowless via pythonw), or:  py tools\\ff9_build_gui.pyw

Handles BOTH a single field and a whole campaign -- it auto-detects which you picked:

  * <name>.field.toml  -- ONE field. Build/deploy to:
      Test field 4003  -- the in-game test slot, reachable via the debug warp. Reversible.
      Game mod folder  -- install at its real id in the game's FF9CustomMap.
      Other folder     -- build it anywhere.
    The build auto-merges a sibling <name>.scene.toml (Blender placement) with the field.toml (logic).

  * campaign.toml      -- a CHAIN of forked fields (from `ff9mapkit import-chain`). Build/deploy to:
      Deploy to game   -- reversibly install the whole chain into its own mod folder (reach each
                          screen via F6 -> Warp). Reversible with "Revert campaign".
      Build only       -- compile every member into the campaign's dist/ without touching the game.
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]        # ...\ff9mapkit
sys.path.insert(0, str(KIT_ROOT))
DEPLOY = KIT_ROOT / "tools" / "deploy_field.py"
REVERT = KIT_ROOT / "tools" / "scroll_out" / "revert_deploy.py"
DEPLOY_CAMPAIGN = KIT_ROOT / "tools" / "deploy_campaign.py"
REVERT_CAMPAIGN = KIT_ROOT / "tools" / "scroll_out" / "revert_campaign.py"
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
    """('campaign', plan) if `path` is a campaign manifest, else ('field', None). A campaign.toml has a
    [campaign] table -- load_campaign raises on anything else, so it's the cheap, exact discriminator."""
    try:
        from ff9mapkit.campaign import load_campaign
        return "campaign", load_campaign(path)
    except Exception:
        return "field", None


class App:
    def __init__(self, parent):
        self.root = parent.winfo_toplevel()      # real Tk root (after/dialogs); the UI mounts on `parent`
        self.pal = apply_theme(self.root)        # shared modern palette (styles ttk globally too)
        self.busy = False
        self.kind = "field"                      # "field" | "campaign" -- set from the picked file
        self.plan = None                         # the loaded CampaignPlan when kind == "campaign"
        self.game_mod = detect_game_mod()
        pad = dict(padx=10, pady=5)

        # --- project file (a .field.toml OR a campaign.toml) ---
        top = ttk.Frame(parent); top.pack(fill="x", **pad)
        ttk.Label(top, text="Project file  (<name>.field.toml  or  campaign.toml):").grid(
            row=0, column=0, sticky="w")
        self.field = tk.StringVar()
        ttk.Entry(top, textvariable=self.field).grid(row=1, column=0, sticky="we")
        ttk.Button(top, text="Browse...", command=self.browse_field).grid(row=1, column=1, padx=(6, 0))
        top.columnconfigure(0, weight=1)
        self.field.trace_add("write", lambda *_: self._on_field_change())

        # --- detected kind banner ---
        self.status = ttk.Label(parent, text="Pick a field or campaign file.", foreground=self.pal["muted"])
        self.status.pack(fill="x", padx=10)

        # --- targets: a FIELD frame and a CAMPAIGN frame; only the matching one is shown ---
        self.tgt_holder = ttk.Frame(parent); self.tgt_holder.pack(fill="x", **pad)

        self.field_tgt = ttk.LabelFrame(self.tgt_holder, text="Build to (field)")
        self.target = tk.StringVar(value="test")
        ttk.Radiobutton(self.field_tgt, text="Test field 4003  -  play it now (New Game -> hut door)",
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
        self._write("Pick a .field.toml (one field) or a campaign.toml (a chain), choose a target, "
                    "then Build / Deploy.\n")

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
        """Re-detect field-vs-campaign whenever the path points at a real file, and re-skin the UI."""
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
        if self.kind == "campaign" and self.plan is not None:
            self.camp_tgt.pack(fill="x")
            self.rb_camp_deploy.config(text=f"Deploy to game (reversible)  ->  {self.plan.mod_folder}")
            ids = [m.new_id for m in self.plan.members]
            rng = f"{min(ids)}-{max(ids)}" if ids else "?"
            self.status.config(text=f"Campaign '{self.plan.name}':  {len(self.plan.members)} fields "
                                    f"(ids {rng})  ->  {self.plan.mod_folder}")
            self.go.config(text="Build / Deploy campaign")
            self.rev.config(text="Revert campaign")
        else:
            self.field_tgt.pack(fill="x")
            path = self.field.get().strip()
            self.status.config(text=(f"Field project: {Path(path).name}" if path
                                     else "Pick a field or campaign file."))
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
            title="Pick a field.toml or campaign.toml",
            filetypes=[("Field or campaign", "*.toml"), ("Field project", "*.field.toml"),
                       ("Campaign manifest", "campaign.toml"), ("All files", "*.*")],
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
            messagebox.showerror("No file", "Pick a .field.toml or campaign.toml first.")
            return None
        return f

    def on_check(self):
        if self.busy:
            return
        f = self._picked_file()
        if f:
            self._start(self._check_campaign if self.kind == "campaign" else self._check, f)

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

    def on_go(self):
        if self.busy:
            return
        f = self._picked_file()
        if not f:
            return
        if self.kind == "campaign":
            self._go_campaign(f)
        else:
            self._go_field(f)

    def _go_field(self, field):
        tgt = self.target.get()
        if tgt == "test":
            if messagebox.askyesno(
                    "Deploy to test field 4003",
                    "Build and deploy this field to the in-game test slot (4003)?\n\n"
                    "It replaces whatever test field is there now and becomes reachable via the debug "
                    "warp (New Game -> walk to the hut door). This is reversible."):
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
        try:
            self.post(f"\n--- deploy {Path(field).name}  ->  test field 4003 ---")
            r = subprocess.run([sys.executable, str(DEPLOY), field], cwd=str(KIT_ROOT),
                               capture_output=True, text=True, creationflags=NOWIN)
            if r.stdout:
                self.post(r.stdout)
            if r.returncode != 0:
                self.post("ERROR (deploy failed):\n" + (r.stderr or "(no detail)"))
                return
            self.post(">>> In-game: New Game -> walk to the hut door -> your field.")
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

    def on_revert(self):
        script = REVERT_CAMPAIGN if self.kind == "campaign" else REVERT
        what = "campaign" if self.kind == "campaign" else "test field"
        if not script.exists():
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
    root = tk.Tk()
    root.title("FF9 Map Kit - Build & Deploy")
    root.minsize(660, 500)
    try:
        App(root)
    except Exception:
        messagebox.showerror("FF9 Map Kit", traceback.format_exc())
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
