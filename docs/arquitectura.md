# Arquitectura de dos placas (rama `separate-boards`)

Decisiones tomadas con el usuario (29–30 oct 2026). Todo lo marcado *por decidir* o *por verificar* sigue abierto.

## Idea general

- **Dos placas apiladas**, cada una con componentes a **ambas caras** (el cliente acepta el sobrecosto del ensamblaje a doble cara).
- Los nombres son **`placa-master`** (ESP32, `U4`, celdas) y **`placa-slave`** (`U5`, celdas, bloque de poder).
- Hay una **celda dorada** (`celda/`) rediseñada a doble cara para reducir espacio en X e Y y ruteada con cuidado una sola vez. Todas las celdas de ambas placas son **copias por traslación** de ella (sin espejos ni giros): así las caras de una celda nunca chocan con las de otra, y las vías pasantes no son un problema.
- Los BTS y las tiras de +12 V van en **una sola cara**; la electrónica de control puede ir en ambas (idea inicial; se confirma al diseñar la celda).

## Reparto inicial (revisar cuando la celda dorada fije sus dimensiones)

| Placa | Contenido |
|---|---|
| `placa-master` | ESP32 devkit 30 pines (`A1`), MCP23017 `U4` (0x20), celdas de los 12 primeros canales, segundo LDO 3,3 V, conector hacia la slave |
| `placa-slave` | MCP23017 `U5` (0x21), celdas de los 16 canales restantes (7 controlados + 9 directos), bloque de poder (buck 12→5 V), LDO 3,3 V, conector hacia la master |

- **Solo dos MCP** (`U4` y `U5`), sin tercero.
- **Corrección (30 oct):** `GPA7` y `GPB7` de un MCP23017 solo pueden ser salidas, así que cada MCP lee como máximo **14 fallas**. `U5` (slave) lee 14 de las 16 fallas de la slave y usa `GPA7`/`GPB7` como 2 de las 7 salidas controladas de la slave. Las otras 5 salidas salen de `U4` (master) y las 2 fallas restantes de la slave las lee `U4`; en total **7 líneas digitales** cruzan por el conector (5 de la master a la slave y 2 de la slave a la master). *Reparto exacto por decidir* (ver propuesta en la conversación o en `docs/pinout-conector.md` cuando exista).
- Las 9 salidas directas tienen su `ESP32_OUT` amarrado a +3,3 V dentro de la celda o en la raíz.
- Las etiquetas de los lados de celda en el esquemático se eliminaron (incluidas las de la Celda1); se conservan las del ESP32 y los MCP.

## Alimentación

- **Entrada de +12 V propia en cada placa**; por el conector entre placas no pasa corriente de carga.
- El buck (12→5 V) está en la slave y entrega 5 V a la master por el conector.
- **Un LDO de 3,3 V por placa** (el segundo se deja con sitio en la master). Razones: disipación (AP2112K, θJA ≈ 184 °C/W según copia de terceros del datasheet, *por verificar* en la hoja oficial; con 1,7 V de caída, 150 mA son ≈ 0,26 W) y ruido/caída a través del conector; el latch de protección es de hardware y sigue funcionando con su alimentación local. *Por verificar*: sumar la corriente real de las 28 celdas.

## Conexión entre placas

- Mecánica: **apiladas**, con separadores M3 en las esquinas (la distancia se ajusta en montaje).
- Eléctrica (propuesta, *por decidir*): cable corto con conector de pestillo (tipo JST XH / Micro-Fit), no una regleta macho-hembra rígida tipo shield (placa larga, vibración, tolerancias).
- Pines estimados: 5 V ×2, GND ×2, SDA, SCL, 7 salidas controladas desde `U4` y alguna de reserva (≈ 14–16).
- El pinout definitivo vivirá en `docs/pinout-conector.md` (pendiente) y un script verificará que coincida en ambos esquemáticos.

## Estructura del repositorio

Ver `CLAUDE.md`. Las celdas de las placas se generan con `herramientas/` desde `celda/`; no se editan a mano. La **extracción inicial** de la celda (esquemático + PCB) se hizo con `herramientas/extraer_celda_esquematico.py` y `herramientas/extraer_celda_pcb.py` a partir de la Celda1 del monolito (`legacy/`).

## Estado

1. ✅ Carpetas creadas; monolito movido a `legacy/`.
2. ✅ Proyecto `celda/` extraído de la Celda1 (esquemático: 87 componentes, ERC sin errores; PCB: paridad 0). Hereda cosas por corregir al rediseñarla: `FALLA4` sin cerrar, +12 V sin tiras, 4 vías sueltas, vía de +3,3 V con tramo suelto.
3. ⏳ Rediseñar la celda dorada a doble cara.
4. 🔄 Esquemáticos raíz de las dos placas: **generados** (`herramientas/generar_raiz.py`, reparto de pines en `docs/asignacion-pines.md`, conector en `docs/pinout-conector.md`); sin ERC con errores y con las redes por canal verificadas con el netlist. Falta cablear alimentación/I²C de los MCP y las uniones del bloque de poder. Falta también el script de replicación del PCB (necesita la celda con +12 V y contorno cerrados).
5. ⏳ Verificación de cada placa (DRC, conectividad, paridad) y script que compare el pinout del conector.
