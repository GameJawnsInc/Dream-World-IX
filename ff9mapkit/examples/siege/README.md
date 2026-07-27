# siege — a tower-defense minigame in one block

A whole playable game mode from a single `[siege]` table: hold the depot until the clock
runs out, buying troops from a war council that deploys them where you stand, while raiders
arrive in timed waves and fight whatever blocks them.

```
ff9mapkit lint  examples/siege/siege.field.toml
ff9mapkit build examples/siege/siege.field.toml --out dist --mod-name Siege
```

It is an ordinary **novel field** — placeholder art in `art/` (repaint it), a plain quad
walkmesh, and it runs on **stock Memoria**: no donor field, no engine patches. Reaching it
in-game is up to you (a gateway from another field, or the debug menu's warp).

## What the one block generates

Everything except the field itself. `[siege]` desugars at load into the plain, separately
proven blocks — you can see exactly what it produced with `ff9mapkit behavior compile`:

| You write | You get |
|---|---|
| `timer` + `waves` | the countdown HUD, a data-table wave clock, and the wave counter |
| `[[siege.ally]]` | a priced hire pool, its war-council row (hidden while unaffordable or sold out), the class's whole behavior tree, and parked seats for its units |
| `[[siege.raider]]` | staged spawns, the wave-gated march down its lane, the counter-engage when something blocks it, and the depot commit |
| `[siege.base]` | the thing being defended, its HP, and the win/loss detection |
| `win_gil` / `win_item` | a single payout that can never double-fire |
| the theater dials | wave heralds, hit cues, death animations, the win wash, the loss sting |

Drop every optional dial and the siege still plays — the presentation is additive.

## Where to look next

- **`docs/FORMAT.md` § `[siege]`** — every dial, with defaults.
- **`docs/BEHAVIOR.md`** — what the generated trees actually are, and the laws they encode
  (the reveal beat, the clock-coupled battle law, the field-animation laws). Worth reading
  before you swap in your own animations or a `loss_battle`.
- **`studies/fort-condor/`** — the arc this productizes, if you want the history.

## Making it yours

Start by changing numbers (`timer`, `waves`, prices, `hp`, `radius`) — those need no new
knowledge. Then models and animations, but check what a rig actually owns first:
`ff9mapkit models <MODEL>` lists its clips, and gestures must come from the model's **own
form** (a different form is a different skeleton, and the linter refuses it).
