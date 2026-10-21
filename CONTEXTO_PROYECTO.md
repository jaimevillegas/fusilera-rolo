# Fusilera 24 canales — Contexto del proyecto

Documento de contexto para retomar el trabajo (humano o asistente) sin perder el hilo.
Estado a: **20 oct 2026**. Herramienta: **KiCad 10.0.7**. Idioma de trabajo: español.
Las referencias (R1, U3, ...) son las **actuales, tras anotar el esquemático**; no coinciden con las de versiones anteriores de este documento.

---

## 1. Qué es

Una **fusilera electrónica de 24 canales** para controlar las cargas de un carro (luces, motores de vidrios, pito, etc.).
Cada canal es un interruptor high-side con **protección de sobrecorriente que se enclava** (latch): si la corriente supera un umbral, el canal se apaga y se queda apagado hasta que se **apaga el carro** (la placa se alimenta desde **ignición**, así que al apagar el carro el circuito se reinicia).

El diseño nació de un prototipo en protoboard (con MCP23017 y ESP32 devkit en zócalo). Se está replicando en KiCad **un canal a la vez**; cuando el canal esté validado se duplicará hasta 24.

Cliente: el **BTS50010-1TAD es requerimiento suyo** (ya lo dimensionó). El estado de disparo **sí** se enviará al ESP32 por **entradas analógicas** (cada canal con una resistencia de valor distinto hacia una línea común; ver sección 6).

---

## 2. Requisitos y decisiones acordadas

| Tema | Decisión |
|---|---|
| Interruptor de potencia | BTS50010-1TAD (Infineon), requisito del cliente. TO-263-7 (PG-TO263-7-10), 1,0 mΩ. |
| Reset del latch | Apagar el carro. Todo el circuito va desde **ignición**. RC de encendido (`R6`+`C3`). |
| Control del canal | OR de dos entradas: **ESP32/MCP23017** o pin **MANUAL** (3.3 o 5 V, uno por canal). |
| Disparo | Siempre manda: `Q2` baja `IN` sin importar quién lo esté empujando. |
| Umbral de disparo | Lo fija `R1` (THT, no ensamblar, soldada a mano). **Cada canal lleva su propio divisor `R2`/`R1`**; grupos de canales (luces, vidrios, etc.) con valores distintos. |
| Lógica | 74HC132 como latch SR (2 NAND por canal). Se mantiene (NO se pasa al 74HC279). |
| Comparador | **LM339** (SOIC-14). La tarjeta no estará cerca del motor ni sufrirá temperatura (el LM339 es 0–70 °C; se acepta). |
| Grado de componentes | **Robusto**, no AEC-Q formal. |
| Fabricación | **PCB de 4 capas**, componentes SMD **a ambos lados**, potencia y tierra en capas internas. |
| Ensamblaje | JLCPCB o PCBWay (cualquiera). Todo SMD salvo `R1` (THT, no ensamblar) y los zócalos del ESP32. |
| Pasivos | **0805**. |
| LEDs | Testigo de `IN`: **verde estándar** (~2,1 V). Testigo de falla (latch): **rojo**. 0805. |
| Condensadores | Electrolíticos SMD (decisión del usuario) para `C1`, `C3`, `C5`. |
| ESP32 | **Devkit V1 de 30 pines, removible** (en zócalos hembra). Alimentado por su pin `VIN` (5 V). Su pin `3V3` **no** se conecta a nuestro riel. |
| Expansión de E/S | **1 × MCP23017** (I²C, 16 salidas) + **8 salidas directas** del ESP32 = 24 canales. `RESET` del MCP fijo a 3.3 V. |
| Regulador | Opción **A**: buck 12→5 V (alimenta el devkit con diodo Schottky anti-retroalimentación USB) + LDO 5→3.3 V para la lógica. **Pendiente de diseñar**. |

---

## 3. Arquitectura de un canal (lo que está en el esquemático)

