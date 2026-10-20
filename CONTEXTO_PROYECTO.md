# Fusilera 24 canales — Contexto del proyecto

Documento de contexto para retomar el trabajo (humano o asistente) sin perder el hilo.
Estado a: **19 oct 2026**. Herramienta: **KiCad 10.0.7**. Idioma de trabajo: español.

---

## 1. Qué es

Una **fusilera electrónica de 24 canales** para controlar las cargas de un carro (luces, motores de vidrios, pito, etc.).
Cada canal es un interruptor high-side con **protección de sobrecorriente que se enclava** (latch): si la corriente supera un umbral, el canal se apaga y se queda apagado hasta que se **apaga el carro** (la placa se alimenta desde **ignición**, así que al apagar el carro el circuito se reinicia).

El diseño nació de un prototipo en protoboard. Se está replicando en KiCad **un canal a la vez**; cuando el canal esté validado se duplicará 24 veces.

Cliente: no pidió señales de "bandera de disparo" hacia el ESP32 (no se envían). El **BTS50010-1TAD es requerimiento del cliente** (ya lo dimensionó él).

---

## 2. Requisitos y decisiones acordadas

| Tema | Decisión |
|---|---|
| Interruptor de potencia | BTS50010-1TAD (Infineon), requisito del cliente. TO-263-7 (PG-TO263-7-10), 1,0 mΩ. |
| Reset del latch | Apagar el carro. Todo el circuito va desde **ignición**. RC de encendido (`R13`+`C2`). |
| Banderas de disparo al ESP32 | **No** (el cliente no lo pidió). |
| Control del canal | OR de dos entradas: pin del **ESP32** o pin **MANUAL** (3.3 o 5 V, uno por canal). |
| Disparo | Siempre manda: `Q2` baja `IN` sin importar quién lo esté empujando. |
| Umbral de disparo | Lo fija `R12` (THT, no ensamblar, soldada a mano). **Cada canal lleva su propio divisor `R11`/`R12`**; habrá grupos de canales (luces, vidrios, etc.) con valores distintos. |
| Lógica | 74HC132 como latch SR (2 NAND por canal) — se mantiene, NO se pasa al 74HC279. |
| Comparador | **LM339** (SOIC-14). La tarjeta no estará cerca del motor ni sufrirá temperatura (el LM339 es 0–70 °C; se acepta). |
| Grado de componentes | **Robusto**, no AEC-Q formal. |
| Fabricación | **PCB de 4 capas**, componentes SMD **a ambos lados**, potencia y tierra en capas internas. |
| Ensamblaje | JLCPCB o PCBWay (cualquiera). Todo SMD salvo `R12` (THT, no ensamblar). |
| Pasivos | **0805**. |
| LEDs | Testigo de `IN`: **verde estándar** (~2,1 V). Testigo de falla (latch): **rojo**. 0805. |
| Condensadores | Electrolíticos SMD (decisión del usuario) para `C2`, `C5`, `C7`. |
| ESP32 | **Devkit removible**. Se alimentará por su pin 5V/VIN; su pin 3V3 **no** se conecta a nuestro riel. |
| Regulador | Opción **A**: buck 12→5 V (alimenta el devkit con diodo Schottky anti-retroalimentación USB) + LDO 5→3.3 V para la lógica. **Pendiente de diseñar**. |

---

## 3. Arquitectura de un canal (lo que está en el esquemático)

