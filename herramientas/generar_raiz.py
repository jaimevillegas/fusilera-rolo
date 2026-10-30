#!/usr/bin/env python3
"""Genera el proyecto (esquemático raíz) de una placa a partir de la celda dorada.

Uso: generar_raiz.py {master|slave} [directorio_salida]

- Copia `celda/celda_circuito.kicad_sch` con una instancia por celda de la placa
  (referencias desplazadas +100 por celda: la celda k usa el offset 100*(k-1)).
- Crea las hojas de celda en la raíz con etiquetas por canal (`ESP32_OUTk`,
  `MANUALk`, `FALLAk`, `OUTk`) y amarra a +3,3 V las salidas directas.
- Coloca A1/U4 (master) o U5 + bloque de poder (slave) tomados de `legacy/`,
  etiqueta solo los pines del reparto de E/S (docs/asignacion-pines.md) y añade el
  conector de enlace `J10` con las mismas etiquetas en ambas placas.
- NO cablea alimentación ni I²C de los MCP (SDA/SCL solo llegan al ESP32 y al conector).
"""
import json
import os
import re
import sys
import uuid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_SCH = f"{REPO}/legacy/fusilera 24 canales.kicad_sch"
CELDA_DIR = f"{REPO}/celda"
CONN_LIB = "/usr/share/kicad/symbols/Connector_Generic.kicad_sym"
OLD_ROOT = "6451a64b-df92-4e59-b073-88385097038f"   # raíz del monolito (legacy)
CELL_SHEET_UUID = "7ac4191c-7220-47a0-be32-4085e2ecb618"
CELL_ROOT_UUID = "6451a64b-df92-4e59-b073-88385097038f"  # raíz del proyecto celda
TOTAL_DIRECTOS = range(20, 29)  # canales 20..28: salida directa, siempre en alto

# (pin del ESP32 -> red)  /  (pin del MCP -> red)
ESP32_MASTER = {
    13: "ESP32_OUT1", 25: "ESP32_OUT2", 24: "ESP32_OUT3", 22: "ESP32_OUT4",
    21: "ESP32_OUT5", 16: "ESP32_OUT6", 8: "ESP32_OUT7", 9: "ESP32_OUT8",
    10: "ESP32_OUT9", 6: "ESP32_OUT10", 7: "ESP32_OUT11", 26: "ESP32_OUT12",
    2: "FALLA1", 3: "FALLA2", 4: "FALLA3", 5: "FALLA4",
    17: "SCL", 20: "SDA",
}
U4_PINS = {**{21 + i: f"FALLA{5 + i}" for i in range(7)}, 1: "FALLA12",
           28: "ESP32_OUT15", 8: "ESP32_OUT16", 2: "ESP32_OUT17",
           3: "ESP32_OUT18", 4: "ESP32_OUT19", 5: "FALLA27", 6: "FALLA28"}
U5_PINS = {**{21 + i: f"FALLA{13 + i}" for i in range(7)},
           **{1 + i: f"FALLA{20 + i}" for i in range(7)},
           28: "ESP32_OUT13", 8: "ESP32_OUT14"}
LINK_PINS = ["LINK_5V", "LINK_5V", "GND", "GND", "SDA", "SCL",
             "ESP32_OUT15", "ESP32_OUT16", "ESP32_OUT17", "ESP32_OUT18",
             "ESP32_OUT19", "FALLA27", "FALLA28", None]  # 14: reserva

BOARDS = {
    "master": dict(cells=[1, 2, 3], sheet_y0=38.1, project="placa-master"),
    "slave": dict(cells=[4, 5, 6, 7], sheet_y0=101.6, project="placa-slave"),
}


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