### Flujo
1. **Entrada `IN` del BTS** (`U3` pin 2, red `U3-IN`): OR con diodos entre `ESP32 OUT` (`R5`, 4.7k) y `MANUAL` (`R4`, 4.7k) mediante `D1` (BAT54C, cátodo común pin 3 → `IN`). `R8` (100k) es pull-down de `IN`. Sin señal o con el devkit retirado, `IN` queda en bajo (canal apagado).
2. **Medición:** el pin `IS` de `U3` (red `U3-IS`) genera una corriente proporcional a la de carga. `R9` (1k) la convierte en tensión; `C5` (1 µF) la filtra. Va a la entrada − del comparador `U1A` (pin 4).
3. **Umbral:** divisor `R2` (10k a +3.3V) y `R1` (a GND) en la entrada + (pin 5).
4. **Comparador `U1A`** (colector abierto, pull-up `R3` 10k a +3.3V): su salida (pin 2) baja a 0 si hay sobrecorriente. Va a `U2` pin 4 (red `U2B-4`).
5. **Latch SR con dos NAND del 74HC132 (`U2`):** pin 3 → pin 5 (red `U2A-3`); pin 6 → pin 2 (red `U2A-2`). `U2` pin 1 = reset (`R6` 10k a +3.3V y `C3` a GND: en el encendido está en bajo ~10 ms y fija el estado "sin disparo").
   - Normal: `U2` pin 6 = 0 → `Q2` apagado → manda el ESP32/MCP o MANUAL.
   - Disparo: comparador a 0 → `U2` pin 6 = 1 → `Q2` conduce (vía `R11` 4.7k) → baja `IN` → BTS apagado. El latch mantiene el estado aunque la corriente vuelva a cero.
6. **LED rojo `D3`** (con `R12` 1k) enciende cuando el latch está disparado.
7. **LED verde `D2`** (testigo de `IN` alto): buffer con `Q1` (MMBT2222A). `R7` (100k) toma `IN` hacia la base; `R10` (2.2k) + `D2` desde +3.3V al colector; emisor a GND. LED encendido = hay señal alta en `IN`.
8. Alimentación: `C1` (100 µF/16 V) en `U1` V+, `U1` pin 12 a GND, `U2` pin 14 a +3.3V, pin 7 a GND. Desacoples de 100 nF `C2` y `C4` (uno por cada integrado), cableados.
9. **Salida de falla hacia el ESP32** (en definición): el nodo de disparo (`U2A-2`, `U2` pin 6) irá, a través de **una resistencia propia por canal**, a una línea analógica compartida (`FALLA_ESP32`). La resistencia debe ir **entre** el nodo y la etiqueta: si la etiqueta cuelga directo del nodo, KiCad une las dos redes y avisa de conflicto.

### Compuertas/comparadores restantes (para los otros canales)
- 74HC132: cada chip da 2 canales → 24 canales = 12 chips (las compuertas C y D de `U2` son el 2.º latch).
- LM339: 4 canales por chip (3 comparadores libres en `U1`) → 6 chips.
- Entradas libres de `U2` (pines 9, 10, 12, 13) y de `U1`: se usarán al replicar; mientras tanto, **amarrar entradas CMOS sin usar a GND**.

### Etiquetas de red (estado)
Se están usando etiquetas para reducir cableado: `U3-IN`, `U3-IS`, `U2A-2`, `U2A-3`, `U2B-4` (algunas **globales**), `MANUAL`, `ESP32 OUT`, `OUT`, `FALLA ESP32`.
Pendiente: pasar a **etiquetas locales con nombres funcionales** (`IN`, `IS`, `CMP`, `TRIP`, `LATCH`), porque las globales y los nombres basados en referencias unen todos los canales al copiarlos. Al replicar, añadir sufijo por canal (`IN1`, `IN2`, ...).

---

## 4. Lista de materiales (estado actual del esquemático)

