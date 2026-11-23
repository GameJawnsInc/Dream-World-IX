"""Does the argv TraceDoc emits parse? (an event message starting with '-'; --id band in the CLI)"""
from ff9mapkit.cli import build_parser
p = build_parser()
for msg in ("-Stop!", "--", "Hello there"):
    try:
        a = p.parse_args(["image-field", "x.png", "--floor", "1,2 3,4 5,6", "--out", "o",
                          "--event-zone", f"{msg}@1,2;3,4;5,6;7,8"])
        print(repr(msg), "-> parsed", a.event_zone)
    except SystemExit as e:
        print(repr(msg), "-> argparse SystemExit", e.code)
a = p.parse_args(["image-field", "x.png", "--floor", "1,2 3,4 5,6", "--out", "o", "--id", "9005"])
print("--id 9005 accepted by the parser:", a.id)