def fm(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def uid():
    return str(uuid.uuid4())


def top_blocks(t):
    """Bloques de primer nivel (profundidad 1) como (nombre, texto)."""
    out, i = [], t.index("\n\t(") + 1
    while True:
        k = t.find("\n\t(", i - 1)
        if k < 0:
            return out
        s = k + 1
        e = balanced(t, s)
        out.append((t[s:e].split()[0].lstrip("("), t[s:e]))
        i = e


def shift_block(blk, dx, dy):
    def f(m):
        return "(at %s %s%s)" % (fm(float(m.group(1)) + dx), fm(float(m.group(2)) + dy), m.group(3) or "")
    return re.sub(r"\(at ([-\d.]+) ([-\d.]+)( [-\d.]+)?\)", f, blk)


def set_instance(blk, project, root, ref):
    new = '(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit %s)\n\t\t\t\t)\n\t\t\t)\n\t\t)'
    i = blk.index("(instances")
    j = balanced(blk, i)
    unit = re.search(r"\(unit (\d+)\)", blk[i:j]).group(1)
    return blk[:i] + new % (project, root, ref, unit) + blk[j:]


def reseed_uuids(blk):
    return re.sub(r'\(uuid "[0-9a-f-]+"\)', lambda m: '(uuid "%s")' % uid(), blk)


def wire(x1, y1, x2, y2):
    return ('\t(wire\n\t\t(pts\n\t\t\t(xy %s %s) (xy %s %s)\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)\n') % (fm(x1), fm(y1), fm(x2), fm(y2), uid())


def junction(x, y):
    return '\t(junction\n\t\t(at %s %s)\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "%s")\n\t)\n' % (fm(x), fm(y), uid())


def label(name, x, y, left):
    """left=True: el cable sale hacia la izquierda de la etiqueta."""
    return ('\t(label "%s"\n\t\t(at %s %s %d)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify %s bottom)\n\t\t)\n'
            '\t\t(uuid "%s")\n\t)\n') % (name, fm(x), fm(y), 180 if left else 0, "right" if left else "left", uid())


class LibPins:
    """Posición de los pines (relativa al origen) de un símbolo de biblioteca."""

    def __init__(self, text):
        self.pins = {}
        for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length ([\d.]+)\)[\s\S]*?\(number "([^"]+)"', text):
            self.pins[int(m.group(5))] = (float(m.group(1)), float(m.group(2)), int(m.group(3)))


def label_pins(libpins, sx, sy, mapping):
    """Cable de 2,54 mm + etiqueta en cada pin del mapa (símbolo sin giro)."""
    out = ""
    for num, net in mapping.items():
        px, py, ang = libpins.pins[num]
        x, y = sx + px, sy - py
        left = ang == 0   # pin que apunta a la derecha => el cable sale a la izquierda
        xe = x - 2.54 if left else x + 2.54
        out += wire(xe, y, x, y) + label(net, xe, y, left)
    return out


def get_lib(text, name):
    i = text.index('\n\t\t(symbol "%s"' % name) + 1
    return text[i:balanced(text, i)]


