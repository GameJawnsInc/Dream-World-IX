exec(open(r"<SCRATCH>/review/cutscene-code/p5_problems_parity.py").read().split("case(\"say leads")[0])
case("player acts without being in the cast", [{"face_player": True, "actor": "Cid"}, {"turn": 64, "actor": "player"}])
case("dup of a with_prev turn", [{"walk": "altar", "actor": "Cid"}, {"turn": 128, "actor": "Mira", "with_prev": True}, {"turn": 128, "actor": "Mira", "with_prev": True}])
