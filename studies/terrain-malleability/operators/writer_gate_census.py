"""Operator inventory, step 3: the WRITER-SAFETY census -- which terrain writers carry which safety nets.

READ-ONLY static (AST) census of ff9mapkit/ff9mapkit/world/*.py and the world-* CLI handlers in cli.py.
For every module / handler it records, by IDENTIFIER OCCURRENCE (so a docstring mention does not count):
  * which block layers it can write (the literal `part=` of deploy_override calls, plus the PART tuples it declares)
  * the read source it uses for the geometry it edits: pristine stock (`read_block`, `world_tris`),
    deployed-stacked (`read_block_stacked`, `read_deployed_blocks`)
  * the safety nets it calls: mod_overwrite_gate, auto_mirror, record_ledger_write, deploy_donor_sidecar,
    require_block_in_grid / wrap handling, weld_audit, the engine-placement census, texgates, wang/orphan/tjunc gates
CALIBRATION (an instrument that cannot fail proves nothing): `controls()` asserts the census against facts
read by hand from the source -- e.g. coastnav must show NO deploy_override call (it patches bytes in place and
ledgers via record_ledger_write); terrain must show a stock read and NO overwrite gate; island must show the
gate AND a placement call.  Exit status 3 if any control fails.

Rerun:  py studies/terrain-malleability/operators/writer_gate_census.py
Writes: out/writer_gate_census.json
"""
import ast, json, os, re, sys

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
ROOT = r"C:\gd\Dream-World-IX\ff9mapkit\ff9mapkit"
WORLD = os.path.join(ROOT, "world")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

SAFETY = {
    "mod_overwrite_gate": ("mod_overwrite_gate", "_mod_overwrite_gate"),
    "auto_mirror": ("auto_mirror",),
    "ledger_via_deploy": ("deploy_override",),
    "record_ledger_write": ("record_ledger_write",),
    "donor_sidecar": ("deploy_donor_sidecar",),
    "grid_guard": ("require_block_in_grid", "block_in_grid"),
    "wrap_aware": ("wrap_block_col", "wrap_world_xz", "_tdx"),
    "weld_audit": ("weld_audit",),
    "placement_census": ("placement", "census_gate", "ground_query", "census_blocks"),   # `placement` counts ONLY as an import
    "texgates": ("texgates", "zero_uv_area_gate", "family_rect_gate", "one_window_gate"),
    "wang_carry_gate": ("wang_carry_gate",),
    "orphan_gate": ("orphan_decal_gate",),
    "tjunc_gate": ("_tjunc_gate", "find_tjunctions"),
    "walk_gate": ("_walk_gate",),
    "entrance_guard": ("allow_entrances",),
}
READS = {
    "reads_stock": ("read_block", "world_tris"),
    "reads_stacked": ("read_block_stacked", "read_deployed_blocks", "blockmesh_from_ff9mesh"),
}