### Flujo
1. **Entrada `IN` del BTS** (`U6` pin 2): OR con diodos entre `ESP32 OUT` (`R18`, 4.7k) y `MANUAL` (`R19`, 4.7k) mediante `D3` (BAT54C, cátodo común → `IN`). `R20` (100k) es pull-down de `IN`. Si no hay señal o el devkit está retirado, `IN` queda en bajo (canal apagado).
2. **Medición:** el pin `IS` de `U6` genera una corriente proporcional a la de carga. `R17` (1k) la convierte en tensión; `C7` (1 µF) la filtra. Va a la entrada − del comparador `U5A` (pin 4).
3. **Umbral:** divisor `R11` (10k a +3.3V) y `R12` (a GND) en la entrada + (pin 5).
4. **Comparador `U5A`** (colector abierto, pull-up `R16` 10k a +3.3V): su salida (pin 2) baja a 0 si hay sobrecorriente. Va a `U4B` pin 4.
5. **Latch SR con dos NAND (`U4A`, `U4B` del 74HC132):** `U4A` pin 3 → `U4B` pin 5; `U4B` pin 6 → `U4A` pin 2. `U4A` pin 1 = reset (`R13` 10k a +3.3V y `C2` a GND: en el encendido está en bajo ~10 ms y fija el estado "sin disparo").
   - Normal: `U4B` pin 6 = 0 → `Q2` apagado → manda el ESP32/MANUAL.
   - Disparo: comparador a 0 → `U4B` pin 6 = 1 → `Q2` conduce (vía `R14` 4.7k) → baja `IN` → BTS apagado. El latch mantiene el estado aunque la corriente vuelva a cero.
6. **LED rojo `D2`** (con `R15` 1k) enciende cuando el latch está disparado (cuelga de `U4B` pin 6).
7. **LED verde `D4`** (testigo de `IN` alto): buffer con `Q3` (MMBT2222A). `R21` (100k) toma `IN` hacia la base; `R22` (2.2k) + `D4` desde +3.3V al colector; emisor a GND. LED encendido = hay señal alta en `IN` (el BTS recibe orden de encender).
8. Alimentación: `C5` (100 µF/16 V) en `U5` V+, `U5` pin 12 a GND, `U4` pin 14 a +3.3V, pin 7 a GND. Desacoples de 100 nF `C8` (para `U4`) y `C9` (para `U5`) **colocados pero sin cablear**.

### Compuertas/comparadores restantes (para los otros canales)
- 74HC132: `U4C`, `U4D` (2.º latch). Cada 74HC132 da 2 canales → 24 canales = 12 chips.
- LM339: 3 comparadores libres por chip (4 canales por chip) → 24 canales = 6 chips.
- Las entradas libres de `U4` (pines 9, 10, 12, 13) y de `U5` quedarán conectadas al duplicar los canales; mientras no se usen, **amarrar entradas de CMOS sin usar a GND**.

---

## 4. Lista de materiales (estado actual del esquemático)

| Ref | Valor | Huella | Nota |
|---|---|---|---|
| U4 | 74HC132D | SOIC-14_3.9x8.7mm_P1.27mm | Latch (símbolo `74xx:74LS132`, mismo pinout). KiCad no trae símbolo 74HC132 |
| U5 | LM339D | SOIC-14_3.9x8.7mm_P1.27mm | 4 comparadores |
| U6 | BTS50010-1TAD | TO-263-7_TabPin4 | **Verificar la huella contra el plano del datasheet (PG-TO263-7-10)** |
| Q2 | MMBT2222A | SOT-23 | Baja `IN` al disparar. Pines SOT-23: B=1, E=2, C=3 |
| Q3 | MMBT2222A | SOT-23 | Buffer del LED verde |
| D3 | BAT54C | SOT-23 | OR de entradas. Elegir marca conocida (Nexperia BAT54C,215 etc.) |
| D2 | LED rojo | LED_0805 | Testigo de falla |
| D4 | LED verde | LED_0805 | Testigo de `IN`. **Usar verde estándar/amarillo-verde ~2,1 V, NO esmeralda InGaN (Vf 2,6–3,1 V)** |
| R11 | 10k | R_0805 | Divisor umbral (por canal) |
| R12 | umbral | R_Axial_DIN0207_L6.3mm_P10.16mm_Horizontal | **THT, DNP (no ensamblar).** Se suelda a mano por canal |
| R13 | 10k | R_0805 | Reset RC |
| R14 | 4.7k | R_0805 | Base de `Q2` |
| R15 | 1k | R_0805 | LED rojo |
| R16 | 10k | R_0805 | Pull-up salida comparador |
| R17 | 1k | R_0805 | Resistencia de sensado `IS` |
| R18 | 4.7k | R_0805 | Serie de `ESP32 OUT` |
| R19 | 4.7k | R_0805 | Serie de `MANUAL` |
| R20 | 100k | R_0805 | Pull-down de `IN` |
| R21 | 100k | R_0805 | Base de `Q3` |
| R22 | 2.2k | R_0805 | LED verde (1k si se quiere más brillante) |
| C2 | 1uF 25V | CP_Elec_4x5.4 | Reset RC (electrolítico) |
| C5 | 100uF 16V | CP_Elec_6.3x5.4 | Bulk 3.3 V |
| C7 | 1uF 25V | CP_Elec_4x5.4 | Filtro de `IS`. Ver nota de fuga |
| C8 | 100nF | C_0805 | Desacople `U4` — **sin cablear** |
| C9 | 100nF | C_0805 | Desacople `U5` — **sin cablear** |

