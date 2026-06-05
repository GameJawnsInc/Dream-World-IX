#!/usr/bin/env pythonw
"""FF9 Map Kit -- tiny build & deploy GUI (no terminal needed).

Double-click this file to launch (it runs windowless via pythonw), or:  py tools\\ff9_build_gui.pyw

Pick a `<name>.field.toml`, choose where to put it, and click Build / Deploy:
  * Test field 4003  -- builds + deploys it to the in-game test slot, reachable via the debug warp
                        (New Game -> walk to the hut door). Reversible with "Revert test field".
  * Game mod folder  -- builds it into the game's FF9CustomMap (install at its real field id).
  * Other folder     -- builds it to any folder you pick.

The build auto-merges a sibling `<name>.scene.toml` (Blender placement) with the field.toml (logic).
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
NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

import tkinter as tk                                   # noqa: E402
from tkinter import ttk, filedialog, messagebox, scrolledtext   # noqa: E402


def detect_game_mod():
    """The game's FF9CustomMap folder, or None if the install can't be found."""
    try:
        from ff9mapkit import config
        return config.find_game_path() / "FF9CustomMap"
    except Exception:
        return None


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.game_mod = detect_game_mod()
        root.title("FF9 Map Kit - Build & Deploy")
        root.minsize(660, 480)
        pad = dict(padx=10, pady=5)

        # --- field file ---
        top = ttk.Frame(root); top.pack(fill="x", **pad)
        ttk.Label(top, text="Field file  (<name>.field.toml):").grid(row=0, column=0, sticky="w")
        self.field = tk.StringVar()
        ttk.Entry(top, textvariable=self.field).grid(row=1, column=0, sticky="we")
        ttk.Button(top, text="Browse...", command=self.browse_field).grid(row=1, column=1, padx=(6, 0))
        top.columnconfigure(0, weight=1)

        # --- target ---
        tgt = ttk.LabelFrame(root, text="Build to"); tgt.pack(fill="x", **pad)
        self.target = tk.StringVar(value="test")
        ttk.Radiobutton(tgt, text="Test field 4003  -  play it now (New Game -> hut door)",
                        value="test", variable=self.target).pack(anchor="w", padx=6, pady=2)
        gtxt = (f"Game mod folder (install):  {self.game_mod}" if self.game_mod
                else "Game mod folder  -  (game install not found)")
        self.rb_game = ttk.Radiobutton(tgt, text=gtxt, value="game", variable=self.target)
        self.rb_game.pack(anchor="w", padx=6, pady=2)
        if not self.game_mod:
            self.rb_game.state(["disabled"])
        of = ttk.Frame(tgt); of.pack(fill="x", padx=6, pady=2)
        ttk.Radiobutton(of, text="Other folder:", value="other",
                        variable=self.target).pack(side="left")
        self.other = tk.StringVar()
        ttk.Entry(of, textvariable=self.other).pack(side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(of, text="Browse...", command=self.browse_other).pack(side="left")

        # --- buttons ---
        btns = ttk.Frame(root); btns.pack(fill="x", **pad)
        self.go = ttk.Button(btns, text="Build / Deploy", command=self.on_go)
        self.go.pack(side="left")
        self.rev = ttk.Button(btns, text="Revert test field", command=self.on_revert)
        self.rev.pack(side="left", padx=8)
        if not REVERT.exists():
            self.rev.state(["disabled"])

        # --- log ---
        self.log = scrolledtext.ScrolledText(root, height=16, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, **pad)
        self._write("Pick a .field.toml, choose where to build it, then Build / Deploy.\n"
                    "Tip: 'Test field 4003' lets you walk it in-game immediately.\n")

        self.q: queue.Queue = queue.Queue()
        root.after(120, self._drain)

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

    # ---- pickers ----
    def browse_field(self):
        f = filedialog.askopenfilename(
            title="Pick a field.toml",
            filetypes=[("Field project", "*.field.toml"), ("TOML", "*.toml"), ("All files", "*.*")])
        if f:
            self.field.set(f)

    def browse_other(self):
        d = filedialog.askdirectory(title="Output folder")
        if d:
            self.other.set(d)
            self.target.set("other")

    # ---- run ----
    def _busy(self, b):
        self.busy = b
        self.go.state(["disabled"] if b else ["!disabled"])

    def _start(self, fn, *args):
        self._busy(True)
        threading.Thread(target=fn, args=args, daemon=True).start()

    def on_go(self):
        if self.busy:
            return
        field = self.field.get().strip()
        if not field or not Path(field).is_file():
            messagebox.showerror("No field", "Pick a .field.toml first.")
            return
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
            self.root.after(0, lambda: self.rev.state(["!disabled"]))
        except Exception:
            self.post("ERROR:\n" + traceback.format_exc())
        finally:
            self.root.after(0, lambda: self._busy(False))

    def on_revert(self):
        if not REVERT.exists():
            messagebox.showinfo("Nothing to revert", "No test-field deploy to undo yet.")
            return
        if not messagebox.askyesno("Revert test field",
                                   "Restore the game to before the last test deploy?"):
            return

        def work():
            try:
                self.post("\n--- revert test field ---")
                r = subprocess.run([sys.executable, str(REVERT)], cwd=str(KIT_ROOT),
                                   capture_output=True, text=True, creationflags=NOWIN)
                self.post(r.stdout or "")
                if r.returncode != 0:
                    self.post("ERROR:\n" + (r.stderr or "(no detail)"))
            except Exception:
                self.post("ERROR:\n" + traceback.format_exc())
        threading.Thread(target=work, daemon=True).start()


def main():
    root = tk.Tk()
    try:
        App(root)
    except Exception:
        messagebox.showerror("FF9 Map Kit", traceback.format_exc())
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