| Ref | Valor | Huella | Nota |
|---|---|---|---|
| A1 | ESP32 DevKit V1 30 pines | `fusilera:ESP32_DevKit_30pin_Socket` | Símbolo y huella propios (en `libs/`). Zócalos hembra 2×15, 25,4 mm entre filas |
| U1 | LM339D | SOIC-14_3.9x8.7mm_P1.27mm | 4 comparadores |
| U2 | 74HC132D | SOIC-14_3.9x8.7mm_P1.27mm | Latch (símbolo `74xx:74LS132`, mismo pinout; KiCad no trae 74HC132) |
| U3 | BTS50010-1TAD | TO-263-7_TabPin4 | **Verificar la huella contra el plano del datasheet (PG-TO263-7-10)** |
| U4 | MCP23017-E/SO | SOIC-28W_7.5x17.9mm_P1.27mm | Expansor I²C de 16 E/S. Sin cablear. **Verificar código de pedido y temperatura** |
| Q1 | MMBT2222A | SOT-23 | Buffer del LED verde. Pines SOT-23: B=1, E=2, C=3 |
| Q2 | MMBT2222A | SOT-23 | Baja `IN` al disparar |
| D1 | BAT54C | SOT-23 | OR de entradas. Elegir marca conocida (p. ej. Nexperia BAT54C,215) |
| D2 | LED verde | LED_0805 | Testigo de `IN`. **Verde estándar ~2,1 V, NO esmeralda InGaN (Vf 2,6–3,1 V)** |
| D3 | LED rojo | LED_0805 | Testigo de falla |
| R1 | umbral | R_Axial_DIN0207_L6.3mm_P10.16mm_Horizontal | **THT, DNP (no ensamblar).** Se suelda a mano por canal |
| R2 | 10k | R_0805 | Divisor umbral (por canal) |
| R3 | 10k | R_0805 | Pull-up salida comparador |
| R4 | 4.7k | R_0805 | Serie de `MANUAL` |
| R5 | 4.7k | R_0805 | Serie de `ESP32 OUT` |
| R6 | 10k | R_0805 | Reset RC |
| R7 | 100k | R_0805 | Base de `Q1` |
| R8 | 100k | R_0805 | Pull-down de `IN` |
| R9 | 1k | R_0805 | Resistencia de sensado `IS` |
| R10 | 2.2k | R_0805 | LED verde (1k si se quiere más brillante) |
| R11 | 4.7k | R_0805 | Base de `Q2` |
| R12 | 1k | R_0805 | LED rojo |
| C1 | 100uF 16V | CP_Elec_6.3x5.4 | Bulk 3.3 V (electrolítico) |
| C2, C4 | 100nF | C_0805 | Desacople de `U1`/`U2` |
| C3 | 1uF 25V | CP_Elec_4x5.4 | Reset RC (electrolítico) |
| C5 | 1uF 25V | CP_Elec_4x5.4 | Filtro de `IS`. Ver nota de fuga |

---

## 5. Cálculo del umbral de disparo

Del datasheet del BTS50010-1TAD: relación de corriente de sensado **dkILIS típica = 52100**. Sensado: `IIS ≈ I_carga / dkILIS` (+ pequeña corriente de offset). Con `R9` = 1k:

```
V_umbral = I_disparo / 52100 × 1000 Ω
R1       = V_umbral × R2 / (3.3 V − V_umbral)        (R2 = 10k)
```

| I disparo | V umbral | R1 (con R2 = 10k) |
|---|---|---|
| 5 A | ~0,10 V | ~300 Ω |
| 10 A | ~0,19 V | ~620 Ω |
| 20 A | ~0,38 V | ~1,3 kΩ |
| 30 A | ~0,58 V | ~2,1 kΩ |
| ~55 A | ~1,05 V | 4,7 kΩ (valor del prototipo) |

**Advertencias:** son estimaciones. Según un hilo de Infineon la exactitud del sensado depende de tensión, temperatura y corriente, y a corrientes bajas puede ser mala. Los umbrales bajos se acercan al offset del comparador. **Validar con carga real.** La fuga del electrolítico `C5` (µA × 1 kΩ = mV) puede mover un par de % el disparo en umbrales bajos. El umbral es ratiométrico al riel de 3.3 V.

---

## 6. ESP32 devkit y MCP23017: asignación de pines

Devkit de 30 pines con **USB abajo**. Numeración del símbolo `A1`: pines **1–15** = columna izquierda (arriba→abajo); **16–30** = columna derecha (arriba→abajo).
Izquierda: 1 EN, 2 VP(GPIO36), 3 VN(GPIO39), 4 D34, 5 D35, 6 D32, 7 D33, 8 D25, 9 D26, 10 D27, 11 D14, 12 D12, 13 D13, 14 GND, 15 VIN.
Derecha: 16 D23, 17 D22(SCL), 18 TX0(GPIO1), 19 RX0(GPIO3), 20 D21(SDA), 21 D19, 22 D18, 23 D5, 24 TX2(GPIO17), 25 RX2(GPIO16), 26 D4, 27 D2, 28 D15, 29 GND, 30 3V3.
*(Los alias de GPIO son los estándar del DevKit V1; verificar con la placa.)*

