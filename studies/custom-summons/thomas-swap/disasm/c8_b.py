import refkit
pe=refkit.load()
fns=refkit.functions(pe)
# exact pdata entries near the regions of interest
for lo,hi in fns:
    if 0xd100 <= lo <= 0xd300 or 0xe180 <= lo <= 0xe400 or 0xec00 <= lo <= 0xef00:
        print("pdata entry %05x..%05x"%(lo,hi))
