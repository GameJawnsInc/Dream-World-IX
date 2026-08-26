"""Measure the INDIRECT reward protocol the census cannot see:

  caller:  Byte[226] = Bit[N]            (read latch)
           Int16[224] = <reward code>    (literal: <512 item, 512..999 card, >=1000 gil-1000)
           RunScript*(uid, tag 12|13)    (shared reward helper on the player object)
           Bit[N] = Byte[226]            (commit latch only if the grant landed)

The census attributes the grant to the HELPER (computed operand, no guard, no
literal latch write) -> classes it `unresolved` / `bare`.
"""
import json, os, sys, collections
REPO = r"C:\gd\Dream-World-IX\.claude\worktrees\ff9-completion-journal-research-d86041"
sys.path.insert(0, os.path.join(REPO, "ff9mapkit"))
from ff9mapkit.extract import EventBundle, ID_TO_EVT
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.cfg import FieldFlow, parse_set, RUNSCRIPT_OPS

SET = 0x05
CALL_OPS = frozenset({0x10, 0x12, 0x14, 0x16, 0x18, 0x1A})


def main():
    bundle = EventBundle()
    stats = collections.Counter()
    sites = []
    for fid in sorted(ID_TO_EVT):
        try:
            data = bundle.eb_for_id(fid)
            if not data:
                continue
            eb = EbScript.from_bytes(data)
            ff = FieldFlow.build(eb)
        except Exception:
            continue
        raw = eb.data
        for key, fl in ff.flows.items():
            for blk in fl.blocks:
                if fl._dom[blk.index] == 0:
                    continue
                ins_list = blk.instrs
                for i, ins in enumerate(ins_list):
                    if ins.op != SET:
                        continue
                    st = parse_set(raw, ins)
                    if st.kind != "assign" or st.source != 0:
                        continue
                    # (a) reward-code literal into the arg slot Int16[224]
                    if st.vtype in (6, 7) and st.index == 224 and st.value is not None:
                        code = st.value
                        # is a script call within the next few instructions?
                        nxt = [x for x in ins_list[i + 1:i + 6] if x.op in CALL_OPS]
                        if nxt:
                            stats["reward_code_call_sites"] += 1
                            kindc = ("gil" if code >= 1000 else
                                     "card" if code >= 512 else "item")
                            stats["reward_code_" + kindc] += 1
                            sites.append({"field": fid, "key": list(key),
                                          "off": ins.off, "code": code,
                                          "kind": kindc})
                    # (b) latch commit whose VALUE is a variable, not literal 1
                    if st.vtype in (0, 1):
                        if st.value == 1:
                            stats["bit_write_literal_1"] += 1
                        elif st.value is None:
                            stats["bit_write_COMPUTED"] += 1
                        else:
                            stats["bit_write_literal_other"] += 1
    per_field = collections.Counter(s["field"] for s in sites)
    print(json.dumps({
        "stats": dict(sorted(stats.items())),
        "reward_code_call_sites_total": len(sites),
        "fields_with_reward_code_calls": len(per_field),
        "top_fields": per_field.most_common(15),
        "distinct_codes": len({s["code"] for s in sites}),
    }, indent=1))
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "indirect.json"), "w") as fh:
        json.dump(sites, fh)


main()
