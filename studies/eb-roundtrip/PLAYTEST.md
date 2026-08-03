# eb-roundtrip arc — playtest checklist (slot 30810)

> ★ **PLAYTEST PASSED (owner, 2026-08-03):** Test A — the chest gave an **Elixir** with the
> matching message (the 4-byte source edit executed correctly in-engine). Test B — everything
> else played like stock Ice Cavern (the verbatim remainder is faithful). The arc's flagship
> proof is in-game confirmed.

**What is deployed:** a verbatim fork of Ice Cavern (donor 302, `EVT_ICE_IC_TER_0`) at scratch
id **30810** in `FF9CustomMap`, whose chest reward was changed **by editing decompiled `.ebs`
source text** — not a `[[logic_edit]]`, not a byte patch: `eb-src` decompiled the deployed
`.eb`, the lines `AddItem(236, 1)  # Potion` / `SetTextVariable(0, 236)` were edited to 239 in
the text (both give paths + both display sites), and `eb-asm --against` spliced exactly those
4 bytes back into the 9,268-byte file. All 7 languages were edited identically. Backups of the
pre-edit files: `backups/*.eb.bytes.<lang>.20260803-153914` (main repo).

**Requires:** a RELAUNCH first (new-id registration + ForkDonorPatch are read at launch), and
the custom engine bundle (it is a forked field).

## Test A — the source-edited chest (the arc's flagship proof)

1. Launch FF9 → any save or New Game → `~` → Go → **Warp to field 30810**.
2. Walk to the chest and open it.
3. **PASS:** the message says **"Received Elixir!"** AND the inventory gains **1 Elixir**.
   - "Received Potion!" or a Potion in the bag = a site was missed → report which half.
   - No prompt at all = the once-guard thinks it's looted → `~` → Flags → report.
4. Re-interact with the chest: it must NOT re-give (the donor's once-guard is untouched).

## Test B — everything else is verbatim (5 minutes, optional but valuable)

The other 9,264 bytes are the donor's own. Walk the room, cross a gateway trigger zone, let a
random encounter fire, check the battle music. **PASS:** indistinguishable from real Ice
Cavern behavior. Any anomaly here is a round-trip fidelity bug and is exactly what I want to
hear about.

## Test C — language consistency (30 seconds, optional)

Switch the game language (uk or fr) → reopen a save → warp 30810 → the chest text/name
conventions of that language, but the reward is still Elixir (all 7 langs edited).

## Reading material

The decompiled, annotated sources you can read (and grep) are in
`C:\gd\_ebs_playtest\source\<lang>.ebs` — e.g. `us.ebs` line ~1026: `AddItem(239, 1)  # Elixir`.

## Revert

- Whole field: `py tools/scroll_out/revert_deploy_30810.py`
- Just the source edit (keep the fork, restore Potion): copy the timestamped backups from the
  main repo `backups/` over the deployed `field/<lang>/*30810*.eb.bytes` files.
