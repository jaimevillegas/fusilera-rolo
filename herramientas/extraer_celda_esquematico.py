"""Crea el proyecto 'celda' (esquemático) a partir de la Celda1 del monolito.
Uso: build_celda_sch.py repo_dir salida_dir"""
import re,sys,uuid,json,os
repo,out=sys.argv[1:3]
os.makedirs(out,exist_ok=True)
OLDROOT="6451a64b-df92-4e59-b073-88385097038f"; S1="7ac4191c-7220-47a0-be32-4085e2ecb618"
NEWROOT=str(uuid.uuid4())
sub=open(f"{repo}/celda4.kicad_sch").read()
def balanced(s,i):
    d=0
    for j in range(i,len(s)):
        if s[j]=="(": d+=1
        elif s[j]==")":
            d-=1
            if d==0: return j+1
res=[];pos=0;n=0
while True:
    i=sub.find("(instances",pos)
    if i<0: res.append(sub[pos:]); break
    j=balanced(sub,i); blk=sub[i:j]
    m=re.search(r'\(path "/%s/%s"\s*\(reference "([^"]+)"\)\s*\(unit (\d+)\)'%(OLDROOT,S1),blk)
    assert m,blk[:200]
    new='(instances\n\t\t\t(project "celda"\n\t\t\t\t(path "/%s/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit %s)\n\t\t\t\t)\n\t\t\t)\n\t\t)'%(NEWROOT,S1,m.group(1),m.group(2))
    res.append(sub[pos:i]); res.append(new); pos=j; n+=1
open(f"{out}/celda_circuito.kicad_sch","w").write("".join(res))
print("instancias reescritas:",n)
root=open(f"{repo}/fusilera 24 canales.kicad_sch").read()
sh=[m.group(0) for m in re.finditer(r'\t\(sheet\n[\s\S]*?\n\t\)\n',root) if S1 in m.group(0)][0]
dy=38.1-190.5
def shift(m): return "(at %s %s%s)"%(m.group(1),("%.2f"%(float(m.group(2))+dy)).rstrip("0").rstrip("."),m.group(3) or "")
sh=re.sub(r'\(at ([\d.]+) ([\d.]+)( \d+)?\)',shift,sh)
sh=sh.replace('"Sheetname" "Celda1"','"Sheetname" "Celda"').replace("celda4.kicad_sch","celda_circuito.kicad_sch")
i=sh.index("(instances"); sh=sh[:i]+'(instances\n\t\t\t(project "celda"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(page "2")\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n'%NEWROOT
pins=re.findall(r'\(pin "([^"]+)" (\w+)\s*\(at ([\d.]+) ([\d.]+) (\d+)',sh)
fm=lambda v:("%.2f"%v).rstrip("0").rstrip(".")
extra=""
for name,typ,x,y,ang in pins:
    x=float(x);y=float(y); left=(ang=="180"); xs=x-2.54 if left else x+2.54
    extra+='\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "%s")\n\t)\n'%(fm(xs),fm(y),fm(x),fm(y),uuid.uuid4())
    extra+='\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s bottom)\n\t\t)\n\t\t(uuid "%s")\n\t)\n'%(name,fm(xs),fm(y),180 if left else 0,"right" if left else "left",uuid.uuid4())
hdr='(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n\t(generator_version "10.0")\n\t(uuid "%s")\n\t(paper "A3")\n\t(lib_symbols)\n'%NEWROOT
tail='\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n'
open(f"{out}/celda.kicad_sch","w").write(hdr+sh+extra+tail)
p=json.load(open(f"{repo}/fusilera 24 canales.kicad_pro"))
p["sheets"]=[[NEWROOT,"Raíz"],[S1,"Celda"]]
p["meta"]["filename"]="celda.kicad_pro"
json.dump(p,open(f"{out}/celda.kicad_pro","w"),indent=2,ensure_ascii=False)
json.dump({"newroot":NEWROOT,"sheet":S1},open(f"{out}/ids.json","w"))
print("raíz nueva",NEWROOT)
