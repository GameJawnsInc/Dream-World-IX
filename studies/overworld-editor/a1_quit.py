"""Rung A1's in-game check, scenario 2 of 2: close the game a1_reach.py left open (run with ``--attach``)."""


def run(g):
    g.shot("a1-final")
    g.send("quit", wait=False)
