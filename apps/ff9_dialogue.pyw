#!/usr/bin/env pythonw
"""FF9 Map Kit -- Dialogue editor + stock-dialogue viewer.

Double-click to launch (windowless via pythonw), or:  py apps\\ff9_dialogue.pyw [field.toml]

A focused surface for the WORDS of a field. The Logic Editor owns structure + placement (who stands
where, which option gives what); this owns the text: every NPC line, event message, choice prompt + reply,
and cutscene narration in ONE list, each with a LIVE preview of how it wraps on the FF9 screen (so simple
dialogue stays well-formatted -- FF9 never auto-wraps). It edits the same ``<field>.field.toml`` the Logic
Editor does (round-trips through the kit's serializer) and never touches a Blender ``scene.toml``.

It is also a VIEWER: "Import from game" reads a real FF9 field's ``.eb`` + ``.mes`` (or a built mod
folder's, no install needed) and shows "NPC -> text" -- the kit's own shipped hut joins to
"I miss you Zidane" with zero install. All the data logic lives in the tk-free :mod:`ff9mapkit.dialogue`
spine; this is the thin Tk wiring over it.
"""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]                 # repo root (apps/ is a direct child)
sys.path.insert(0, str(ROOT / "ff9mapkit"))                # the kit package

import tkinter as tk                                        # noqa: E402
from tkinter import filedialog, messagebox, ttk            # noqa: E402

from ff9mapkit import dialogue as DLG                       # noqa: E402  (the read/edit spine)
from ff9mapkit.content import text as _text                 # noqa: E402  (tail codes, wrap default)
from ff9mapkit.editor import picker                         # noqa: E402  (catalog Browse, reused)
from ff9mapkit.editor.model import FieldDoc, protected_reason  # noqa: E402
from ff9mapkit.editor.theme import apply_theme              # noqa: E402

SECTION_TAGS = {"npc": "NPC", "event": "Event", "choice": "Choice", "reply": "Reply", "cutscene": "Cutscene"}


