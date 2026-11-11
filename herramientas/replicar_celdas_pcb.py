#!/usr/bin/env python3
"""Replica por traslación la celda dorada (celda/celda.kicad_pcb) en el PCB de una placa.

Uso: replicar_celdas_pcb.py {master|slave} [--cols N] [--sep MM] [--origen X,Y] [-o salida.kicad_pcb]

Requisitos: el esquemático raíz de la placa ya generado (herramientas/generar_raiz.py).
Hace, por cada celda de la placa:
  - copia huellas, pistas, vías y rótulos de la celda dorada desplazados (sin giros ni espejos);
  - renumera referencias (+100 por celda), enlaza cada huella a su símbolo del esquemático raíz
    (misma ruta que genera generar_raiz.py) y toma la red de cada pad del netlist de la placa;
  - traduce las redes de pistas y vías por pad (las redes de interfaz pasan a ser las del canal).
Con una sola columna (por defecto) la celda 1 va abajo y las demás encima. Las tiras de +12 V de la celda
dorada (pistas de 9 mm en F.Cu) se unen entre celdas, bajan hasta un tronco inferior que cierra las dos
tiras y alimenta el borne `J1`; `J2` (GND) se coloca a su izquierda. Con `--cols` mayor que 1 las tiras
quedan sueltas (el script avisa).
Además crea un plano GND (In1) y un plano +3,3 V (In2) únicos del tamaño de la placa y un contorno
rectangular provisional alrededor de todo el contenido (`--margen`).
Las huellas de la raíz (ESP32, MCP, bloque de poder, conector) se cargan de las bibliotecas según el
esquemático y se dejan en una franja provisional sobre las celdas, ya enlazadas y con sus redes.
"""
import argparse
import collections
import os
import re
import subprocess
import sys
import tempfile
import uuid

import pcbnew

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARDS = {
    "master": dict(cells=[1, 2, 3], cols=1),
    "slave": dict(cells=[4, 5, 6, 7], cols=1),
}
GLOBAL_NETS = ("GND", "+3.3V", "+12V")
TRONCO_BAJADA = 17.15      # mm entre el fondo de la tira de la celda inferior y el eje del tronco con J1
TRONCO_CHAFLAN = 3.0       # mm del chaflán entre el tronco y la tira derecha
BORNES_HOLGURA = 1.1       # mm entre los anillos de J1 y J2
mm, F = pcbnew.ToMM, pcbnew.FromMM


def read_pin2net(sch):
    """pin -> nombre de red según el netlist del esquemático (kicad-cli)."""
    with tempfile.TemporaryDirectory() as tmp:
        net = os.path.join(tmp, "n.net")
        subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch],
                       check=True, capture_output=True)
        text = open(net).read()
    i = text.index("(nets")
    pin2net = {}
    for blk in re.split(r"\n\t\t\(net\n", text[i:])[1:]:
        name = re.search(r'\(name "([^"]+)"\)', blk).group(1)
        for r, p in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"', blk):
            pin2net[(r, p)] = name
    return pin2net


def dup(item):
    """Duplicate() según el tipo de objeto (algunos aceptan addToParentGroup y otros no)."""
    try:
        return item.Duplicate(False)
    except TypeError:
        return item.Duplicate()


def new_ref(ref, off):
    m = re.match(r"^(\D+)(\d+)$", ref)
    return "%s%0*d" % (m.group(1), len(m.group(2)), int(m.group(2)) + off)


