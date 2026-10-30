# Asignación de pines (reparto A, aprobado el 30 oct 2026)

Canales 1–28 repartidos en 7 celdas de 4: celdas 1–3 en la **master** (canales 1–12, todos controlados) y celdas 4–7 en la **slave** (canales 13–28; controlados 13–19, directos 20–28). Las redes se llaman igual en ambas placas: `ESP32_OUTk`, `MANUALk`, `FALLAk`, `OUTk` (k = canal). Lo implementa `herramientas/generar_raiz.py` (tablas `ESP32_MASTER`, `U4_PINS`, `U5_PINS`, `LINK_PINS`).

Regla de fondo: `GPA7` y `GPB7` de un MCP23017 solo pueden ser salidas; cada MCP lee como máximo 14 fallas.

## Master

| Señal | Origen |
|---|---|
| `ESP32_OUT1…12` | ESP32 `A1`: D13, RX2, TX2, D18, D19, D23, D25, D26, D27, D32, D33, D4 (en ese orden) |
| `FALLA1…4` | ESP32 `A1`: VP, VN, D34, D35 |
| `FALLA5…11` | `U4` `GPA0…GPA6` |
| `FALLA12` | `U4` `GPB0` |
| `ESP32_OUT15` | `U4` `GPA7` → conector |
| `ESP32_OUT16` | `U4` `GPB7` → conector |
| `ESP32_OUT17…19` | `U4` `GPB1…GPB3` → conector |
| `FALLA27`, `FALLA28` | `U4` `GPB4`, `GPB5` ← conector |
| libres | `U4` `GPB6`; ESP32: D14, D12, D5, D2, D15 (D14 da un pulso al arrancar, ver `avisos-electricos.md`) |
| I²C | ESP32 D21 = SDA, D22 = SCL (hasta el conector; los pines de `U4` aún sin cablear) |

## Slave

| Señal | Origen |
|---|---|
| `ESP32_OUT13`, `ESP32_OUT14` | `U5` `GPA7`, `GPB7` |
| `ESP32_OUT15…19` | conector (vienen de `U4`) |
| `ESP32_OUT20…28` | +3,3 V (salidas directas, siempre en alto) |
| `FALLA13…19` | `U5` `GPA0…GPA6` |
| `FALLA20…26` | `U5` `GPB0…GPB6` |
| `FALLA27`, `FALLA28` | conector (hacia `U4`) |

## Estado del cableado (30 oct)

Hecho en ambos esquemáticos raíz:
- Etiquetas de las señales de arriba en celdas, ESP32, MCP y conector `J10`.
- MCP: `VDD` a +3,3 V, `VSS` a GND, `RESET` a +3,3 V, `SDA`/`SCK` a las redes `SDA`/`SCL`, direcciones (`U4` = 0x20 con `A0`–`A2` a GND; `U5` = 0x21 con `A0` a +3,3 V), 100 nF de desacoplo (`C6`) y marcas de no conectado en los pines sin uso.
- I²C: los pull-ups de 4,7 kΩ (`R901`, `R902`) están **solo en la master** (un juego por bus).
- **Master**: entrada de +12 V (`J1`) y masa (`J2`), LDO 3,3 V (`U7`, `C14`, `C15`) alimentado desde `LINK_5V`, y `D6` entre `LINK_5V` y `VIN` del ESP32 (anti-retroalimentación USB). El `3V3` del devkit queda sin conectar.
- **Slave**: el bloque de poder del monolito sin `D6`; el riel de 5 V sale por `LINK_5V` al conector, `VBB` se une a `+12V` y `V3V3_OUT` a `+3.3V`.

Pendiente: conectores `MANUALk` y `OUTk` (siguen como etiquetas sueltas), fusible master (`F1`, valor por preguntar al cliente) y TVS de Vbb, `EN` del ESP32 (queda sin conectar: el devkit ya trae su pull-up), tiras de +12 V del PCB (se hacen al final con todo armado).