def build(board, outdir):
    cfg = BOARDS[board]
    proj = cfg["project"]
    root = str(uuid.uuid5(uuid.NAMESPACE_URL, "fusilera/" + proj))  # estable entre ejecuciones (los PCB enlazan por ruta)
    legacy = open(LEGACY_SCH).read()
    blocks = top_blocks(legacy)
    ls = legacy.index("(lib_symbols")
    lib_text = legacy[ls:balanced(legacy, ls)]
    # biblioteca embebida: la del monolito + Conn_01x14
    cl = open(CONN_LIB).read()
    cs = cl.index('\t(symbol "Conn_01x14"')
    conn_sym = cl[cs:balanced(cl, cs)].replace('(symbol "Conn_01x14"', '(symbol "Connector_Generic:Conn_01x14"', 1)
    conn_sym = "\t" + conn_sym.lstrip("\t")
    lib_text = lib_text[:-1].rstrip() + "\n\t\t" + conn_sym.strip() + "\n\t)"
    pins_esp = LibPins(get_lib(lib_text, "fusilera:ESP32_DevKit_30pin"))
    pins_mcp = LibPins(get_lib(lib_text, "Interface_Expansion:MCP23017x-x-SO"))
    pins_conn = LibPins(get_lib(lib_text, "Connector_Generic:Conn_01x14"))

    def legacy_symbol(ref):
        for n, b in blocks:
            if n == "symbol" and re.search(r'\(property "Reference" "%s"' % re.escape(ref), b):
                return b
        raise KeyError(ref)

    body = ""
    # --- hojas de celda -------------------------------------------------
    cell_src = open(f"{CELDA_DIR}/celda_circuito.kicad_sch").read()
    root_cell = open(f"{CELDA_DIR}/celda.kicad_sch").read()
    sh0 = root_cell.index("\t(sheet\n")
    sheet_tpl = root_cell[sh0:root_cell.index("\t(sheet_instances")]
    # quitar los cables/etiquetas dibujados en la raíz de la celda: solo hoja
    sheet_uuids = []
    pwr_n = 200
    for idx, k in enumerate(cfg["cells"]):
        y0 = cfg["sheet_y0"] + 50.8 * idx
        suid = str(uuid.uuid5(uuid.UUID(root), "Celda%d" % k))
        sheet_uuids.append((k, suid))
        sh = sheet_tpl.replace(CELL_SHEET_UUID, suid)
        sh = shift_block(sh, 0, y0 - 38.1)
        sh = sh.replace('"Sheetname" "Celda"', '"Sheetname" "Celda%d"' % k)
        sh = re.sub(r'\(pin ("[^"]+") (\w+)(\s*\(at [^)]*\)\s*\(uuid) "[0-9a-f-]+"',
                    lambda m: '(pin %s %s%s "%s"' % (m.group(1), m.group(2), m.group(3), uid()), sh)
        i = sh.index("(instances")
        sh = sh[:i] + '(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(page "%d")\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % (proj, root, 2 + idx)
        body += sh
        # canales de la celda y pines
        pinpos = {m.group(1): (float(m.group(3)), float(m.group(4)))
                  for m in re.finditer(r'\(pin "([^"]+)" (\w+)\s*\(at ([\d.]+) ([\d.]+) \d+\)', sh)}
        directos = []
        for j in range(1, 5):
            c = 4 * (k - 1) + j
            for base in ("ESP32_OUT", "MANUAL", "FALLA", "OUT"):
                x, y = pinpos[f"{base}{j}"]
                net = f"{base}{c}"
                if base == "ESP32_OUT" and c in TOTAL_DIRECTOS:
                    directos.append(y)
                    body += wire(63.5, y, x, y)
                    continue
                left = base in ("ESP32_OUT", "MANUAL")
                xe = x - 2.54 if left else x + 2.54
                body += wire(xe, y, x, y) + label(net, xe, y, left)
        if directos:
            tpl = reseed_uuids(legacy_symbol("#PWR094"))
            ytop = min(directos)
            pwr_n += 1
            tpl = shift_block(tpl, 63.5 - 83.82, ytop - 406.4)
            tpl = tpl.replace('"#PWR094"', '"#PWR0%d"' % pwr_n)
            body += set_instance(tpl, proj, root, "#PWR0%d" % pwr_n)
            if len(directos) > 1:
                body += wire(63.5, min(directos), 63.5, max(directos))
                for y in sorted(directos)[1:-1]:
                    body += junction(63.5, y)
    # --- circuito de celda con N instancias ----------------------------
    parts, pos, nref = [], 0, 0
    while True:
        i = cell_src.find("(instances", pos)
        if i < 0:
            parts.append(cell_src[pos:])
            break
        j = balanced(cell_src, i)
        m = re.search(r'\(reference "([^"]+)"\)\s*\(unit (\d+)\)', cell_src[i:j])
        ref, unit = m.group(1), m.group(2)
        mm = re.match(r"^(\D+)(\d+)$", ref)
        paths = ""
        for k, suid in sheet_uuids:
            off = 100 * (k - 1)
            r = "%s%0*d" % (mm.group(1), len(mm.group(2)), int(mm.group(2)) + off)
            paths += '\n\t\t\t\t(path "/%s/%s"\n\t\t\t\t\t(reference "%s")\n\t\t\t\t\t(unit %s)\n\t\t\t\t)' % (root, suid, r, unit)
        parts.append(cell_src[pos:i])
        parts.append('(instances\n\t\t\t(project "%s"%s\n\t\t\t)\n\t\t)' % (proj, paths))
        pos = j
        nref += 1
    cell_out = "".join(parts)

    # --- microcontrolador / MCP ----------------------------------------
    if board == "master":
        a1 = reseed_uuids(shift_block(legacy_symbol("A1"), 218.44 - 210.82, 69.85 - 177.8))
        body += set_instance(a1, proj, root, "A1")
        body += label_pins(pins_esp, 218.44, 69.85, ESP32_MASTER)
        u4 = reseed_uuids(shift_block(legacy_symbol("U4"), 218.44 - 217.17, 149.86 - 241.3))
        body += set_instance(u4, proj, root, "U4")
        body += label_pins(pins_mcp, 218.44, 149.86, U4_PINS)
    else:
        u5 = reseed_uuids(shift_block(legacy_symbol("U5"), 231.14 - 217.17, 149.86 - 306.07))
        body += set_instance(u5, proj, root, "U5")
        body += label_pins(pins_mcp, 231.14, 149.86, U5_PINS)
        c6 = reseed_uuids(shift_block(legacy_symbol("C6"), 231.14 - 217.17, 149.86 - 306.07))
        body += set_instance(c6, proj, root, "C6")
        # bloque de poder: símbolos, cables y textos del monolito con y < 100
        for n, b in blocks:
            if n == "symbol":
                ref = re.search(r'\(property "Reference" "([^"]+)"', b).group(1)
                y = float(re.search(r"\(at [-\d.]+ ([-\d.]+)", b).group(1))
                if y < 100 and ref not in ("A1", "U4", "U5"):
                    body += set_instance(b, proj, root, ref)
            elif n in ("wire", "junction", "label", "text", "polyline", "no_connect"):
                ys = [float(a or c) for a, c in re.findall(r"\(xy [-\d.]+ ([-\d.]+)\)|\(at [-\d.]+ ([-\d.]+)", b)]
                if ys and max(ys) < 100:
                    body += b + "\n"
    # --- conector de enlace ---------------------------------------------
    jx, jy = 320.04, 120.65
    j10 = ('\t(symbol\n\t\t(lib_id "Connector_Generic:Conn_01x14")\n\t\t(at %s %s 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n\t\t(exclude_from_sim no)\n'
           '\t\t(in_bom yes)\n\t\t(on_board yes)\n\t\t(in_pos_files yes)\n\t\t(dnp no)\n\t\t(uuid "%s")\n'
           '\t\t(property "Reference" "J10"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
           '\t\t(property "Value" "Enlace_placas"\n\t\t\t(at %s %s 0)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
           '\t\t(property "Footprint" "Connector_JST:JST_XH_B14B-XH-A_1x14_P2.50mm_Vertical"\n\t\t\t(at %s %s 0)\n\t\t\t(hide yes)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
           '\t\t(property "Datasheet" "~"\n\t\t\t(at %s %s 0)\n\t\t\t(hide yes)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n'
           % (fm(jx), fm(jy), uid(), fm(jx), fm(jy - 22), fm(jx), fm(jy + 22), fm(jx), fm(jy), fm(jx), fm(jy)))
    for n in range(1, 15):
        j10 += '\t\t(pin "%d"\n\t\t\t(uuid "%s")\n\t\t)\n' % (n, uid())
    j10 += '\t\t(instances\n\t\t\t(project "%s"\n\t\t\t\t(path "/%s"\n\t\t\t\t\t(reference "J10")\n\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)\n' % (proj, root)
    body += j10
    gnd_n = 0
    for num, net in enumerate(LINK_PINS, start=1):
        if net is None:
            continue
        px, py, ang = pins_conn.pins[num]
        x, y = jx + px, jy - py
        xe = x - 2.54
        if net == "GND":
            gnd_n += 1
            g = reseed_uuids(legacy_symbol("#PWR091"))
            g = shift_block(g, xe - 72.39, y - 35.56).replace('"#PWR091"', '"#PWR0%d"' % (300 + gnd_n))
            body += wire(xe, y, x, y) + set_instance(g, proj, root, "#PWR0%d" % (300 + gnd_n))
        else:
            body += wire(xe, y, x, y) + label(net, xe, y, True)

    hdr = ('(kicad_sch\n\t(version 20260306)\n\t(generator "eeschema")\n\t(generator_version "10.0")\n\t(uuid "%s")\n\t(paper "A3")\n\t' % root) \
        + lib_text + "\n"
    tail = '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n'

    os.makedirs(outdir, exist_ok=True)
    open(f"{outdir}/{proj}.kicad_sch", "w").write(hdr + body + tail)
    open(f"{outdir}/celda_circuito.kicad_sch", "w").write(cell_out)
    pro = json.load(open(f"{CELDA_DIR}/celda.kicad_pro"))
    pro["meta"]["filename"] = f"{proj}.kicad_pro"
    pro["schematic"]["top_level_sheets"] = [{"filename": f"{proj}.kicad_sch", "name": proj, "uuid": root}]
    pro["sheets"] = [[root, "Raíz"]] + [[s, "Celda%d" % k] for k, s in sheet_uuids]
    json.dump(pro, open(f"{outdir}/{proj}.kicad_pro", "w"), indent=2, ensure_ascii=False)
    for f in ("fp-lib-table", "sym-lib-table"):
        open(f"{outdir}/{f}", "w").write(open(f"{CELDA_DIR}/{f}").read())
    print(f"{proj}: raíz {root}, {len(sheet_uuids)} celdas, {nref} símbolos con instancias por celda")


if __name__ == "__main__":
    board = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else f"{REPO}/placa-{board}"
    build(board, out)
