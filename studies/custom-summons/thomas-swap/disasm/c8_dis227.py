import struct, refkit
# MIPS R3000A disassembler built ONLY from the DLL's own decode table order (0x66c70).
NAMES = ["nop","sll","sra","srl","move","jalr","jr","mfhi","mthi","mflo","mtlo",
 "mult","multu","div","divu","add","addu","and","xor","srlv","sub","subu","nor","or",
 "sllv","slt","sltu","srav","addi","addiu","slti","sltiu","andi","ori","xori",
 "li(addiu)","li(ori)","lui","lb","lh","lwl","lw","lbu","lhu","lwr",
 "sb","sh","swl","sw","swr","j","jal","beq","bne","bgez","bltz","bltzal","bgezal",
 "blez","bgtz","b","swc2","lwc2","cfc2","ctc2","cop2","break","swc0?","swc1?","swc3?",
 "lwc0?","lwc1?","lwc3?","bc0f","bc1f","bc2f","bc3f","bc0t","bc1t","bc2t"]
REG=["zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
 "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"]
pe=refkit.load(); TB=0x66c70
ent=[]; i=0
while True:
    m,mt=struct.unpack_from("<II", pe.get_data(TB+i*0x38,8),0)
    if m==0: break
    ent.append((m,mt)); i+=1
def dec(w):
    for idx,(m,mt) in enumerate(ent):
        if (w&m)==mt: return idx
    return None
def walk(path):
    b=open(path,'rb').read(); n=struct.unpack_from("<h",b,0)[0]; p=2; pos=0x800; out=[]; ordn=0
    for c in range(n):
        ci,rc=struct.unpack_from("<hh",b,p); p+=4
        for j in range(rc):
            rid=struct.unpack_from("<b",b,p)[0]; info=struct.unpack_from("<b",b,p+1)[0]
            sz=struct.unpack_from("<h",b,p+2)[0]<<11; p+=4
            if rid==3: out.append((ordn,pos,sz))
            pos+=sz
            if rid==2 and info!=0: pos+=struct.unpack_from("<h",b,p)[0]<<11; p+=2
        ordn+=1
    return b,pos,out
b,endp,id3=walk(r"C:/gd/SCRATCH/summon-format/ef227.bytes")
print("ef227 len=%#x cursor=%#x  id3 images:"%(len(b),endp), [(o,hex(p),hex(s)) for o,p,s in id3])
for ordn,off,sz in id3:
    pay=b[off:off+sz]
    ptr=struct.unpack_from("<I",pay,0)[0]
    psx=0x801E7700 + (ordn&1)*0x5000
    hdr=(ptr&0xfffffff)-(psx&0xfffffff)
    progs=struct.unpack_from("<16I",pay,hdr+8)
    live=[(k,(v&0xfffffff)-(psx&0xfffffff)) for k,v in enumerate(progs) if v]
    print("chunk%d headerRel=%#x hdrwords=%s live programs=%s"%(ordn,hdr,
        struct.unpack_from("<2I",pay,hdr), [(k,hex(o)) for k,o in live]))
    for k,po in live[:1]:
        print("  --- disasm program %d @ image+%#x (first 40 instr) ---"%(k,po))
        for n in range(40):
            o=po+n*4
            w=struct.unpack_from("<I",pay,o)[0]
            idx=dec(w)
            nm=NAMES[idx] if idx is not None and idx<len(NAMES) else ("?%s"%idx)
            rs=(w>>21)&31; rt=(w>>16)&31; rd=(w>>11)&31; imm=w&0xffff
            simm=imm-0x10000 if imm&0x8000 else imm
            print("   +%04x  %08x  %-10s rs=%-4s rt=%-4s rd=%-4s imm=%d"%(o,w,nm,REG[rs],REG[rt],REG[rd],simm))
