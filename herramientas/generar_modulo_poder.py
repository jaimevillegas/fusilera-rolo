#!/usr/bin/env python3
"""Genera el proyecto `modulo-poder/`: el bloque de poder de la slave como placa aparte.

Uso: generar_modulo_poder.py [directorio_salida]   (por defecto `modulo-poder/` en la raíz del repositorio)

Entrada de 12 V de carro por bornes M3 -> fusible -> NTC limitador de corriente de arranque -> diodo de
polaridad inversa -> TVS + condensadores de entrada (incluido uno de 10000 uF para aguantar las caídas de
tensión del arranque) -> buck LM5164 de 5 V -> LDO AP2112K de 3,3 V. Sale por una regleta JST XH de 5 pines
(5 V, GND, 3,3 V, GND, PGOOD).

Crea el esquemático (cableado solo por etiquetas, las redes salen del netlist del bloque de la slave), el
proyecto y un PCB de dos capas con las huellas dispersas fuera de cualquier contorno: SIN pistas, SIN contorno y
SIN planos (el cobre se hace a mano). Si el PCB ya existe no lo sobrescribe (usa --forzar).
"""
import json
import math
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generar_raiz as g  # noqa: E402

REPO = g.REPO
PROJ = "modulo-poder"
ROOT = str(uuid.uuid5(uuid.NAMESPACE_URL, "fusilera/" + PROJ))
fm, uid = g.fm, g.uid