Las referencias empiezan en R11/C2/U4... porque se borró el circuito viejo (U1–U3, Q1, etc.). Se renumerará con *Anotar* al final.

---

## 5. Cálculo del umbral de disparo

Del datasheet del BTS50010-1TAD: relación de corriente de sensado **dkILIS típica = 52100**. Sensado: `IIS ≈ I_carga / dkILIS` (+ pequeña corriente de offset). Con `R17` = 1k:

```
V_umbral = I_disparo / 52100 × 1000 Ω
R12      = V_umbral × R11 / (3.3 V − V_umbral)        (R11 = 10k)
```

| I disparo | V umbral | R12 (con R11 = 10k) |
|---|---|---|
| 5 A | ~0,10 V | ~300 Ω |
| 10 A | ~0,19 V | ~620 Ω |
| 20 A | ~0,38 V | ~1,3 kΩ |
| 30 A | ~0,58 V | ~2,1 kΩ |
| ~55 A | ~1,05 V | 4,7 kΩ (valor del prototipo) |

**Advertencias:** son estimaciones. Según un hilo de Infineon la exactitud del sensado depende de tensión, temperatura y corriente, y a corrientes bajas puede ser mala. Los umbrales bajos se acercan al offset del comparador. **Validar con carga real.** La fuga del electrolítico `C7` (µA × 1 kΩ = mV) puede mover un par de % el disparo en umbrales bajos.
El umbral es ratiométrico al riel de 3.3 V.

---

## 6. Regulador (pendiente)

Arquitectura elegida:

```
IGN 12V ─ fusible ─ protección polaridad ─ TVS ─ buck 12→5V ─┬─ diodo Schottky ─► devkit ESP32 (pin 5V/VIN)
                                                              └─ LDO 5→3.3V ─► lógica (74HC132, LM339, pull-ups, LEDs)
```

- Presupuesto: devkit con WiFi ~0,5–0,7 A pico a 5 V; lógica ~100 mA o menos a 3.3 V → buck de **≥1,5 A**.
- Entrada de carro: picos de hasta ~40 V (load dump), caídas a 6–8 V al arrancar el motor, posible polaridad inversa. Buck de entrada ancha (≥60 V cómodo), TVS, protección de polaridad (P-MOSFET o Schottky), fusible.
- Candidatos a verificar (no confirmados): familias LMR36015-Q1, LM5164-Q1.
- El pin 3V3 del devkit **no** se conecta a la lógica (evita conflicto con el USB).
- Si se quiere LED azul, alimentarlo del riel de 5 V (no aplica: se eligió verde/rojo).
- Poner `PWR_FLAG` en `+12V` y `GND` cuando existan los conectores (ya no en +3.3V, que lo da el regulador).

---

## 7. Hallazgos técnicos relevantes (verificados en datasheets/listados)