### Restricciones verificadas del ESP32
- Pines de arranque (strapping): GPIO0, 2, 5, 12, 15. Pull por defecto: 0, 5, 15 pull-up; 2, 12 pull-down. GPIO12 en alto impide arrancar.
- GPIO14 no es de arranque (es JTAG).
- GPIO34, 35, 36, 39: solo entrada, sin pull internos.
- ADC2 no funciona con WiFi activo → lecturas analógicas en ADC1 (GPIO32–39).
- Un pin con pull-up interno al arrancar (5, 15) pasaría por `R5`/`D1` hacia `IN` y, con `R8` = 100k, `IN` podría llegar a ~2 V y encender un canal un instante. Por eso se evitan para salidas.
- *No confirmado:* si algunos pines emiten PWM breve al arrancar (mencionado en guías de terceros).

### Asignación acordada
| Pin símbolo | Etiqueta | Uso |
|---|---|---|
| 20 | D21 | **SDA** → MCP23017 (pull-up 4.7k a 3.3V) |
| 17 | D22 | **SCL** → MCP23017 (pull-up 4.7k a 3.3V) |
| 4 | D34 | **Falla analógica 1** (ADC1, solo entrada) |
| 5 | D35 | **Falla analógica 2** (ADC1, solo entrada) |
| 2, 3 | VP, VN | Entradas libres (ADC1), reserva |
| 13, 25, 24, 22, 21, 8, 9, 10, 6, 7, 26, 16 | D13, D16, D17, D18, D19, D25, D26, D27, D32, D33, D4, D23 | **Salidas directas seguras** (12 disponibles, se usan 8 → 4 de reserva) |
| 11 | D14 | Reserva (JTAG), con precaución |
| 23, 28, 27, 12 | D5, D15, D2, D12 | **Evitar** (arranque) |
| 18, 19 | TX0, RX0 | **Evitar** (programación/log USB) |
| 1 | EN | Reset del ESP32 |
| 15 | VIN | +5 V del buck (vía Schottky) |
| 14, 29 | GND | GND |
| 30 | 3V3 | **No conectar** (marca de no conexión) |

### MCP23017 (`U4`, SOIC-28W)
- 16 salidas (GPA0–7 = pines 21–28, GPB0–7 = pines 1–8) para 16 canales; los otros 8 canales van a las salidas directas del ESP32.
- `SDA` pin 13 y `SCK` pin 12 al ESP32; pull-ups de 4.7k.
- `RESET` (pin 18) **fijo a 3.3 V** (se libera D23 como salida directa); `A0`–`A2` (15–17) a GND (dirección 0x20); `VDD` pin 9 a +3.3V con 100 nF, `VSS` pin 10 a GND; `INTA`/`INTB` sin usar; `NC` pines 11 y 14.
- GPA7/GPB7 son solo salida (no importa: se usan como salidas).
- Al arrancar, el MCP23017 deja todos los pines como entradas de alta impedancia → con `R8` (pull-down) **los canales arrancan apagados**.

### Falla analógica
Dos entradas analógicas (D34, D35): cada canal envía su estado de disparo por una resistencia de valor distinto hacia una de esas líneas, de modo que el ESP32 identifique qué canal falló. Hay que definir cuántos canales por línea y los valores (el ADC del ESP32 solo distingue algunos niveles con fiabilidad, no sirve para fallas simultáneas sin una codificación cuidadosa).

---

## 7. Regulador (pendiente)

```
IGN 12V ─ fusible ─ protección polaridad ─ TVS ─ buck 12→5V ─┬─ diodo Schottky ─► devkit ESP32 (pin VIN)
                                                              └─ LDO 5→3.3V ─► lógica (74HC132, LM339, MCP23017, pull-ups, LEDs)
```

- Presupuesto: devkit con WiFi ~0,5–0,7 A pico a 5 V; lógica ~100 mA o menos a 3.3 V → buck de **≥1,5 A**.
- Entrada de carro: picos de hasta ~40 V (load dump), caídas a 6–8 V al arrancar el motor, posible polaridad inversa. Buck de entrada ancha (≥60 V cómodo), TVS, protección de polaridad (P-MOSFET o Schottky), fusible.
- Candidatos a verificar (no confirmados): familias LMR36015-Q1, LM5164-Q1.
- El pin 3V3 del devkit **no** se conecta a la lógica (evita conflicto con el USB).
- Poner `PWR_FLAG` en `+12V` y `GND` cuando existan los conectores (`+3.3V` lo dará el regulador).

---

## 8. Hallazgos técnicos relevantes (verificados en datasheets/listados)

