#!/usr/bin/env python3
"""Replica por traslación la celda dorada (celda/celda.kicad_pcb) en el PCB de una placa.

Uso: replicar_celdas_pcb.py {master|slave} [--cols N] [--sep MM] [--origen X,Y] [-o salida.kicad_pcb]

Requisitos: el esquemático raíz de la placa ya generado (herramientas/generar_raiz.py).
Hace, por cada celda de la placa:
  - copia huellas, pistas, vías y rótulos de la celda dorada desplazados (sin giros ni espejos);
  - renumera referencias (+100 por celda), enlaza cada huella a su símbolo del esquemático raíz
    (misma ruta que genera generar_raiz.py) y toma la red de cada pad del netlist de la placa;
  - traduce las redes de pistas y vías por pad (las redes de interfaz pasan a ser las del canal).
Además crea un plano GND (In1) y un plano +3,3 V (In2) únicos del tamaño de la placa y un contorno
rectangular provisional. NO hace tiras de +12 V: las conexiones de +12 V de los BTS se dejan sin
rutear a propósito (se dibujan al final, con todo armado) y el script lo avisa al terminar.
Las huellas de la raíz (ESP32, MCP, bloque de poder, conector) se cargan de las bibliotecas según el
esquemático y se dejan en una franja provisional bajo las celdas, ya enlazadas y con sus redes.
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
    "master": dict(cells=[1, 2, 3], cols=3),
    "slave": dict(cells=[4, 5, 6, 7], cols=2),
}
GLOBAL_NETS = ("GND", "+3.3V", "+12V")
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
    ap.add_argument("--cols", type=int, help="celdas por fila (por defecto: master 3, slave 2)")
    ap.add_argument("--sep", type=float, default=3.0, help="separación entre celdas en mm (por defecto 3)")
    ap.add_argument("--origen", default="10,10", help="esquina superior izquierda de la primera celda, mm")
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

    stats = collections.Counter()
    for idx, k in enumerate(cfg["cells"]):
        off = 100 * (k - 1)
        sheet = str(uuid.uuid5(uuid.UUID(root), "Celda%d" % k))
        dx = F(tx0 + (idx % cols) * px - x0)
        dy = F(ty0 + (idx // cols) * py - y0)
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

    # --- huellas de la raíz en una franja bajo las celdas (colocación provisional) ----
    rows = (len(cfg["cells"]) + cols - 1) // cols
    ncols = min(cols, len(cfg["cells"]))
    width = ncols * px - a.sep
    x, y, rowh = tx0, ty0 + rows * py - a.sep + 6.0, 0.0
    maxx = tx0 + width
    parts = sorted(read_root_parts(f"{boarddir}/{proj}.kicad_sch"),
                   key=lambda q: (PRIORIDAD.index(q[0]) if q[0] in PRIORIDAD else 99, q[0]))
    for ref, val, fpid, suid, extra in parts:
        fp = load_footprint(fpid)
        fp.SetReference(ref)
        fp.SetValue(val)
        for f in fp.GetFields():      # Datasheet y Description como en el símbolo (evita avisos de paridad)
            if f.GetName() in extra:
                f.SetText(extra[f.GetName()])
        fp.SetExcludedFromBOM(not extra["in_bom"])
        fp.SetPath(pcbnew.KIID_PATH("/%s/%s" % (root, suid)))
        r = fp.GetBoundingBox(False)
        w, h = mm(r.GetWidth()), mm(r.GetHeight())
        if x > tx0 and x + w > tx0 + max(width, 100.0):
            x, y, rowh = tx0, y + rowh + 3.0, 0.0
        fp.Move(pcbnew.VECTOR2I(F(x - mm(r.GetX())), F(y - mm(r.GetY()))))
        maxx = max(maxx, x + w)
        x, rowh = x + w + 3.0, max(rowh, h)
        for p in fp.Pads():
            key = (ref, p.GetNumber())
            p.SetNet(get_net(pin2net[key]) if key in pin2net else get_net(""))
        b.Add(fp)
        stats["huellas de la raíz"] += 1
    strip_bottom = y + rowh

    # --- contorno provisional y planos únicos -----------------------------------
    m = 2.0
    bx0, by0 = tx0 - m, ty0 - m
    bx1 = maxx + m
    by1 = strip_bottom + m
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
    print("Aviso: las conexiones de +12 V (BTS) quedan sin rutear a propósito. Las huellas de la raíz "
          "están en una franja provisional bajo las celdas: colócalas a mano.")


if __name__ == "__main__":
    main()
