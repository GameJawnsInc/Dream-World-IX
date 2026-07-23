import refkit
pe = refkit.load(); base=refkit.image_base(pe)
fns = refkit.functions(pe)
hits = refkit.xrefs_to(pe, 0x220830, fns)
print("refs to summonModels 0x220830:")
for h in hits: print(" ", hex(h[0]), h[1], h[2])
print()
print("strings with 'Summon':")
for s in refkit.find_strings(pe, "Summon"): print(" ", s)