- **LM339: 0–70 °C.** Hermano LM2901 (variante V/NCV2901) llega a −40/+125 °C con el mismo pinout. Se decidió mantener LM339 (la tarjeta no está cerca del motor).
- **74HC132D (Nexperia):** −40/+125 °C, SOIC-14, 2–6 V. Existe versión AEC-Q100 Grado 1.
- **BTS50010-1TAD:** PG-TO263-7-10, 1,0 mΩ, dkILIS típico 52100, Rsense recomendada 1 kΩ, entrada compatible 3.3 V…Vs, Vs operativo 8–18 V (extendido 3.2–28 V). Está en LCSC (C2150443).
- **MMBT2222A:** en SOT-23 el orden de pines (B=1, E=2, C=3) difiere del PN2222A TO-92 (E=1, B=2, C=3). El símbolo en KiCad ya está cambiado a MMBT2222A.
- **BAT54C:** el Vf varía mucho entre fabricantes (0,5–1 V a 100 mA). Afecta el nivel de `IN`.
- **LEDs verdes:** esmeralda InGaN (Vf 2,6–3,1 V) no sirve con 3.3 V; usar verde estándar (~2,1 V).
- **JLCPCB:** algunas fichas muestran AEC-Q200 por pieza; no se confirmó un filtro AEC-Q. **PCBWay:** consigue piezas por MPN del BOM. Ninguno confirmado para trazabilidad automotriz formal (no es requisito).
- Nivel de `IN`: con 3.3 V y los diodos, `IN` ≈ 2,9 V. Con `MANUAL` a 5 V, ≈ 4,5 V (el datasheet indica entrada 3.3 V…Vs; verificar máximo absoluto).

---

## 8. Estado del esquemático y pendientes

### Ya hecho
- Circuito de un canal completo (comparador, latch, `Q2`, entrada OR con diodos, testigo verde, LED rojo, reset RC).
- Todas las huellas asignadas (ver BOM). Revisadas por conectividad antes/después de cada cambio.
- Circuito viejo (con 74HC74) eliminado.

### Pendiente — esquemático
- [ ] **Cablear `C8` y `C9`** (100 nF) entre alimentación y GND de `U4` y `U5`.
- [ ] Conectores/pines reales para `MANUAL` y `ESP32 OUT` (hoy son solo etiquetas de un pin) y para la salida `OUT` y la entrada de 12 V.
- [ ] **Amarrar entradas sin usar** de `U4` (pines 9, 10, 12, 13) a GND, y las de comparadores no usados, hasta replicar los canales.
- [ ] Añadir `PWR_FLAG` a `+12V` y `GND`; resolver los 3 errores `power_pin_not_driven` (+3.3V sin fuente hasta que exista el regulador).
- [ ] Revisar valor de `R22` (2.2k vs 1k) según brillo real del LED verde.
- [ ] Rotular/reetiquetar `OUT` por canal (`OUT1`, `OUT2`...).
- [ ] **Replicar el canal ×24**, usando 12 × 74HC132 y 6 × LM339 (o jerarquía de hojas); duplicar `R11`/`R12` por canal con valores por grupo. Renumerar con *Anotar*.
- [ ] Resolver aviso `lib_symbol_mismatch` de `Q2`/`Q3` (MMBT2222A): *Herramientas → Actualizar símbolos desde biblioteca*.
- [ ] Tamaño de hoja: pasó a "GERBER"; usar un tamaño estándar (A2/A1/A0) y ordenar el layout.