class DialogueApp:
    """The dialogue editor, mounted on a parent (a window OR a notebook tab) -- the App-on-parent contract
    the kit's other GUIs use, so it runs standalone and as a Campaign-Editor tab."""

    def __init__(self, parent, path=None):
        self.container = parent
        self.root = parent.winfo_toplevel()
        self.palette = apply_theme(self.root)
        self.doc = None                          # FieldDoc | None
        self.refs = []                           # dialogue.TextRef list for the open doc
        self.active = None                       # {"idx", widgets...} for the row being edited
        self.campaign_plan = None                # optional CampaignPlan (set by the workspace) -> flag picker

        self._build_toolbar()
        ttk.Separator(self.container, orient="horizontal").pack(fill="x")
        panes = ttk.PanedWindow(self.container, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8, pady=8)
        left = ttk.Frame(panes)
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        panes.add(left, weight=1)
        self.form = ttk.Frame(panes)
        panes.add(self.form, weight=3)

        self.status = ttk.Label(self.container, text="", anchor="w", padding=(10, 4))
        self.status.pack(fill="x")
        if path:
            self.open_path(Path(path))
        else:
            self._welcome()

    # ----------------------------------------------------------------- toolbar
    def _build_toolbar(self):
        bar = ttk.Frame(self.container)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(bar, text="Open", command=self.on_open).pack(side="left")
        ttk.Button(bar, text="Save", command=self.on_save, style="Accent.TButton").pack(side="left", padx=(6, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="Import from game...", command=self.on_import).pack(side="left")
        ttk.Button(bar, text="Help", command=self.on_help).pack(side="right")
        self.title_lbl = ttk.Label(bar, text="(no file)")
        self.title_lbl.pack(side="right", padx=(0, 10))

    def on_help(self):
        messagebox.showinfo(
            "FF9 Map Kit - Dialogue",
            "WHAT THIS IS\n"
            "Every line of text in a field, in one place: NPC dialogue, event messages, choice prompts + "
            "replies, and cutscene narration. The box on the right shows the line; the preview under it "
            "shows how it WRAPS on the FF9 screen (FF9 never auto-wraps, so the kit pre-breaks long lines).\n\n"
            "EDIT\n"
            "Pick a line on the left, type, watch the preview. Speaker + window tail (the little pointer) "
            "edit alongside. Save writes the .field.toml (same file the Logic Editor uses).\n\n"
            "VIEW STOCK DIALOGUE / IMPORT\n"
            "Import from game reads a real FF9 field's text and shows 'NPC -> line' -- a way to view the "
            "original game's writing, or lift it into your own room. No install? Point it at a built mod "
            "folder instead.\n\n"
            "WHERE PLACEMENT LIVES\n"
            "Who stands where, which option gives an item, story flags -- that's the Logic Editor. This "
            "owns the words.")

    def _set_status(self, msg):
        self.status.configure(text=msg)

    # ----------------------------------------------------------------- file io
    def on_open(self):
        f = filedialog.askopenfilename(title="Open field.toml",
                                       filetypes=[("Field project", "*.field.toml"),
                                                  ("TOML", "*.toml"), ("All files", "*.*")])
        if f:
            self.open_path(Path(f))

    def open_path(self, path) -> bool:
        """Load a field.toml -- the single load entry point (the toolbar Open and a host workspace both
        route here). Commits any pending edit first. Returns True on success."""
        self._commit_active()
        try:
            self.doc = FieldDoc.load(Path(path))
        except Exception as e:                   # noqa: BLE001
            messagebox.showerror("Open failed", f"{path}\n\n{e}")
            return False
        split = " (+ scene.toml)" if self.doc.scene_data is not None else ""
        self.title_lbl.configure(text=Path(path).name + split)
        self._refresh_tree()
        self._set_status(f"opened {Path(path).name} -- {len(self.refs)} dialogue line(s)")
        return True

    def set_doc(self, doc):
        """Adopt an externally-owned FieldDoc -- the unified Campaign Editor shares ONE doc across its Logic
        and Dialogue tabs, so both edit the same data with no divergence. Commit the active row first so an
        in-progress edit in this tab isn't lost when the host re-points us."""
        self._commit_active()
        self.doc = doc
        self._refresh_tree()
        if doc is not None:
            self.title_lbl.configure(text=Path(doc.path).name)
            self._set_status(f"{len(self.refs)} dialogue line(s)")

    def on_save(self) -> bool:
        if self.doc is None:
            return False
        self._commit_active()
        reason = protected_reason(self.doc.path)
        if reason:
            messagebox.showerror("Can't save here", f"{self.doc.path}\n\n{reason}.\n\nSave a copy elsewhere.")
            return False
        try:
            self.doc.save()
        except Exception as e:                   # noqa: BLE001
            messagebox.showerror("Save failed", str(e))
            return False
        self._set_status(f"saved {self.doc.path.name}")
        return True

    # ----------------------------------------------------------------- tree
    def _refresh_tree(self, reselect=0):
        self.refs = DLG.collect_text_refs(self.doc.data) if self.doc else []
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.refs):
            self.tree.insert("", "end", iid=str(i), text=r.label)
        self.active = None
        if self.refs and self.tree.exists(str(reselect)):
            self.tree.selection_set(str(reselect))
        elif not self.refs:
            self._show_empty()

    def _on_select(self, _evt=None):
        sel = self.tree.selection()
        if not sel:
            return
        self._commit_active()
        self._show_ref(int(sel[0]))

    # ----------------------------------------------------------------- form
    def _clear_form(self):
        for w in self.form.winfo_children():
            w.destroy()
        self.active = None

    def _welcome(self):
        self._clear_form()
        ttk.Label(self.form, justify="left", wraplength=560, padding=14, text=(
            "FF9 Map Kit - Dialogue editor\n\n"
            "Open a .field.toml to edit every line of its dialogue in one place, with a live preview of how "
            "each line wraps on the FF9 screen.\n\n"
            "Get a file from:  ff9mapkit new MY_ROOM  ·  ff9mapkit import <field>  ·  the Blender export.\n\n"
            "Or click 'Import from game...' to VIEW a real FF9 field's dialogue (point it at your install, "
            "or a built mod folder for an offline look).")).pack(anchor="nw")

    def _show_empty(self):
        self._clear_form()
        ttk.Label(self.form, justify="left", wraplength=560, padding=14, text=(
            "This field has no dialogue yet.\n\nAdd an NPC (with a line), an event message, a choice, or a "
            "cutscene 'say' in the Logic Editor -- they'll all appear here to word-smith.\n\nOr 'Import from "
            "game...' to pull lines from a real field.")).pack(anchor="nw")

    def _show_ref(self, idx):
        self._clear_form()
        if idx >= len(self.refs):
            return
        ref = self.refs[idx]
        pal = self.palette
        ttk.Label(self.form, text=ref.label, font=("", 11, "bold")).pack(anchor="w", padx=8, pady=(8, 2))

        # the line text (multi-line)
        ttk.Label(self.form, text="Line:", foreground=pal["muted"]).pack(anchor="w", padx=10)
        txt = tk.Text(self.form, height=4, wrap="word", relief="flat", borderwidth=0,
                      background=pal["field"], foreground=pal["text"], insertbackground=pal["text"],
                      highlightthickness=1, highlightbackground=pal["border"], highlightcolor=pal["accent"],
                      padx=8, pady=6)
        txt.pack(fill="x", padx=10, pady=(0, 6))
        txt.insert("1.0", DLG.get_text(self.doc.data, ref.path) or "")
        txt.bind("<KeyRelease>", lambda e: self._update_preview())

        speaker_var = tail_var = None
        if ref.speaker_path is not None:
            row = ttk.Frame(self.form)
            row.pack(fill="x", padx=10, pady=2)
            ttk.Label(row, text="Speaker:").pack(side="left")
            speaker_var = tk.StringVar(value=DLG.get_text(self.doc.data, ref.speaker_path) or "")
            ttk.Entry(row, textvariable=speaker_var, width=18).pack(side="left", padx=(4, 12))
            ttk.Label(row, text="Tail:").pack(side="left")
            tail_var = tk.StringVar(value=DLG.get_text(self.doc.data, ref.tail_path) or "")
            ttk.Combobox(row, textvariable=tail_var, width=6, values=[""] + sorted(_text.TAIL_CODES)
                         ).pack(side="left", padx=4)
            ttk.Label(row, text="(window pointer corner; default UPR)", foreground=pal["muted"]).pack(side="left")

        # the live wrap preview
        ttk.Label(self.form, text="On-screen preview (how it wraps in the FF9 window):",
                  foreground=pal["muted"]).pack(anchor="w", padx=10, pady=(8, 0))
        prev = tk.Text(self.form, height=7, wrap="none", state="disabled", relief="flat", borderwidth=0,
                       background=pal["surface"], foreground=pal["text"], font=("Consolas", 11),
                       highlightthickness=1, highlightbackground=pal["border"], padx=8, pady=6)
        prev.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        prev.tag_configure("warn", foreground=pal["warn"])

        self.active = {"idx": idx, "ref": ref, "text": txt, "speaker": speaker_var, "tail": tail_var,
                       "preview": prev}
        # a Browse picker for a speaker that's a renameable party name tag (e.g. [VIVI])
        ttk.Button(self.form, text="Insert name tag...", command=self._pick_name_tag).pack(
            anchor="w", padx=10, pady=(0, 8))
        self._update_preview()

    def _pick_name_tag(self):
        """Pick an archetype/creature and insert its name as a speaker tag (a hint for a renameable name)."""
        if not self.active or self.active["speaker"] is None:
            self._set_status("this line has no speaker field (replies/cutscene says don't take one)")
            return
        name = picker.pick(self.root, kinds=["archetype", "creature"], title="Pick a speaker",
                           initial=self.active["speaker"].get().strip(), campaign_context=self.campaign_plan)
        if name:
            self.active["speaker"].set(name)

    def _wrap_width(self):
        w = (self.doc.data.get("dialogue", {}) or {}).get("wrap") if self.doc else None
        if w is False:                            # [dialogue] wrap = false -> author wraps by hand; no preview break
            return None
        if w is None:
            return _text.DEFAULT_WRAP_WIDTH
        try:
            return float(w)
        except (TypeError, ValueError):
            return _text.DEFAULT_WRAP_WIDTH

    def _update_preview(self):
        if not self.active:
            return
        line = self.active["text"].get("1.0", "end-1c")
        spk = self.active["speaker"].get().strip() if self.active["speaker"] is not None else ""
        shown = _text.with_speaker(spk, line) if spk else line
        width = self._wrap_width()
        wrapped = DLG.wrap_preview(shown, width) if width else shown
        over = DLG.overflow(shown, width) if width else []
        prev = self.active["preview"]
        prev.configure(state="normal")
        prev.delete("1.0", "end")
        prev.insert("1.0", wrapped or "(empty)")
        if over:
            prev.insert("end", f"\n\n! {len(over)} word(s) may overflow the window -- verify in-game.", "warn")
        prev.configure(state="disabled")

    def _commit_active(self):
        """Write the row being edited back into the doc (idempotent; safe when nothing's active)."""
        a = self.active
        if not a or self.doc is None:
            return
        ref = a["ref"]
        DLG.set_text(self.doc.data, ref.path, a["text"].get("1.0", "end-1c").strip("\n"))
        if a["speaker"] is not None and ref.speaker_path is not None:
            DLG.set_text(self.doc.data, ref.speaker_path, a["speaker"].get().strip())
        if a["tail"] is not None and ref.tail_path is not None:
            DLG.set_text(self.doc.data, ref.tail_path, a["tail"].get().strip())
        # refresh the tree label if the entity name didn't change (cheap: keep labels current after edits)
        if self.tree.exists(str(a["idx"])):
            self.tree.item(str(a["idx"]), text=ref.label)

    # ----------------------------------------------------------------- import / view
    def import_lines(self, field, lang="us", mod=None):
        """Read a real field's dialogue (or a mod folder's, with ``mod``) -- the tk-free core the import
        dialog + the --smoke test both call. Returns a list of dialogue.ViewedLine."""
        if mod:
            return DLG.read_local_dialogue(mod, field, lang=lang)
        return DLG.read_field_dialogue(field, lang=lang)

    def on_import(self):
        win = tk.Toplevel(self.root)
        win.title("Import dialogue from the game")
        win.transient(self.root)
        win.geometry("700x600")
        win.minsize(640, 480)
        win.configure(background=self.root["background"])
        pal = self.palette
        top = ttk.Frame(win, padding=8)
        top.pack(fill="x", side="top")
        ttk.Label(top, text="Field:").grid(row=0, column=0, sticky="e", padx=2, pady=2)
        field_var = tk.StringVar(value="100")
        ttk.Entry(top, textvariable=field_var, width=22).grid(row=0, column=1, sticky="w")
        ttk.Label(top, text="(real field id / FBG name)", foreground=pal["muted"]).grid(row=0, column=2, sticky="w")
        ttk.Label(top, text="Lang:").grid(row=1, column=0, sticky="e", padx=2, pady=2)
        lang_var = tk.StringVar(value="us")
        ttk.Entry(top, textvariable=lang_var, width=6).grid(row=1, column=1, sticky="w")
        ttk.Label(top, text="From mod:").grid(row=2, column=0, sticky="e", padx=2, pady=2)
        mod_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=mod_var, width=40).grid(row=2, column=1, columnspan=2, sticky="we")
        ttk.Label(top, text="(optional: a built mod folder to read offline -- no install needed)",
                  foreground=pal["muted"]).grid(row=3, column=1, columnspan=2, sticky="w")
        top.columnconfigure(1, weight=1)

        bar = ttk.Frame(win, padding=8)               # reserve the buttons at the BOTTOM first, so they keep
        bar.pack(side="bottom", fill="x")             # their natural height even on a short window
        out = tk.Text(win, wrap="word", state="disabled", relief="flat", borderwidth=0, font=("Consolas", 10),
                      background=pal["surface"], foreground=pal["text"], padx=8, pady=6)
        out.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 6))
        state = {"lines": []}

        def do_read():
            try:
                lines = self.import_lines(field_var.get().strip(), lang_var.get().strip() or "us",
                                          mod_var.get().strip() or None)
            except Exception as e:               # noqa: BLE001
                messagebox.showerror("Import failed", str(e), parent=win)
                return
            state["lines"] = lines
            out.configure(state="normal")
            out.delete("1.0", "end")
            out.insert("1.0", DLG.format_lines(lines) if lines else "(no dialogue found)")
            out.configure(state="disabled")

        def insert_npcs():
            npc_lines = [ln for ln in state["lines"] if ln.source == "npc" and ln.text]
            if not npc_lines or self.doc is None:
                messagebox.showinfo("Nothing to insert",
                                    "Read a field first, and open a field.toml to insert into.", parent=win)
                return
            lst = self.doc.data.setdefault("npc", [])
            for ln in npc_lines:
                lst.append({"name": f"imported_{len(lst)}", "preset": "vivi",
                            "dialogue": ln.text, "pos": [0, 0]})
            self._refresh_tree()
            self._set_status(f"inserted {len(npc_lines)} NPC stub(s) -- position them in Blender / the Logic Editor")
            win.destroy()

        ttk.Button(bar, text="Read", command=do_read, style="Accent.TButton").pack(side="left")
        ttk.Button(bar, text="Insert NPC stubs into this field", command=insert_npcs).pack(side="left", padx=6)
        ttk.Button(bar, text="Close", command=win.destroy).pack(side="right")
        win.grab_set()


