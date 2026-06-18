<!--
Thanks for contributing to Dream World IX! Keep this short — a few lines per section is plenty.
-->

### Summary

What this PR does, in a sentence or two, and why.

### What changed

- (bullet the notable changes)

### Testing done

How you verified it. The offline suite runs from the package directory:

```
cd ff9mapkit
py -m pytest -n 6
```

- [ ] `py -m pytest` passes (byte-level tests skip until `extract-templates` is run; pure-logic
      tests always run)
- [ ] Where it applies, the change was checked in-game (build → deploy → playtest)

### Checklist

- [ ] **No FINAL FANTASY IX game bytes are included** — no `*.eb.bytes` / `*.bgx` /
      `*.bgi.bytes` / `*.mes` or decompiled field scripts. (See
      [PROVENANCE](ff9mapkit/docs/PROVENANCE.md) and the [DISCLAIMER](DISCLAIMER.md).)
- [ ] Docs updated if behavior or commands changed.