### Pendiente — diseño
- [ ] **Regulador** (sección 6): seleccionar buck, LDO, TVS, protección de polaridad, fusible; dibujar.
- [ ] Verificar el umbral con el BTS real y fijar `R12` por grupo.
- [ ] Definir pines del ESP32 para las 24 salidas (evitar pines de arranque/strapping; un pull-up interno ~45k + `R18` contra `R20` podría encender el canal al arrancar). Se pensó en 74HC595 (salidas) si faltan GPIO.
- [ ] Comprobar contra el datasheet del BTS: umbral de `IN` alto (~2,9 V con 3.3 V) y máximo absoluto de `IN` (si `MANUAL` es 5 V).
- [ ] Verificar la huella `TO-263-7_TabPin4` contra el plano de PG-TO263-7-10.
- [ ] Elegir referencias concretas (MPN) de cada componente para el ensamblador (marca conocida para BAT54C, MMBT2222A; verde estándar ~2,1 V; electrolíticos SMD) y generar BOM + archivo de colocación.

### Pendiente — PCB
- [ ] El `.kicad_pcb` está **vacío** (no se ha iniciado). Cuando empiece: 4 capas, componentes a ambas caras, potencia y tierra en planos internos, **tierra de potencia vs lógica** (la medición de `IS` es sensible a caídas de tensión en GND), pistas gruesas para los BTS y disipación (TO-263), `R12` THT accesible para soldar a mano.
- [ ] Revisar posición de `R12` (THT) frente a los 24 canales (huella axial horizontal 10,16 mm ocupa espacio).

---

## 9. Archivos del proyecto

| Archivo | Descripción |
|---|---|
| `fusilera 24 canales.kicad_sch` | Esquemático (un canal) |
| `fusilera 24 canales.kicad_pcb` | PCB (vacío) |
| `fusilera 24 canales.kicad_pro` / `.kicad_prl` | Proyecto / preferencias locales |
| `.history/` | Respaldo automático de KiCad (tiene su propio repo Git) — **no subir** |
| `_restore_backup_*/` | Copia antigua de un esquemático restaurado — **no subir** |
| `~*.lck` | Bloqueos de KiCad — **no subir** |

Sugerido para `.gitignore`: `.history/`, `_restore_backup_*/`, `~*.lck`, `*-backups/`, `fp-info-cache`.

---

## 10. Notas de flujo de trabajo (para quien continúe)

- **No editar el `.kicad_sch` con el editor de KiCad abierto**: se pierde el cambio al guardar. Pedir que lo cierren (el aviso es la ausencia/presencia de `~*.kicad_sch.lck`).
- Verificación con `kicad-cli` tras cada cambio:
  - `kicad-cli sch erc --severity-all -o erc.txt "fusilera 24 canales.kicad_sch"`
  - `kicad-cli sch export netlist --format kicadsexpr -o n.net "fusilera 24 canales.kicad_sch"`
  - Comparar el netlist antes/después para asegurar conectividad idéntica.
- El usuario va **cableando a mano**; el asistente coloca componentes sin cablear en zona libre y luego revisa su imagen o el netlist guardado.
- Decisiones se toman **por pasos cortos con opciones y recomendación**; verificar datos técnicos con datasheets/búsqueda antes de recomendar piezas.

---

## 11. Historial resumido de decisiones

1. Rehacer el circuito en KiCad a partir de la protoboard (se eliminó el diseño viejo con 74HC74/PN2222A/LM339 DIP).
2. 74HC132N y LM339N como CI base (luego SOIC-14).
3. Entrada manual por canal: OR con diodos (BAT54C) + pull-down 100k; corregido un error inicial de divisor (R_serie 10k con pull-down 10k → 1,5 V).
4. Testigo de `IN` con buffer NPN (no directo en `IN`, que lo cargaría).
5. Todo SMD 0805, 4 capas, ensamblaje JLCPCB/PCBWay, grado robusto.
6. LM339 y 74HC132 se mantienen; MMBT2222A y BAT54C aceptados; LED verde estándar y rojo.
7. Electrolíticos para `C2`, `C5`, `C7`; desacoples 100 nF añadidos.
8. `R12` THT axial horizontal normal, no ensamblar, un divisor por canal.
9. Regulador opción A (buck 12→5 V + LDO 3.3 V) — por diseñar.
