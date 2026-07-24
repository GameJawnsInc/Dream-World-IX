# jawn-relay v2 — the rejoin-grace relay (deployed 2026-07-23)

The co-op relay server (`wss://relay.jawnston.com` → Caddy TLS → this process on
`127.0.0.1:7777`). **The live source of truth is `/opt/jawn-relay/main.go` on the
server** (ssh alias `mygame`, systemd unit `jawn-relay.service`); this directory
keeps a byte-identical copy + the live smoke test for provenance.

## What v2 changed (vs the May-13 v1)

v1 killed BOTH legs and deleted the session the moment EITHER leg errored — the
amplifier that turned every one-machine wobble into a two-sided despawn/re-pair
(the 2026-07-23 flaky session: 6 drops in ~110s, each a single-leg `close 1006`
EOF that took the healthy partner down with it). v2:

- **Park, don't kill**: an ABNORMAL drop parks that role's slot; the survivor
  keeps its connection (frames to the absent partner are dropped — the wire is
  latest-state ~30Hz, loss self-heals). The dropped role rejoins with the same
  code within a 60s grace; the session resumes.
- **Replace stale occupants**: a fast redial that finds its old half-open conn
  still in the slot replaces it (old conn closed; its handler retires via
  pointer-identity guards).
- **Clean quit still ends the session immediately**: a WS close 1000/1001 tears
  down at once (smoke-proven 0.05s) — only abnormal drops park.
- **Idle reaper**: 90s read deadline (the wire is never quiet when healthy) so a
  silently-dead pair can't leak conns/goroutines forever.
- **Hardening from the pre-deploy adversarial review**: per-leg write mutex (the
  gorilla one-writer contract across a fast-reconnect overlap), gc re-validation
  before teardown (rejoin-vs-expiry race), pair-timeout re-check (timer-vs-pair
  select race).

## Deploy recipe

```
ssh mygame "cd /opt/jawn-relay && ts=$(date +%Y%m%d-%H%M%S) && cp main.go main.go.bak.$ts && cp relay relay.bak.$ts"
scp studies/battle-coop/relay/main.go mygame:/opt/jawn-relay/main.go
ssh mygame "cd /opt/jawn-relay && /snap/bin/go build -o relay.new . && mv relay.new relay && systemctl restart jawn-relay"
py studies/battle-coop/relay/smoke_test.py   # live acceptance: pair / abnormal-kill survive / rejoin / clean-quit
```

v1 backups on the server: `main.go.v1.20260723-212040` / `relay.v1.20260723-212040`.

## Smoke test

`smoke_test.py` is a self-contained WS client (TLS + handshake + masked frames,
no kit imports) that runs the four-scenario acceptance against the LIVE endpoint.
Both post-deploy runs: ALL PASS (2026-07-23).