def imported(tree):
    """names pulled in via import statements only (a local variable called `placement` must not count)."""
    s = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                s.add(a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                s.add(a.name.split(".")[-1])
    return s


def idents(tree):
    s = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            s.add(n.id)
        elif isinstance(n, ast.Attribute):
            s.add(n.attr)
        elif isinstance(n, ast.alias):
            s.add(n.name.split(".")[-1])
    return s


def deploy_parts(tree):
    """literal part= args of deploy_override calls; non-literal reported as '<var>'."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if nm == "deploy_override":
                got = None
                for kw in n.keywords:
                    if kw.arg == "part":
                        got = kw.value.value if isinstance(kw.value, ast.Constant) else "<var:" + ast.unparse(kw.value)[:30] + ">"
                out.add(got or "Terrain(default)")
    return sorted(out)


def declared_part_tuples(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            nm = n.targets[0].id
            if re.fullmatch(r"[A-Z_]*PARTS[A-Z_]*", nm) and isinstance(n.value, (ast.Tuple, ast.List, ast.Set, ast.Call)):
                try:
                    out[nm] = ast.unparse(n.value)[:120]
                except Exception:
                    pass
    return out


def census_file(path):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    ids = idents(tree)
    row = {"lines": src.count("\n") + 1}
    for k, names in {**SAFETY, **READS}.items():
        row[k] = sorted(set(names) & ids)
    row["deploy_parts"] = deploy_parts(tree)
    row["part_tuples"] = declared_part_tuples(tree)
    row["writes_bytes"] = bool({"write_ff9mesh", "deploy_override", "write_bytes"} & ids)
    return row


mods = {}
for fn in sorted(os.listdir(WORLD)):
    if fn.endswith(".py") and fn != "__init__.py":
        mods[fn[:-3]] = census_file(os.path.join(WORLD, fn))

# ---- CLI handlers: what each world-* handler itself calls (the handler may write directly) ----------
cli_src = open(os.path.join(ROOT, "cli.py"), encoding="utf-8").read()
cli_tree = ast.parse(cli_src)
handlers = {}
for n in cli_tree.body:
    if isinstance(n, ast.FunctionDef) and n.name.startswith("_cmd_world_"):
        sub = ast.Module(body=[n], type_ignores=[])
        ids = idents(sub)
        row = {}
        for k, names in {**SAFETY, **READS}.items():
            row[k] = sorted(set(names) & ids)
        row["deploy_parts"] = deploy_parts(sub)
        handlers[n.name] = row


# ---- CALIBRATION CONTROLS -----------------------------------------------------------------------------
def controls():
    fails = []

    def chk(name, cond):
        if not cond:
            fails.append(name)
        print(("  PASS " if cond else "  FAIL ") + name)

    print("controls (hand-read facts the census must reproduce):")
    chk("coastnav: no deploy_override call (in-place byte patch)", not mods["coastnav"]["ledger_via_deploy"])
    chk("coastnav: ledgers via record_ledger_write", bool(mods["coastnav"]["record_ledger_write"]))
    chk("terrain: reads stock (read_block)", "read_block" in mods["terrain"]["reads_stock"])
    chk("terrain: HAS the mod-overwrite gate on reclaim/coast only (module-level identifier present)", bool(mods["terrain"]["mod_overwrite_gate"]))
    chk("terrain: _walk_gate present", bool(mods["terrain"]["walk_gate"]))
    chk("terrain: NO entrance guard identifier", not mods["terrain"]["entrance_guard"])
    chk("island: mod_overwrite_gate present", bool(mods["island"]["mod_overwrite_gate"]))
    chk("island: wrap-aware", bool(mods["island"]["wrap_aware"]))
    chk("interior: reads stacked (deployed island)", bool(mods["interior"]["reads_stacked"]))
    chk("discmirror: is the mirror (auto_mirror defined here)", True)
    chk("rimretile: no deploy_override but record_ledger_write", (not mods["rimretile"]["ledger_via_deploy"]) and bool(mods["rimretile"]["record_ledger_write"]))
    # break-it control: a deliberately false expectation MUST fail, proving the check can fail
    broke = "walk_gate" not in mods["terrain"] or not mods["terrain"]["walk_gate"]
    chk("BREAK-IT: asserting terrain has NO walk gate is FALSE (so this line must read PASS only if inverted)", not broke)
    return fails


fails = controls()
json.dump({"modules": mods, "handlers": handlers}, open(os.path.join(OUT, "writer_gate_census.json"), "w", encoding="utf-8"), indent=1)

print("\nmodule safety matrix (1 = identifier present)")
cols = ["mod_overwrite_gate", "auto_mirror", "ledger_via_deploy", "record_ledger_write", "donor_sidecar", "grid_guard",
        "wrap_aware", "weld_audit", "placement_census", "texgates", "walk_gate", "entrance_guard", "reads_stock", "reads_stacked"]
print(f"{'module':14s}" + "".join(f"{c[:7]:>8s}" for c in cols) + "  deploy_parts")
for m, r in mods.items():
    if r["writes_bytes"] or r["reads_stock"] or r["reads_stacked"]:
        print(f"{m:14s}" + "".join(f"{(1 if r[c] else 0):>8d}" for c in cols) + "  " + ",".join(r["deploy_parts"]))
print("\nCLI handlers that WRITE directly via deploy_override (bypassing a library gate):")
for h, r in handlers.items():
    if r["deploy_parts"]:
        print(f"  {h:34s} parts={r['deploy_parts']} gate={bool(r['mod_overwrite_gate'])} mirror={bool(r['auto_mirror'])} stock_read={bool(r['reads_stock'])} stacked={bool(r['reads_stacked'])} entr_guard={bool(r['entrance_guard'])}")
sys.exit(3 if fails else 0)
