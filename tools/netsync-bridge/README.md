# netsync-bridge — ws→wss bridge for FF9 co-op ghost sync

FF9's Unity Mono runtime predates TLS 1.2, so the game cannot talk to the
public co-op relay (which is `wss://`, TLS-only) directly. Each player runs
this tiny bridge next to the game instead:

```
FF9  ──ws:// (loopback)──►  netsync_bridge.py  ──wss:// (TLS)──►  public relay
```

The bridge is a dumb pipe: it completes the WebSocket handshake on both hops
and then forwards bytes verbatim. It holds no game state and no secrets — the
default relay endpoint is baked in (lightly obfuscated only to keep the URL
out of automated string-scrapers; the real access gate is your random session
code).

## Quickstart — the one-command way

`ff9mapkit coop` does everything on this page for you (room deploy, config,
code, bridge):

```
ff9mapkit coop host              # player 1 -- prints + copies your session code
ff9mapkit coop join ff9-XXXX     # player 2 -- with the host's code
```

Leave the command running while you play (it hosts the bridge), launch FF9,
and F6 → Warp → 30003 on both machines. The rest of this page is the manual
version of the same setup.

## Manual setup (both players)

1. Run the bridge (needs Python 3.8+, no packages):

   ```
   py netsync_bridge.py
   ```

   Leave it running. It listens on `ws://127.0.0.1:49201`.

2. In `<game>\Memoria.ini`, point the game at it:

   ```ini
   [Netsync]
   Enabled = 1
   Role = host            ; the OTHER player sets Role = client
   TargetField = 30003
   RelayUrl = ws://127.0.0.1:49201
   SessionCode =          ; leave empty on the host — see below
   ```

3. **Session code:** on first launch the **host's** game generates a random
   code (`ff9-XXXXXXXX`), saves it into their `Memoria.ini`, and logs it to
   `Memoria.log`. The host reads it out of either place and sends it to the
   other player, who pastes it as their `SessionCode`. The code is the only
   thing that pairs you two on the shared relay — anyone without it cannot
   join your session. Codes are case-insensitive.

4. Both launch the game and warp to the co-op field (F6 → Warp → 30003).
   Each of you should see the other's ghost walk the room.

With the current custom engine the `[Netsync]` section **hot-reloads**: a
running game picks up edits within a couple of seconds (enabling co-op from
fully OFF applies at the next screen change). On older engine builds,
relaunch after editing.

## Options

```
py netsync_bridge.py --port 49300              # different local port (update RelayUrl to match)
py netsync_bridge.py --relay ws://<ip>:7777    # different relay (e.g. a plaintext LAN test relay)
py netsync_bridge.py --insecure                # skip TLS cert verification (self-signed relays)
```

`py test_relay_roundtrip.py` proves the whole path without the game: it runs
a bridge, connects a fake host + guest through it to the real relay under a
throwaway session code, and checks packets arrive verbatim both ways.

## Troubleshooting

- **`relay connect ... failed` in `Memoria.log`** — the bridge isn't running,
  or `RelayUrl` doesn't match the bridge's port.
- **Bridge says `connection ... failed: ...getaddrinfo...`** — no internet /
  DNS; the relay hostname must resolve.
- **You connect but never pair** — the codes don't match (compare them,
  including the `ff9-` prefix), or the other player isn't connected yet. The
  relay waits 60 s for the second player, then both games retry automatically.
  After a crash it can take up to a minute for the old session to clear.
- **No relay at all?** The proven direct-LAN mode still works: leave
  `RelayUrl` empty and set `PeerAddress`/`Port` to the host's LAN IP instead
  (same WiFi, firewall allowed, VPNs off or LAN-sharing enabled).
