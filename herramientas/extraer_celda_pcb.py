"""Extrae la Celda1 del monolito a un PCB propio (proyecto 'celda').
Uso: extract_celda_pcb.py monolito.kicad_pcb netlist_celda.net ids.json salida.kicad_pcb"""
import pcbnew,re,json,sys,collections
src,netf,idsf,dst=sys.argv[1:5]
ids=json.load(open(idsf)); NEWROOT,SHEET=ids["newroot"],ids["sheet"]
mm=pcbnew.ToMM; F=pcbnew.FromMM
b=pcbnew.LoadBoard(src)
nl=open(netf).read(); i=nl.index("(nets"); pin2net={}
for blk in re.split(r'\n\t\t\(net\n',nl[i:])[1:]:
    name=re.search(r'\(name "([^"]+)"\)',blk).group(1)
    for r,p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"',blk): pin2net[(r,p)]=name
S1=[f for f in b.GetFootprints() if f.GetSheetname()=="/Celda1/"]
others=[f for f in b.GetFootprints() if f.GetSheetname()!="/Celda1/"]
s1refs={f.GetReference() for f in S1}
# red antigua -> red nueva (por pad)
m1={}
for f in S1:
    for p in f.Pads():
        n=pin2net.get((f.GetReference(),p.GetNumber()))
        if p.GetNetname() and n: m1[p.GetNetname()]=n
micro={q.GetNetname() for fr in ("A1","U4","U5") for q in b.FindFootprintByReference(fr).Pads()}
micro.add("+12V"); micro.discard("GND"); micro.discard("+3.3V")
bb=[f.GetBoundingBox(False) for f in S1]
X0,X1=min(mm(r.GetX()) for r in bb),max(mm(r.GetRight()) for r in bb)
Y0,Y1=min(mm(r.GetY()) for r in bb),max(mm(r.GetBottom()) for r in bb)
inreg=lambda p,m=3:X0-m<=mm(p.x)<=X1+m and Y0-m<=mm(p.y)<=Y1+m
pos=lambda t:t.GetPosition() if t.GetClass()=="PCB_VIA" else t.GetStart()
# pads de otras huellas (no de la celda): el cobre que las toca no es de la celda
opads=[]
for f in others:
    for p in f.Pads():
        r=p.GetBoundingBox(); opads.append((r.GetX(),r.GetY(),r.GetRight(),r.GetBottom()))
def on_other_pad(p):
    return any(r[0]<=p.x<=r[2] and r[1]<=p.y<=r[3] for r in opads)
def inner_tree(net):
    cellpads=[(q,f) for f in S1 for q in f.Pads() if q.GetNetname()==net]
    if len(cellpads)<2: return []
    objs=[t for t in b.GetTracks() if t.GetNetname()==net]
    rects=[(q.GetBoundingBox().GetX(),q.GetBoundingBox().GetY(),q.GetBoundingBox().GetRight(),q.GetBoundingBox().GetBottom()) for q,f in cellpads]
    adj=collections.defaultdict(set); eo={}
    nk=lambda v:(v.x,v.y)
    for t in objs:
        if t.GetClass()=="PCB_VIA": continue
        a,c=nk(t.GetStart()),nk(t.GetEnd()); adj[a].add(c); adj[c].add(a); eo[frozenset((a,c))]=t
    pts=list(adj)
    for v in [t.GetPosition() for t in objs if t.GetClass()=="PCB_VIA"]:
        close=[w for w in pts if abs(w[0]-v.x)<20000 and abs(w[1]-v.y)<20000]
        for w1 in close:
            for w2 in close:
                if w1!=w2: adj[w1].add(w2)
    term=set()
    for r in rects:
        for w in pts:
            if r[0]-100000<=w[0]<=r[2]+100000 and r[1]-100000<=w[1]<=r[3]+100000: term.add(w)
    ch=True
    while ch:
        ch=False
        for v in list(adj):
            if len(adj[v])<=1 and v not in term:
                for u in list(adj[v]): adj[u].discard(v)
                del adj[v]; ch=True
    keep=[t for k,t in eo.items() if tuple(k)[0] in adj and tuple(k)[1] in adj]
    vk=[t for t in objs if t.GetClass()=="PCB_VIA" and any(abs(w[0]-t.GetPosition().x)<20000 and abs(w[1]-t.GetPosition().y)<20000 for w in adj)]
    return [t for t in keep+vk if inreg(pos(t))]
cellnets={p.GetNetname() for f in S1 for p in f.Pads() if p.GetNetname()}
keep=[]
for t in b.GetTracks():
    n=t.GetNetname()
    if not inreg(pos(t)) or n in micro: continue
    if n in ("GND","+3.3V"):
        if not inreg(pos(t),0.5): continue
        if on_other_pad(pos(t)) or (t.GetClass()!="PCB_VIA" and (on_other_pad(t.GetStart()) or on_other_pad(t.GetEnd()))): continue
        keep.append(t)
    elif n in cellnets: keep.append(t)