- **LM339: 0–70 °C.** Hermano LM2901 (variante V/NCV2901) llega a −40/+125 °C con el mismo pinout. Se decidió mantener LM339.
- **74HC132D (Nexperia):** −40/+125 °C, SOIC-14, 2–6 V. Existe versión AEC-Q100 Grado 1.
- **BTS50010-1TAD:** PG-TO263-7-10, 1,0 mΩ, dkILIS típico 52100, Rsense recomendada 1 kΩ, entrada compatible 3.3 V…Vs, Vs operativo 8–18 V (extendido 3.2–28 V). Está en LCSC (C2150443).
- **MMBT2222A:** en SOT-23 el orden de pines (B=1, E=2, C=3) difiere del PN2222A TO-92. El símbolo en KiCad ya está cambiado.
- **BAT54C:** el Vf varía mucho entre fabricantes (0,5–1 V a 100 mA). Afecta el nivel de `IN`.
- **LEDs verdes:** esmeralda InGaN (Vf 2,6–3,1 V) no sirve con 3.3 V; usar verde estándar (~2,1 V).
- **JLCPCB:** algunas fichas muestran AEC-Q200 por pieza; no se confirmó filtro AEC-Q. **PCBWay:** consigue piezas por MPN del BOM. Ninguno confirmado para trazabilidad automotriz formal (no es requisito).
- Nivel de `IN`: con 3.3 V y los diodos, `IN` ≈ 2,9 V. Con `MANUAL` a 5 V, ≈ 4,5 V (verificar máximo absoluto de `IN`).

---

## 9. Estado del esquemático y pendientes

### Ya hecho
- Circuito de un canal completo y verificado por netlist (comparador, latch, `Q2`, entrada OR con diodos, testigo verde, LED rojo, reset RC, desacoples).
- Todas las huellas asignadas. Esquemático **anotado** (referencias renumeradas).
- `U4` (MCP23017) y `A1` (ESP32 devkit) colocados, **sin cablear**. Biblioteca propia `fusilera` creada (`libs/`).
- Circuito viejo (con 74HC74) eliminado.

### Pendiente — esquemático
- [ ] **Conectar `A1` y `U4`** según la sección 6 (SDA/SCL, pull-ups, `RESET` a 3.3V, direcciones, desacople `C` de 100 nF para `U4`, alimentación del devkit por `VIN`, no conectar `3V3`).
- [ ] Definir la **línea de falla analógica**: resistencia por canal, cuántos canales por línea (D34/D35).
- [ ] Pasar etiquetas globales/basadas en referencias a **locales con nombres funcionales** (`IN`, `IS`, `CMP`, `TRIP`, `LATCH`).
- [ ] Conectores/pines reales para `MANUAL`, `ESP32 OUT`, `OUT` y la entrada de 12 V.
- [ ] **Amarrar entradas sin usar** de `U2` (pines 9, 10, 12, 13) y de comparadores no usados, hasta replicar.
- [ ] `PWR_FLAG` en `+12V` y `GND`; resolver los errores `power_pin_not_driven` (+3.3V sin fuente hasta el regulador).
- [ ] Resolver aviso `lib_symbol_mismatch` de `Q1`/`Q2` (MMBT2222A): *Herramientas → Actualizar símbolos desde biblioteca*.
- [ ] Eliminar la nota de texto desactualizada si queda alguna con referencias antiguas.
- [ ] **Replicar el canal ×24** (12 × 74HC132, 6 × LM339), duplicando `R2`/`R1` por canal; renumerar con *Anotar* (opción "mantener" para no tocar lo ya numerado).
- [ ] Tamaño de hoja: pasó a "GERBER"; usar un tamaño estándar (A2/A1/A0) y ordenar el layout.

### Pendiente — diseño
- [ ] **Regulador** (sección 7): seleccionar buck, LDO, TVS, protección de polaridad, fusible; dibujar.
- [ ] Verificar el umbral con el BTS real y fijar `R1` por grupo.
- [ ] Definir resistencias de la falla analógica (sección 6).
- [ ] Comprobar contra el datasheet del BTS: umbral de `IN` alto (~2,9 V con 3.3 V) y máximo absoluto de `IN` (si `MANUAL` es 5 V).
- [ ] Verificar la huella `TO-263-7_TabPin4` contra el plano de PG-TO263-7-10.
- [ ] Verificar el código de pedido y rango de temperatura del MCP23017 (`-E/SO`), y los alias de GPIO del devkit con la placa física.
- [ ] Elegir MPN concretos de cada componente para el ensamblador (marca conocida para BAT54C, MMBT2222A; verde estándar ~2,1 V; electrolíticos SMD) y generar BOM + archivo de colocación.