# (ref, símbolo, valor, huella, x, y, {pin: red})
SOT = "Package_TO_SOT_SMD"
PARTES = [
    # entrada
    ("J1", "Connector:Screw_Terminal_01x01", "borne M3 +12V", "MountingHole:MountingHole_3.2mm_M3_Pad", 25.4, 50.8, {1: "VIN_BORNE"}),
    ("J2", "Connector:Screw_Terminal_01x01", "borne M3 GND", "MountingHole:MountingHole_3.2mm_M3_Pad", 25.4, 76.2, {1: "GND"}),
    ("F2", "Device:Fuse", "2A", "Fuse:Fuse_1206_3216Metric", 88.9, 50.8, {1: "VIN_BORNE", 2: "VIN_F"}),
    ("RT1", "Device:Thermistor_NTC", "NTC 10R 3A", "Varistor:RV_Disc_D9mm_W4.2mm_P5mm", 114.3, 50.8, {1: "VIN_F", 2: "VIN_R"}),
    ("D4", "Device:D_Schottky", "SS36", "Diode_SMD:D_SMB", 139.7, 50.8, {2: "VIN_R", 1: "VIN_D"}),
    ("D5", "Device:D_Zener", "SMBJ24A", "Diode_SMD:D_SMB", 165.1, 50.8, {1: "VIN_D", 2: "GND"}),
    ("CB1", "Device:C_Polarized", "10000uF 35V", "Capacitor_THT:CP_Radial_D18.0mm_P7.50mm", 190.5, 50.8, {1: "VIN_D", 2: "GND"}),
    ("C9", "Device:C_Polarized", "47uF 50V", "Capacitor_SMD:CP_Elec_8x10", 215.9, 50.8, {1: "VIN_D", 2: "GND"}),
    ("C7", "Device:C", "2.2uF 100V X7R", "Capacitor_SMD:C_1210_3225Metric", 241.3, 50.8, {1: "VIN_D", 2: "GND"}),
    ("C8", "Device:C", "2.2uF 100V X7R", "Capacitor_SMD:C_1210_3225Metric", 266.7, 50.8, {1: "VIN_D", 2: "GND"}),
    # buck
    ("R17", "Device:R", "1M", "Resistor_SMD:R_0805_2012Metric", 25.4, 114.3, {1: "VIN_D", 2: "EN"}),
    ("R18", "Device:R", "270k", "Resistor_SMD:R_0805_2012Metric", 50.8, 114.3, {1: "EN", 2: "GND"}),
    ("C10", "Device:C", "2.2nF 50V X7R", "Capacitor_SMD:C_0805_2012Metric", 76.2, 114.3, {1: "BST", 2: "SW"}),
    ("R16", "Device:R", "390k", "Resistor_SMD:R_0805_2012Metric", 101.6, 114.3, {1: "SW", 2: "RIPPLE"}),
    ("C12", "Device:C", "1nF", "Capacitor_SMD:C_0805_2012Metric", 127.0, 114.3, {1: "RIPPLE", 2: "+5V"}),
    ("C13", "Device:C", "82pF C0G", "Capacitor_SMD:C_0805_2012Metric", 152.4, 114.3, {1: "RIPPLE", 2: "FB"}),
    ("R13", "Device:R", "301k", "Resistor_SMD:R_0805_2012Metric", 177.8, 114.3, {1: "+5V", 2: "FB"}),
    ("R14", "Device:R", "95.3k", "Resistor_SMD:R_0805_2012Metric", 203.2, 114.3, {1: "FB", 2: "GND"}),
    ("R15", "Device:R", "31.6k", "Resistor_SMD:R_0805_2012Metric", 228.6, 114.3, {1: "RON", 2: "GND"}),
    ("L1", "Device:L", "22uH", "Inductor_SMD:L_6.3x6.3_H3", 254.0, 114.3, {1: "SW", 2: "+5V"}),
    ("U6", "Regulator_Switching:LM5164DDA", "LM5164DDA", "Package_SO:HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm", 63.5, 177.8,
     {1: "GND", 9: "GND", 2: "VIN_D", 3: "EN", 4: "RON", 5: "FB", 6: "PGOOD", 7: "BST", 8: "SW"}),
    ("C11", "Device:C", "22uF 16V X7R", "Capacitor_SMD:C_1206_3216Metric", 127.0, 177.8, {1: "+5V", 2: "GND"}),
    # LDO de 3,3 V y salida
    ("U7", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", SOT + ":SOT-23-5", 165.1, 177.8,
     {1: "+5V", 3: "+5V", 2: "GND", 5: "+3.3V"}),
    ("C14", "Device:C", "1uF", "Capacitor_SMD:C_0805_2012Metric", 190.5, 177.8, {1: "+5V", 2: "GND"}),
    ("C15", "Device:C", "1uF", "Capacitor_SMD:C_0805_2012Metric", 215.9, 177.8, {1: "+3.3V", 2: "GND"}),
    ("R20", "Device:R", "10k", "Resistor_SMD:R_0805_2012Metric", 241.3, 177.8, {1: "+3.3V", 2: "PGOOD"}),
    ("J3", "Connector_Generic:Conn_01x05", "Salida_5V_3V3", "Connector_JST:JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical", 292.1, 177.8,
     {1: "+5V", 2: "GND", 3: "+3.3V", 4: "GND", 5: "PGOOD"}),
]
NC = {"U7": [4]}
FLAGS = [("VIN_D", 190.5, 76.2, True), ("+5V", 127.0, 139.7, True), ("GND", 76.2, 76.2, False)]
STOCK = [("Connector_Generic", "Conn_01x05"), ("Device", "Thermistor_NTC")]