import math
def segd(p,a,c):
    dx,dy=c[0]-a[0],c[1]-a[1]; L=dx*dx+dy*dy
    t=0 if L==0 else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/L))
    return math.hypot(p[0]-(a[0]+t*dx),p[1]-(a[1]+t*dy))
others_t=[t for t in keep if t.GetNetname() not in ("GND","+3.3V")]
def shorts(v):
    c=(mm(v.GetPosition().x),mm(v.GetPosition().y)); r=mm(v.GetWidth(pcbnew.F_Cu))/2
    for t in others_t:
        if t.GetClass()=="PCB_VIA":
            if math.hypot(mm(t.GetPosition().x)-c[0],mm(t.GetPosition().y)-c[1])<r+mm(t.GetWidth(pcbnew.F_Cu))/2+0.2: return True
        elif t.GetLayer() in (pcbnew.F_Cu,pcbnew.In2_Cu,pcbnew.B_Cu):
            if segd(c,(mm(t.GetStart().x),mm(t.GetStart().y)),(mm(t.GetEnd().x),mm(t.GetEnd().y)))<r+mm(t.GetWidth())/2+0.2: return True
    return False
dropped=[t for t in keep if t.GetClass()=="PCB_VIA" and t.GetNetname() in ("GND","+3.3V") and shorts(t)]
dset={id(t) for t in dropped}; keep=[t for t in keep if id(t) not in dset]
print("vías de plano descartadas por cortocircuito con otra red:",len(dropped))
extra=[]
for n in sorted(micro & cellnets):
    if n in ("+12V",): continue
    extra+=inner_tree(n)
keep+=extra
keepids={id(t) for t in keep}
# apuntes (objeto, nombre de red nueva) antes de borrar
assign=[]
for f in S1:
    for p in f.Pads():
        n=pin2net.get((f.GetReference(),p.GetNumber())); assign.append((p,n or ""))
for t in keep:
    n=t.GetNetname(); assign.append((t,m1.get(n,n)))
keepset=set(map(id,keep))
# borrar: huellas ajenas, cobre no conservado, dibujos, zonas
draws=list(b.GetDrawings()); alltr=list(b.GetTracks())
for f in others: b.Remove(f)
for t in list(b.GetTracks()):
    if id(t) not in keepset:
        # los wrappers cambian: se compara por clave geométrica
        pass
keys={ (("v",t.GetPosition().x,t.GetPosition().y,t.GetNetname()) if t.GetClass()=="PCB_VIA" else ("t",t.GetLayer(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetNetname())) for t in keep}
nrem=0
for t in alltr:
    k=("v",t.GetPosition().x,t.GetPosition().y,t.GetNetname()) if t.GetClass()=="PCB_VIA" else ("t",t.GetLayer(),t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y,t.GetNetname())
    if k not in keys: b.Remove(t); nrem+=1
for d in draws: b.Remove(d)
# redes nuevas y asignación por nombre (tras borrar todo lo ajeno)
trk_new={}
for o,n in assign:
    if n and not b.FindNet(n): b.Add(pcbnew.NETINFO_ITEM(b,n))
for o,n in assign:
    o.SetNet(b.FindNet(n) if n else b.FindNet(""))
for f in S1:
    k=f.GetPath().AsString().split("/")[-1]
    f.SetPath(pcbnew.KIID_PATH("/%s/%s/%s"%(NEWROOT,SHEET,k)))
    f.SetSheetname("/Celda/"); f.SetSheetfile("celda_circuito.kicad_sch")
# contorno y planos
M=2.0
ex=[];ey=[]
for f in S1:
    for p in f.Pads():
        r=p.GetBoundingBox(); ex+=[mm(r.GetX()),mm(r.GetRight())]; ey+=[mm(r.GetY()),mm(r.GetBottom())]
for t in keep:
    for q in ((t.GetPosition(),) if t.GetClass()=="PCB_VIA" else (t.GetStart(),t.GetEnd())):
        ex.append(mm(q.x)); ey.append(mm(q.y))
x0,x1,y0,y1=min(ex)-M,max(ex)+M,min(ey)-M,max(ey)+M
pts=[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
for a,c in zip(pts,pts[1:]):
    s=pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(pcbnew.VECTOR2I(F(a[0]),F(a[1]))); s.SetEnd(pcbnew.VECTOR2I(F(c[0]),F(c[1]))); s.SetWidth(F(0.05)); b.Add(s)
for z in b.Zones():
    ol=z.Outline().Outline(0)
    corners=[(x0+0.3,y0+0.3),(x1-0.3,y0+0.3),(x1-0.3,y1-0.3),(x0+0.3,y1-0.3)]
    # reescribir los 4 vértices del contorno del plano
    for i in range(ol.PointCount()):
        ol.SetPoint(i,pcbnew.VECTOR2I(F(corners[i][0]),F(corners[i][1])))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(dst)
print("huellas:",len(S1),"| cobre conservado:",len(keep),"(de ellos árbol interno micro:",len(extra),") | borrados:",nrem,"| contorno %.1f x %.1f mm"%(x1-x0,y1-y0))
