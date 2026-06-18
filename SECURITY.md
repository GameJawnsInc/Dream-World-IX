# Security Policy

**Dream World IX** (the `ff9mapkit` toolkit) is a desktop modding tool, not a network service.
It runs locally and modifies a copy of *Final Fantasy IX* that you own. There are no servers,
accounts, or remote endpoints in scope. Even so, we take reports seriously — bugs that could
corrupt a user's game install or run unexpected code matter here.

## Supported version

This project is in **public beta**. Security fixes target the **latest `main`** (the current beta).
There are no long-term support branches; please reproduce against an up-to-date checkout before
reporting.

## Reporting a vulnerability

- **For routine bugs** (including non-sensitive security hardening), open a
  [GitHub issue](../../issues) with steps to reproduce, your OS and Python version, and the
  `ff9mapkit` version (`py -m ff9mapkit --version`).
- **For anything sensitive** — something that could be abused before a fix is available — please
  report it privately rather than in a public issue. Contact the maintainer
  (**GameJawnsInc**) through GitHub (a private security advisory on the repository, or a direct
  message) so the issue can be triaged before disclosure.

This is a small, hobby-scale project: there is **no formal SLA or bug-bounty**. We will
acknowledge a report as soon as we reasonably can and work with you on a fix and coordinated
disclosure.

## Safety posture

A few things worth knowing about how the toolkit operates:

- **It edits a local game install.** Deploying a mod writes into your *Final Fantasy IX* folder
  and its mod directory. **Always back up your clean game install first** — a copy of the whole
  install folder is your only true reset. The deploy scripts also write per-id revert helpers, but
  treat the backup as authoritative.
- **It ships no game data.** The repository and published package contain **zero** Square-Enix
  bytes. Base assets are regenerated from *your own* install via `ff9mapkit extract-templates`.
  Never commit FF9 game bytes when contributing — see
  [`ff9mapkit/docs/PROVENANCE.md`](ff9mapkit/docs/PROVENANCE.md) and the root
  [`DISCLAIMER.md`](DISCLAIMER.md).
- **It runs the code you give it.** Like any build tool, the toolkit and the Blender add-on
  execute on your machine and process files you point them at. Only run `field.toml` projects,
  mods, and patches from sources you trust.
- **No warranty.** The software is provided "as is", without warranty of any kind — see
  [`LICENSE`](LICENSE) and [`DISCLAIMER.md`](DISCLAIMER.md).
