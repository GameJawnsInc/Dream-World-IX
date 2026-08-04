# Rung 1 playtest — demand-driven `story-seed` presets, in-game

Three verbatim forks, each booted with `story-seed`'s emitted `[startup]` block **pasted
verbatim — zero hand edits** (the rung's honesty requirement). Sources under
`C:\gd\_ns_playtest\`; revert via the per-id `revert_deploy_308NN.py` scripts. New ids →
**one game RELAUNCH** needed before the first warp.

| slot | donor | seed | what to look for |
|---|---|---|---|
| **30820** | 111 — Alexandria inn, disc-1 play night | `scenario = 1152`, once-flag 3719 left clear | You are **Vivi, alone**. Walk toward the innkeeper: the **"Whaddya mean, there's no vacancies!!!?"** scene should fire (camera move + angry customer). ~ → Reload and walk again: it should REPLAY (the seed clears the once-flag every load — intended for testing). |
| **30821** | 352 — Dali inn, beat **2700** | 7 bits seeded; **2073 clear** (its window opens at 2990) | The inn during the party's Dali stay. Note the cast present and the state of the story-gated door (it reads bits 2064/2073/2078). |
| **30822** | 352 — same donor, beat **3000** | same + **2073 SET**, scenario 3000 | The SAME room, later beat. The A/B question: does anything observably differ from 30821 — the gated door, the cast, dialogue? The two tomls differ ONLY by `scenario` and bit 2073. |

Verdicts to report per slot: behaves-as-the-beat / scenario-zero-ish / wrong-or-weird (what).

Known limits going in (say so if they bite): bit **2078** is a set-AND-cleared toggle the tool
refuses to auto-seed (reported in the toml comments — if the Dali door looks wrong, that's the
first suspect); **party composition is not seeded** (rung 7) — a scene gating on a specific
cast member may silently not fire (the Ice Cavern lesson).

## Results

- 30820 (111 @ 1152): PENDING
- 30821 (352 @ 2700): PENDING
- 30822 (352 @ 3000): PENDING