def build(parent, path=None):
    return DialogueApp(parent, path)


def _smoke():
    """Headless self-test: load a field, edit a line, commit, preview; import the hut offline."""
    import tempfile
    root = tk.Tk()
    root.withdraw()
    # a tiny field with one NPC line (avoid editing a bundled example -- protected_reason blocks Save there)
    d = Path(tempfile.mkdtemp())
    f = d / "smoke.field.toml"
    f.write_text('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
                 '[walkmesh]\nquad = [[0,0],[10,0],[10,10],[0,10]]\n\n'
                 '[[npc]]\nname = "V"\npos = [0,0]\ndialogue = "Hi."\n', encoding="utf-8")
    app = DialogueApp(root, f)
    assert app.refs and app.refs[0].section == "npc", app.refs
    app.tree.selection_set("0")
    app._show_ref(0)
    app.active["text"].delete("1.0", "end")
    app.active["text"].insert("1.0", "A longer rewritten line that the author just typed in.")
    app._update_preview()
    app._commit_active()
    assert DLG.get_text(app.doc.data, ("npc", 0, "dialogue")).startswith("A longer rewritten"), app.doc.data
    assert app.on_save() and "A longer rewritten" in f.read_text(encoding="utf-8")
    # the offline import path (the shipped hut joins to its line)
    hut = ROOT / "release" / "FF9CustomMap"
    if hut.is_dir():
        lines = app.import_lines("HUT_INT", mod=str(hut))
        assert any(ln.text == "I miss you Zidane" for ln in lines), lines
        imported = "offline hut import OK"
    else:
        imported = "hut import skipped (release absent)"
    print(f"dialogue app smoke ok: {len(app.refs)} line(s); edit+save round-trips; preview built; {imported}")
    root.destroy()


def main():
    if "--smoke" in sys.argv:
        _smoke()
        return
    arg = next((a for a in sys.argv[1:] if not a.startswith("-")), None)
    root = tk.Tk()
    root.title("FF9 Map Kit - Dialogue")
    root.minsize(880, 560)
    root.geometry("1040x680")
    try:
        DialogueApp(root, arg)
    except Exception:                            # noqa: BLE001
        messagebox.showerror("FF9 Map Kit - Dialogue", traceback.format_exc())
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
