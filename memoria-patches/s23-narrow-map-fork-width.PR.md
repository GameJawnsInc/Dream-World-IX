# PR draft — Fix widescreen letterbox masking for custom field ids

> **Status: DRAFT, not submitted.** Hold until ready to go public. Pairs with
> `memoria-patches/s23-narrow-map-fork-width.patch` (the actual diff, applies on top of base
> `6b8bb2d5`). In-game proven 2026-06-14 on a forked narrow field; deployed engine reverted to
> F6-only afterward (engine-independence). See memory `project-ff9-narrow-map-fork-letterbox`.

**Target:** Memoria — `Assembly-CSharp/Global/Field/Map/NarrowMapList.cs`

---

## Title

`Fix widescreen letterbox masking for custom field ids (fall back to BG width)`

## Body

**Problem.** Custom field ids (FieldCreator output, modded `FieldScene` entries) render off-screen
actors *over* the letterbox/pillarbox bars on narrow maps. A stock narrow field hides them; a custom
one with the same narrow BG doesn't.

**Cause.** `NarrowMapList.MapWidth()` is keyed on the field id via the hardcoded `MapWidthList`. Ids
not in the table fall through to a `500` ("wide enough") default, so a narrow custom BG is treated as
widescreen-capable — the field camera renders full-width and `WidescreenSupport` is never disabled
for it.

**Fix.** When the id isn't in the table, fall back to the *loaded BG's actual width*
(`GetCurrentBgCamera().w`, PSX px — the same unit as the table) before defaulting to 500. Real ids
are unaffected: their `MapWidthList` entry returns first.

**Testing.** In-game on a narrow custom field: off-screen actors now mask correctly. Verified real
fields (e.g. Ice Cavern entrance) and wide/scrolling fields are unchanged. 1 file, no new types.

## Diff

```diff
         foreach (Int32[] entry in MapWidthList)
             if (entry[0] == mapId)
                 return entry[1];
 
+        // Custom / FieldCreator field ids aren't in MapWidthList; the 500 default treats a narrow
+        // custom BG as widescreen-capable, so off-screen actors draw over the letterbox bars. Fall
+        // back to the loaded BG's actual width so narrow detection works for them too. (Real ids
+        // never reach here — their MapWidthList entry returns above.)
+        if (mapId == FF9StateSystem.Common.FF9.fldMapNo)
+        {
+            try
+            {
+                BGCAM_DEF cam = PersistenSingleton<EventEngine>.Instance?.fieldmap?.GetCurrentBgCamera();
+                if (cam != null && cam.w > 0)
+                    return cam.w;
+            }
+            catch { /* scene not loaded yet → fall through to the default */ }
+        }
+
         return 500;
     }
```

## Notes for a reviewer

- The `try/catch` is a boot-safety guard for the pre-load window (`GetCurrentBgCamera()` dereferences
  `scene`, which can be null very early). A maintainer who dislikes a broad catch could swap it for an
  explicit `scene != null` check — behavior is identical.
- `mapId == FF9StateSystem.Common.FF9.fldMapNo` ensures we only read the scene width for the *current*
  map. Every call site passes the current id today; this just keeps it safe if that ever changes.
- Generalizes: any engine behavior gated on the real `fldMapNo` (the per-camera `RestrictedCams`
  tuning, per-map offset fixes, etc.) is lost on a non-real id. This PR closes the most visible case
  (narrow-map width); the same fallback pattern could cover the others if wanted.