def balanced(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j + 1
    raise ValueError("paréntesis sin cerrar")


def read_root_parts(sch):
    """Símbolos de la raíz con huella: [(ref, valor, huella, uuid, extras)] (sin símbolos de alimentación)."""
    text = open(sch).read()
    parts, i = [], 0
    while True:
        i = text.find("\n\t(symbol\n", i)
        if i < 0:
            return parts
        s = i + 1
        e = balanced(text, s)
        blk = text[s:e]
        i = e
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
        fp = re.search(r'\(property "Footprint" "([^"]*)"', blk).group(1)
        if ref.startswith("#") or not fp:
            continue
        val = re.search(r'\(property "Value" "([^"]*)"', blk).group(1)
        uid = re.search(r'\(uuid "([0-9a-f-]+)"\)', blk).group(1)
        extra = {k: v.replace('\\"', '"') for k, v in re.findall(r'\(property "(Datasheet|Description)" "((?:[^"\\]|\\.)*)"', blk)}
        extra["in_bom"] = "(in_bom yes)" in blk
        parts.append((ref, val, fp, uid, extra))


def load_footprint(fpid):
    nick, name = fpid.split(":", 1)
    lib = f"{REPO}/libs/{nick}.pretty" if nick == "fusilera" else f"/usr/share/kicad/footprints/{nick}.pretty"
    fp = pcbnew.FootprintLoad(lib, name)
    if fp is None:
        sys.exit(f"No se encontró la huella {fpid} en {lib}")
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    return fp


PRIORIDAD = ["A1", "U4", "U5", "J10", "U7", "U6", "J1", "J2"]


def content_bbox(board):
    """Caja de huellas, pistas y vías (sin Edge.Cuts) en mm: (x0, y0, x1, y1)."""
    xs, ys = [], []
    for f in board.GetFootprints():
        r = f.GetBoundingBox(False)
        xs += [mm(r.GetX()), mm(r.GetRight())]
        ys += [mm(r.GetY()), mm(r.GetBottom())]
    for t in board.GetTracks():
        r = t.GetBoundingBox()
        xs += [mm(r.GetX()), mm(r.GetRight())]
        ys += [mm(r.GetY()), mm(r.GetBottom())]
    return min(xs), min(ys), max(xs), max(ys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", choices=sorted(BOARDS))
    ap.add_argument("--cols", type=int, help="celdas por fila (por defecto 1: las celdas van en columna)")
    ap.add_argument("--sep", type=float, default=3.0, help="separación entre celdas en mm (por defecto 3)")
    ap.add_argument("--origen", default="10,10", help="esquina superior izquierda de la primera celda, mm")
    ap.add_argument("--margen", type=float, default=2.0, help="margen del contorno alrededor del contenido, mm (por defecto 2)")
    ap.add_argument("-o", dest="out")
    ap.add_argument("--forzar", action="store_true", help="sobrescribir un PCB que ya existe (pierde el trabajo manual)")
    a = ap.parse_args()

    cfg = BOARDS[a.board]
    proj = "placa-" + a.board
    boarddir = f"{REPO}/{proj}"
    out = a.out or f"{boarddir}/{proj}.kicad_pcb"
    if os.path.exists(out) and not a.forzar:
        sys.exit(f"{out} ya existe: regenerarlo borra el trabajo manual (colocación de la raíz, rutas). Usa --forzar si es lo que quieres.")
    cols = a.cols or cfg["cols"]
    tx0, ty0 = (float(v) for v in a.origen.split(","))
    root = str(uuid.uuid5(uuid.NAMESPACE_URL, "fusilera/" + proj))
    pin2net = read_pin2net(f"{boarddir}/{proj}.kicad_sch")

    src = pcbnew.LoadBoard(f"{REPO}/celda/celda.kicad_pcb")      # fuente de verdad (no se modifica)
    b = pcbnew.LoadBoard(f"{REPO}/celda/celda.kicad_pcb")        # hereda configuración y apilado
    # las listas se recogen antes de borrar nada (si no, los envoltorios SWIG dejan de ser iterables)
    viejos = list(b.Zones()) + list(b.GetTracks()) + list(b.GetDrawings()) + list(b.GetFootprints())
    for item in viejos:
        b.Remove(item)

    x0, y0, x1, y1 = content_bbox(src)
    cw, ch = x1 - x0, y1 - y0
    px, py = cw + a.sep, ch + a.sep
    print(f"celda dorada: contenido {cw:.1f} x {ch:.1f} mm; paso {px:.1f} x {py:.1f} mm; {cols} columnas")

    # pad de referencia de cada red de la celda dorada (para traducir pistas y vías)
    net_pad = {}
    for f in src.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() and p.GetNetname() not in net_pad:
                net_pad[p.GetNetname()] = (f.GetReference(), p.GetNumber())

    nets = {}

    def get_net(name):
        if name not in nets:
            n = b.FindNet(name)
            if n is None or name == "":
                n = pcbnew.NETINFO_ITEM(b, name)
                b.Add(n)
            nets[name] = n
        return nets[name]

    def add_track(x_a, y_a, x_b, y_b, width):
        """Pista de +12 V en F.Cu (coordenadas en mm)."""
        t = pcbnew.PCB_TRACK(b)
        t.SetLayer(pcbnew.F_Cu)
        t.SetStart(pcbnew.VECTOR2I(F(x_a), F(y_a)))
        t.SetEnd(pcbnew.VECTOR2I(F(x_b), F(y_b)))
        t.SetWidth(F(width))
        t.SetNet(get_net("+12V"))
        b.Add(t)

    # tiras verticales de +12 V de la celda dorada: x -> (y_sup, y_inf, ancho)
    tiras = {}
    for t in src.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "+12V" and mm(t.GetWidth()) >= 5:
            xs = round(mm(t.GetStart().x), 3)
            ys = [mm(t.GetStart().y), mm(t.GetEnd().y)]
            lo, hi, w = tiras.get(xs, (min(ys), max(ys), mm(t.GetWidth())))
            tiras[xs] = (min(lo, *ys), max(hi, *ys), w)
    if tiras and cols != 1:
        print("Aviso: las tiras de +12 V solo se unen entre celdas con una sola columna (--cols 1); "
              "con más columnas las celdas quedan con sus tiras sueltas.")

    # --- huellas de la raíz: se cargan ya y se colocan en una franja sobre las celdas ----
    parts = sorted(read_root_parts(f"{boarddir}/{proj}.kicad_sch"),
                   key=lambda q: (PRIORIDAD.index(q[0]) if q[0] in PRIORIDAD else 99, q[0]))
    raiz = []
    for ref, val, fpid, suid, extra in parts:
        fp = load_footprint(fpid)
        fp.SetReference(ref)
        fp.SetValue(val)
        for f in fp.GetFields():      # Datasheet y Description como en el símbolo (evita avisos de paridad)
            if f.GetName() in extra:
                f.SetText(extra[f.GetName()])
        fp.SetExcludedFromBOM(not extra["in_bom"])
        fp.SetPath(pcbnew.KIID_PATH("/%s/%s" % (root, suid)))
        for p in fp.Pads():
            key = (ref, p.GetNumber())
            p.SetNet(get_net(pin2net[key]) if key in pin2net else get_net(""))
        raiz.append(fp)
    bornes = [f for f in raiz if f.GetReference() in ("J1", "J2")] if tiras and cols == 1 else []
    franja = [f for f in raiz if f not in bornes]
    # empaquetado por filas; el alto total decide dónde empiezan las celdas
    pos, x, y, rowh = [], tx0, 0.0, 0.0
    ancho_franja = max(cw, 100.0)
    for fp in franja:
        r = fp.GetBoundingBox(False)
        w, h = mm(r.GetWidth()), mm(r.GetHeight())
        if x > tx0 and x + w > tx0 + ancho_franja:
            x, y, rowh = tx0, y + rowh + 3.0, 0.0
        pos.append((fp, x - mm(r.GetX()), y - mm(r.GetY())))
        x, rowh = x + w, max(rowh, h)
        x += 3.0
    alto_franja = y + rowh if franja else 0.0
    celdas_y0 = ty0 + (alto_franja + 6.0 if franja else 0.0)
    for fp, ox, oy in pos:
        fp.Move(pcbnew.VECTOR2I(F(ox), F(oy + ty0)))
        b.Add(fp)

    stats = collections.Counter()
    n_celdas = len(cfg["cells"])
    celda_dy = {}      # índice de celda -> desplazamiento en y (mm)
    dx_col = None
    for idx, k in enumerate(cfg["cells"]):
        off = 100 * (k - 1)
        sheet = str(uuid.uuid5(uuid.UUID(root), "Celda%d" % k))
        fila = n_celdas - 1 - idx if cols == 1 else idx // cols    # en columna, la celda 1 va abajo
        dx_mm = tx0 + (idx % cols) * px - x0
        dy_mm = celdas_y0 + fila * py - y0
        celda_dy[idx], dx_col = dy_mm, dx_mm
        dx, dy = F(dx_mm), F(dy_mm)
        mv = pcbnew.VECTOR2I(dx, dy)

        def cell_net(gname):
            if gname in GLOBAL_NETS or gname == "":
                return gname
            ref, pad = net_pad[gname]
            return pin2net[(new_ref(ref, off), pad)]

        for f in src.GetFootprints():
            nf = pcbnew.Cast_to_FOOTPRINT(dup(f))
            nr = new_ref(f.GetReference(), off)
            nf.SetReference(nr)
            nf.Move(mv)
            symuuid = f.GetPath().AsString().split("/")[-1]
            nf.SetPath(pcbnew.KIID_PATH("/%s/%s/%s" % (root, sheet, symuuid)))
            nf.SetSheetname("/Celda%d/" % k)
            nf.SetSheetfile("celda_circuito.kicad_sch")
            b.Add(nf)
            for p in nf.Pads():
                key = (nr, p.GetNumber())
                p.SetNet(get_net(pin2net[key]) if key in pin2net else get_net(""))
            stats["huellas"] += 1
        for t in src.GetTracks():
            cls = t.GetClass()
            if cls == "PCB_VIA":
                nt = pcbnew.Cast_to_PCB_VIA(dup(t))
            elif cls == "PCB_ARC":
                nt = pcbnew.Cast_to_PCB_ARC(dup(t))
            else:
                nt = pcbnew.Cast_to_PCB_TRACK(dup(t))
            nt.Move(mv)
            nt.SetNet(get_net(cell_net(t.GetNetname())))
            b.Add(nt)
            stats["vías" if cls == "PCB_VIA" else "pistas"] += 1
        for d in src.GetDrawings():
            if d.GetLayer() == pcbnew.Edge_Cuts:
                continue
            cls = d.GetClass()
            if cls == "PCB_TEXT":
                nd = pcbnew.Cast_to_PCB_TEXT(dup(d))
            elif cls == "PCB_SHAPE":
                nd = pcbnew.Cast_to_PCB_SHAPE(dup(d))
            else:
                continue
            nd.Move(mv)
            b.Add(nd)
            stats["rótulos"] += 1

    # --- tiras de +12 V: uniones entre celdas, tronco inferior y bornes J1/J2 -----------
    if tiras and cols == 1:
        for xs, (ys0, ys1, w) in sorted(tiras.items()):
            for idx in range(n_celdas - 1):           # idx + 1 queda justo encima de idx
                add_track(xs + dx_col, ys1 + celda_dy[idx + 1], xs + dx_col, ys0 + celda_dy[idx], w)
                stats["uniones de +12 V"] += 1
        xl, xr = min(tiras), max(tiras)
        ybase = max(v[1] for v in tiras.values()) + celda_dy[0]    # fondo de la tira de la celda inferior
        ytr = ybase + TRONCO_BAJADA
        w = tiras[xl][2]
        add_track(xl + dx_col, ybase, xl + dx_col, ytr, w)
        add_track(xl + dx_col, ytr, xr + dx_col - TRONCO_CHAFLAN, ytr, w)
        add_track(xr + dx_col - TRONCO_CHAFLAN, ytr, xr + dx_col, ytr - TRONCO_CHAFLAN, w)
        add_track(xr + dx_col, ybase, xr + dx_col, ytr - TRONCO_CHAFLAN, w)
        stats["pistas de tronco de +12 V"] += 4
        j1 = next((f for f in bornes if f.GetReference() == "J1"), None)
        if pin2net.get(("J1", "1")) not in (None, "+12V"):
            print("Aviso: J1 está en la red %s (hay fusible F1 entre el borne y las tiras): el tronco de +12 V que dibuja "
                  "este script toca el pad de J1 y dará un corto; hay que partir el cobre en KiCad." % pin2net[("J1", "1")])
        j2 = next((f for f in bornes if f.GetReference() == "J2"), None)
        if j1 is not None:
            j1.SetPosition(pcbnew.VECTOR2I(F(xl + dx_col), F(ytr)))
            b.Add(j1)
        if j2 is not None:
            r1 = max(mm(p.GetSizeX()) for p in j1.Pads()) / 2 if j1 is not None else 6.4
            r2 = max(mm(p.GetSizeX()) for p in j2.Pads()) / 2
            j2.SetPosition(pcbnew.VECTOR2I(F(xl + dx_col - (r1 + r2 + BORNES_HOLGURA)), F(ytr)))
            b.Add(j2)
    stats["huellas de la raíz"] = len(raiz)

    # --- contorno provisional y planos únicos -----------------------------------
    bxa, bya, bxb, byb = content_bbox(b)
    m = a.margen
    bx0, by0, bx1, by1 = bxa - m, bya - m, bxb + m, byb + m
    pts = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1), (bx0, by0)]
    for p, q in zip(pts, pts[1:]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(pcbnew.VECTOR2I(F(p[0]), F(p[1])))
        s.SetEnd(pcbnew.VECTOR2I(F(q[0]), F(q[1])))
        s.SetWidth(F(0.05))
        b.Add(s)
    for z in src.Zones():
        nz = pcbnew.Cast_to_ZONE(dup(z))
        ol = nz.Outline().Outline(0)
        c = [(bx0 + 0.3, by0 + 0.3), (bx1 - 0.3, by0 + 0.3), (bx1 - 0.3, by1 - 0.3), (bx0 + 0.3, by1 - 0.3)]
        for i in range(ol.PointCount()):
            ol.SetPoint(i, pcbnew.VECTOR2I(F(c[i][0]), F(c[i][1])))
        nz.SetNet(get_net(z.GetNetname()))
        b.Add(nz)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(out)
    print(f"{out}: " + ", ".join(f"{v} {k}" for k, v in stats.items())
          + f"; contorno {bx1 - bx0:.1f} x {by1 - by0:.1f} mm")
    if not (tiras and cols == 1):
        print("Aviso: sin tiras de +12 V; las conexiones de +12 V de los BTS quedan sin rutear.")
    print("Las huellas de la raíz están en una franja provisional sobre las celdas: colócalas a mano.")


if __name__ == "__main__":
    main()