def build(outdir):
    os.makedirs(outdir, exist_ok=True)
    legacy = open(g.LEGACY_SCH).read()
    blocks = g.top_blocks(legacy)
    ls = legacy.index("(lib_symbols")
    lib_text = legacy[ls:g.balanced(legacy, ls)]
    for libfile, name in STOCK:      # símbolos de la biblioteca estándar, aplanados si usan "extends"
        sl = open(f"{g.STOCK_SYM}/{libfile}.kicad_sym").read()
        si = sl.index('\t(symbol "%s"\n' % name)
        sym = sl[si:g.balanced(sl, si + 1)]
        ext = re.search(r'\(extends "([^"]+)"\)', sym)
        if ext:
            pi = sl.index('\t(symbol "%s"\n' % ext.group(1))
            sym = sl[pi:g.balanced(sl, pi + 1)].replace(ext.group(1), name)
        sym = sym.replace('(symbol "%s"' % name, '(symbol "%s:%s"' % (libfile, name), 1)
        lib_text = lib_text[:-1].rstrip() + "\n\t\t" + sym.strip() + "\n\t)"

    def legacy_symbol(ref):
        for n, b in blocks:
            if n == "symbol" and re.search(r'\(property "Reference" "%s"' % re.escape(ref), b):
                return b
        raise KeyError(ref)

    pw = [400]

    def psym(net, x, y):
        tpl, (ox, oy) = ("#PWR091", (72.39, 35.56)) if net == "GND" else ("#PWR094", (83.82, 406.4))
        pw[0] += 1
        ref = "#PWR0%d" % pw[0]
        s = g.reseed_uuids(g.shift_block(legacy_symbol(tpl), x - ox, y - oy)).replace('"%s"' % tpl, '"%s"' % ref)
        return g.set_instance(s, PROJ, ROOT, ref)

    def glabel(net, x, y, dx, dy):
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
        fx = '(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)%s\n\t\t)'
        return ('\t(global_label "%s"\n\t\t(shape input)\n\t\t(at %s %s %d)\n\t\t%s\n\t\t(uuid "%s")\n'
                '\t\t(property "Intersheet References" "${INTERSHEET_REFS}"\n\t\t\t(at %s %s 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t%s\n\t\t)\n\t)\n'
                ) % (net, fm(x), fm(y), ang, fx % ("\n\t\t\t(justify %s)" % ("right" if ang == 180 else "left")),
                     uid(), fm(x), fm(y), fx % "\n\t\t\t(hide yes)")

    def lab(net, x, y, dx, dy):
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
        return ('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s bottom)\n\t\t)\n'
                '\t\t(uuid "%s")\n\t)\n') % (net, fm(x), fm(y), ang, "right" if ang == 180 else "left", uid())

    def no_connect(x, y):
        return '\t(no_connect\n\t\t(at %s %s)\n\t\t(uuid "%s")\n\t)\n' % (fm(x), fm(y), uid())

    def tie(lp, sx, sy, mapping, nc=()):
        out = ""
        for num, net in list(mapping.items()) + [(n, None) for n in nc]:
            px, py, ang = lp.pins[num]
            x, y = sx + px, sy - py
            dx, dy = -round(math.cos(math.radians(ang))), round(math.sin(math.radians(ang)))
            if net is None:
                out += no_connect(x, y)
                continue
            xe, ye = x + 2.54 * dx, y + 2.54 * dy
            out += g.wire(x, y, xe, ye)
            if net in ("GND", "+3.3V") and dx == 0 and ((net == "GND") == (dy > 0)):
                out += psym(net, xe, ye)
            elif net in ("GND", "+3.3V"):
                out += glabel(net, xe, ye, dx, dy)
            else:
                out += lab(net, xe, ye, dx, dy)
        return out

    def flag(net, x, y, local):
        s = g.reseed_uuids(g.shift_block(legacy_symbol("#FLG11"), x - 166.37, y - 50.8))
        pw[0] += 1
        s = s.replace('"#FLG11"', '"#FLG0%d"' % pw[0])
        return g.set_instance(s, PROJ, ROOT, "#FLG0%d" % pw[0]) + (lab(net, x, y, 1, 0) if local else glabel(net, x, y, 1, 0))

    def new_part(lib_id, ref, value, fp, x, y, lp):
        b = ('\t(symbol\n\t\t(lib_id "%s")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
             '\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n' % (
                 lib_id, fm(x), fm(y), uuid.uuid5(uuid.UUID(ROOT), "sym:" + ref)))
        for name, val, dy, hide in (("Reference", ref, -5.08, False), ("Value", value, 5.08, False),
                                    ("Footprint", fp, 0, True), ("Datasheet", "~", 0, True)):
            b += '\t\t(property "%s" "%s"\n\t\t\t(at %s %s 0)\n\t\t\t%s(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n' % (
                name, val, fm(x + 3.81), fm(y + dy), "(hide yes)\n\t\t\t" if hide else "")
        for n in sorted(lp.pins):
            b += '\t\t(pin "%d"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, uid())
        b += '\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % (PROJ, ROOT, ref)
        return b

    body = ""
    for ref, lib, val, fp, x, y, mp in PARTES:
        lp = g.LibPins(g.get_lib(lib_text, lib))
        body += new_part(lib, ref, val, fp, x, y, lp) + tie(lp, x, y, mp, nc=NC.get(ref, ()))
    for net, x, y, local in FLAGS:
        body += flag(net, x, y, local)
    hdr = ('(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n\t(generator_version "10.0")\n\t(uuid "%s")\n\t(paper "A3")\n\t' % ROOT) + lib_text + "\n"
    tail = '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n'
    open(f"{outdir}/{PROJ}.kicad_sch", "w").write(hdr + body + tail)
    pro = json.load(open(f"{g.CELDA_DIR}/celda.kicad_pro"))
    pro["meta"]["filename"] = f"{PROJ}.kicad_pro"
    pro["schematic"]["top_level_sheets"] = [{"filename": f"{PROJ}.kicad_sch", "name": PROJ, "uuid": ROOT}]
    pro["sheets"] = [[ROOT, "Raíz"]]
    json.dump(pro, open(f"{outdir}/{PROJ}.kicad_pro", "w"), indent=2, ensure_ascii=False)
    for f in ("fp-lib-table", "sym-lib-table"):
        open(f"{outdir}/{f}", "w").write(open(f"{g.CELDA_DIR}/{f}").read())
    print(f"{outdir}/{PROJ}.kicad_sch: {len(PARTES)} componentes, raíz {ROOT}")


