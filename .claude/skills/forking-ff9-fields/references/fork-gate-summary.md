# The s23-s33 fork-gate suite — what it restores (one-paragraph summary)

Distilled from memory `[[project-ff9-doeventcode-fork-gates]]` and `ff9mapkit/docs/ENGINE.md`. (The
blocks below once quoted `CLAUDE.md` §5/§7 verbatim; that section was refactored INTO the skills, so
they are re-attributed to the sources that own the facts today — the content is unchanged.)
For building/patching the engine itself, use the `building-the-memoria-engine` skill.

**The summary.** The law as it lives today in memory `[[project-ff9-doeventcode-fork-gates]]`
(§Lesson) and the `building-the-memoria-engine` skill's
`.claude/skills/building-the-memoria-engine/references/fork-gate-census.md` (§The principle):

> **Any engine behavior hardcoded on a real `fldMapNo` (or FBG name) is LOST on a custom-id fork.** The
> fork-gate census must sweep it in FOUR forms — a `== N` compare, a local alias (`Int16 mapNo = fldMapNo`),
> a NAME key, and a lookup ARGUMENT — each fixed by a matching lever (`EffectiveFieldId` /
> `EffectiveFieldName` / `FieldLocationName`, the s23–s33 suite). → `ff9mapkit/docs/FORK_IDGATE_MAP.md`.

Why this makes forked fields engine-dependent (canonical statement: `ff9mapkit/docs/ENGINE.md`
§"the bundled fidelity patch set"; also the `building-the-memoria-engine` skill §Engine-independence
split):

> a **FORKED field REQUIRES the s23–s33 suite** (else it loses Dante's off-mesh exemption, narrow-map
> width, the fake-battle return, the softlock fixes, etc.)

The four gate classes and their levers (full per-form table with canonical examples: the
`building-the-memoria-engine` skill's
`.claude/skills/building-the-memoria-engine/references/fork-gate-census.md` §The four gate forms):

> Four gate classes, four levers: `== N` compare + local-alias
> `mapNo` (`EffectiveFieldId`, s23/s24/s29/s30), NAME-keyed (`EffectiveFieldName`, s31/s32), and lookup-arg
> (`FieldLocationName`, s33; this also backs the authorable `[field] location`).

## The ForkDonorPatch.txt deploy leg

The engine learns fork -> donor from a per-mod-folder `ForkDonorPatch.txt` (`<forkId> <donorRealId>`
lines, read by `DataPatchers` at LAUNCH — relaunch to apply). `build_campaign` emits it;
`deploy_field.py` emits/merges it for verbatim forks. From memory `[[project-ff9-npc-on-verbatim]]`,
verbatim:

> deploying a verbatim fork via deploy_field needs ForkDonorPatch; if a fork's whole-scene
> occlusion/fork-behaviors look wrong, check for it first.

## Debugging a lost gate

From memory `[[project-ff9-doeventcode-fork-gates]]`, verbatim:

> ★★ **CASCADE LESSON (load-bearing for fork debugging): one lost id-gate can surface as MULTIPLE
> unrelated-looking symptoms.**

(The forked Ice Cavern's "broken jump" was downstream of the no-encounter id-gate; an in-game A/B of
real field vs fork isolated the real cause before a phantom fix was built.)

## Depth

- Per-site census + verification debt: `ff9mapkit/docs/FORK_IDGATE_MAP.md`.
- Gate verification harness: `tools/verify_fork_gates.py` (see memory
  `[[project-ff9-fork-verification-harness]]`).
- Patch sources: `memoria-patches/` (s23-s33 + s34/s35); origin story + all three census blind
  spots: memory `[[project-ff9-doeventcode-fork-gates]]`.
- Engine build recipe / auto-deploy warning: the `building-the-memoria-engine` skill; memory
  `[[project-ff9-memoria-build]]`.
