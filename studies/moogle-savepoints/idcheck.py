"""Byte-identity harness: does a change alter the DEFAULT [[savepoint]] output?

Builds five savepoint shapes and prints one sha256 per shape. Run it against a PRISTINE tree and against
the changed tree, then diff the two outputs -- any shape whose hash moved has had its bytes altered.

    py studies/moogle-savepoints/idcheck.py <path-to-kit-root>

To materialise a pristine tree to compare against (the templates are gitignored, so copy them over):

    git archive HEAD ff9mapkit | tar -x -C /tmp/base
    cp -r ff9mapkit/ff9mapkit/data/blank_field /tmp/base/ff9mapkit/ff9mapkit/data/
    cp ff9mapkit/ff9mapkit/data/region_template.bin /tmp/base/ff9mapkit/ff9mapkit/data/

WARNING, learned the hard way: it MUST pass `savepoint_txids` (via `build.collect_text`). Without them
the ACT never fires and three different configs hash IDENTICALLY -- the harness looks green while
testing almost nothing. The collect_text call below is that fix; do not "simplify" it away.
"""
import sys, pathlib, tempfile
sys.path.insert(0, sys.argv[1])
from ff9mapkit import build
HEAD = ('[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-600,-600],[600,-600],[600,600],[-600,600]]\n\n'
        '[player]\nspawn = [0, 0]\n\n')
CASES = {
    "bare":  '[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n',
    "dressed": ('[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n'
                'tent = true\nparty = true\nact_hop_to = [-40, 70]\n'),
    "no_moogle": '[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nmoogle = false\n',
    "no_act": '[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nact = false\n',
    "two": ('[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n\n'
            '[[savepoint]]\nzone = [[210,-10],[250,-10],[250,-50],[210,-50]]\n'),
}
td = pathlib.Path(tempfile.mkdtemp())
for name, body in CASES.items():
    p = td / f"{name}.field.toml"
    p.write_text(HEAD + body, encoding="utf-8")
    proj = build.FieldProject.load(p)
    _mes, *_rest = build.collect_text(proj)
    sp_txids = _rest[-1]          # the ACT only fires when its txids are supplied
    eb = build.build_script(proj, "us", {}, savepoint_txids=sp_txids)
    print(f"{name}\t{len(eb)}\t{__import__('hashlib').sha256(eb).hexdigest()[:32]}")