def crear_pcb(outdir, forzar=False):
    """PCB de 2 capas con las huellas aparcadas en una cuadrícula, enlazadas al esquemático y con sus redes."""
    import pcbnew
    import replicar_celdas_pcb as R
    out = f"{outdir}/{PROJ}.kicad_pcb"
    if os.path.exists(out) and not forzar:
        print(f"{out} ya existe: no se sobrescribe (usa --forzar)")
        return
    sch = f"{outdir}/{PROJ}.kicad_sch"
    pin2net = R.read_pin2net(sch)
    b = pcbnew.CreateEmptyBoard()
    b.SetCopperLayerCount(2)
    nets = {}

    def get_net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(b, name)
            b.Add(n)
            nets[name] = n
        return nets[name]

    x0, y0, x, y, rowh, ancho = 10.0, 10.0, 10.0, 10.0, 0.0, 120.0
    for ref, val, fpid, suid, extra in sorted(R.read_root_parts(sch), key=lambda q: q[0]):
        fp = R.load_footprint(fpid)
        fp.SetReference(ref)
        fp.SetValue(val)
        for f in fp.GetFields():
            if f.GetName() in extra:
                f.SetText(extra[f.GetName()])
        fp.SetExcludedFromBOM(not extra["in_bom"])
        fp.SetPath(pcbnew.KIID_PATH("/%s/%s" % (ROOT, suid)))
        for p in fp.Pads():
            k = (ref, p.GetNumber())
            p.SetNet(get_net(pin2net[k]) if k in pin2net else get_net(""))
        r = fp.GetBoundingBox(False)
        w, h = pcbnew.ToMM(r.GetWidth()), pcbnew.ToMM(r.GetHeight())
        if x > x0 and x + w > x0 + ancho:
            x, y, rowh = x0, y + rowh + 6.0, 0.0
        fp.Move(pcbnew.VECTOR2I(pcbnew.FromMM(x - pcbnew.ToMM(r.GetX())), pcbnew.FromMM(y - pcbnew.ToMM(r.GetY()))))
        x, rowh = x + w + 6.0, max(rowh, h)
        b.Add(fp)
    b.Save(out)
    print(f"{out}: {len(b.GetFootprints())} huellas, 2 capas, sin pistas ni contorno")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    outdir = args[0] if args else f"{REPO}/{PROJ}"
    build(outdir)
    crear_pcb(outdir, "--forzar" in sys.argv)