### Pendiente — PCB
- [ ] El `.kicad_pcb` está **vacío** (no se ha iniciado). Cuando empiece: 4 capas, componentes a ambas caras, potencia y tierra en planos internos, **tierra de potencia vs lógica** (la medición de `IS` es sensible a caídas de tensión en GND), pistas gruesas para los BTS y disipación (TO-263), `R1` THT accesible para soldar a mano.
- [ ] **Desacoples (`C2`, `C4`, el de `U4`) lo más cerca posible de los pines de alimentación** de cada integrado, con pistas cortas.
- [ ] Posición de los zócalos del ESP32 (huella propia, 25,4 mm entre filas) y de `R1` (THT axial 10,16 mm) frente a los 24 canales.

---

## 10. Archivos del proyecto

| Archivo | Descripción |
|---|---|
| `fusilera 24 canales.kicad_sch` | Esquemático (un canal + `U4` + `A1`) |
| `fusilera 24 canales.kicad_pcb` | PCB (vacío) |
| `fusilera 24 canales.kicad_pro` | Proyecto |
| `libs/fusilera.kicad_sym` | Símbolo propio `ESP32_DevKit_30pin` |
| `libs/fusilera.pretty/` | Huella propia `ESP32_DevKit_30pin_Socket` |
| `sym-lib-table`, `fp-lib-table` | Tablas de bibliotecas del proyecto (registran `libs/`). Si KiCad no las ve, reabrir el proyecto |
| `CONTEXTO_PROYECTO.md`, `CLAUDE.md` | Contexto y reglas de trabajo |
| `.history/`, `_restore_backup_*/`, `~*.lck`, `*.kicad_prl` | Locales: **no subir** (ya en `.gitignore`) |

Repositorio: https://github.com/jaimevillegas/fusilera-rolo (público).

---

## 11. Notas de flujo de trabajo (para quien continúe)

- **No editar el `.kicad_sch` con el editor de KiCad abierto**: se pierde el cambio al guardar. Pedir que lo cierren (indicador: presencia de `~fusilera 24 canales.kicad_sch.lck`).
- Verificación con `kicad-cli` tras cada cambio:
  - `kicad-cli sch erc --severity-all -o erc.txt "fusilera 24 canales.kicad_sch"`
  - `kicad-cli sch export netlist --format kicadsexpr -o n.net "fusilera 24 canales.kicad_sch"`
  - Comparar el netlist antes/después para asegurar conectividad idéntica.
- El usuario va **cableando a mano**; el asistente coloca componentes sin cablear en zona libre y luego revisa su imagen o el netlist guardado.
- Decisiones **por pasos cortos con opciones y recomendación**; verificar datos técnicos con datasheets/búsqueda antes de recomendar piezas.
- **Commits sin atribución a Claude** (ver `CLAUDE.md`).

---

## 12. Historial resumido de decisiones

1. Rehacer el circuito en KiCad a partir de la protoboard (se eliminó el diseño viejo con 74HC74/PN2222A/LM339 DIP).
2. 74HC132 y LM339 como CI base (SOIC-14).
3. Entrada manual por canal: OR con diodos (BAT54C) + pull-down 100k; corregido un error inicial de divisor.
4. Testigo de `IN` con buffer NPN (no directo en `IN`).
5. Todo SMD 0805, 4 capas, ensamblaje JLCPCB/PCBWay, grado robusto.
6. LM339 y 74HC132 se mantienen; MMBT2222A y BAT54C aceptados; LED verde estándar y rojo; electrolíticos.
7. `R1` THT axial horizontal, no ensamblar, un divisor por canal.
8. Esquemático anotado (renumerado) y desacoples cableados.
9. Falla hacia el ESP32 por entradas analógicas (cambió el requisito inicial).
10. ESP32 devkit de 30 pines en zócalo (símbolo/huella propios) + MCP23017: 1 MCP + 8 salidas directas; `RESET` del MCP a 3.3 V; dos entradas analógicas (D34, D35).
11. Regulador opción A (buck 12→5 V + LDO 3.3 V) — por diseñar.
