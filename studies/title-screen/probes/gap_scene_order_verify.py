import re
MAIN = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data\mainData"
data = open(MAIN, "rb").read()
# Extract all "Assets/Scenes/....unity" length-prefixed strings in the whole file, in file order
pat = re.compile(rb'Assets/Scenes/[A-Za-z0-9_/\-]+\.unity')
seen = []
for m in pat.finditer(data):
    seen.append((m.start(), m.group().decode()))
print("=== All 'Assets/Scenes/*.unity' occurrences in file order ===")
for off, s in seen:
    print(f"  0x{off:04x} ({off})  {s}")
print()
print("=== region 0x7ee0-0x8020 hexdump (ascii) ===")
region = data[0x7ee0:0x8020]
ascii_str = ''.join(chr(b) if 32<=b<127 else '.' for b in region)
print(ascii_str)
