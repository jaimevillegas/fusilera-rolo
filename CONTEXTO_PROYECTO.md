# Fusilera 24 canales — Contexto del proyecto

Documento de contexto para retomar el trabajo (humano o asistente) sin perder el hilo.
Estado a: **20 oct 2026**. Herramienta: **KiCad 10.0.7**. Idioma de trabajo: español.
Las referencias (R1, U3, ...) son las **actuales, tras anotar el esquemático**; no coinciden con las de versiones anteriores de este documento.

---

## 1. Qué es

Una **fusilera electrónica de 24 canales** para controlar las cargas de un carro (luces, motores de vidrios, pito, etc.).
Cada canal es un interruptor high-side con **protección de sobrecorriente que se enclava** (latch): si la corriente supera un umbral, el canal se apaga y se queda apagado hasta que se **apaga el carro** (la placa se alimenta desde **ignición**, así que al apagar el carro el circuito se reinicia).

El diseño nació de un prototipo en protoboard (con MCP23017 y ESP32 devkit en zócalo). Se está replicando en KiCad **un canal a la vez**; cuando el canal esté validado se duplicará hasta 24.

Cliente: el **BTS50010-1TAD es requerimiento suyo** (ya lo dimensionó). El estado de disparo **sí** se enviará al ESP32, **en digital**, leyéndolo con un **segundo MCP23017** (ver sección 6). Se descartó la lectura analógica con resistencias escalonadas: con 24 canales en una sola línea quedaba ~80 mV entre niveles, ambigua con fallas simultáneas y con 24 valores de resistencia distintos en el BOM.

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
| Expansión de E/S | **MCP23017 #1** (`U4`, 0x20): 16 salidas. **MCP23017 #2** (`U5`, 0x21): 14 entradas de falla + 2 salidas (GPA7/GPB7 solo salida). El resto, pines directos del ESP32 (24 canales). `RESET` de ambos fijo a 3.3 V. |
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
9. **Salida de falla hacia el ESP32:** el nodo de disparo (`TRIP` = `U2A-2`, `U2` pin 6) va **directo a una entrada digital**: del MCP23017 #2 (`U5`) o de un pin libre del ESP32 (ver sección 6). Es una señal digital de 0/3.3 V; el ESP32 lee 1 = canal disparado.

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
| A1 | ESP32 DevKit V1 30 pines | `fusilera:ESP32_DevKit_30pin_Socket` | Símbolo y huella propios (en `libs/`). Zócalos hembra 2×15, 25,4 mm entre filas. La huella lleva los nombres de los pines en la serigrafía (F.SilkS), entre las dos filas |
| U1 | LM339D | SOIC-14_3.9x8.7mm_P1.27mm | 4 comparadores |
| U2 | 74HC132D | SOIC-14_3.9x8.7mm_P1.27mm | Latch (símbolo `74xx:74LS132`, mismo pinout; KiCad no trae 74HC132) |
| U3 | BTS50010-1TAD | TO-263-7_TabPin4 | **Verificar la huella contra el plano del datasheet (PG-TO263-7-10)** |
| U4 | MCP23017-E/SO | SOIC-28W_7.5x17.9mm_P1.27mm | Expansor I²C #1: 16 salidas (0x20). Sin cablear. **Verificar código de pedido y temperatura** |
| U5 | MCP23017-E/SO | SOIC-28W_7.5x17.9mm_P1.27mm | Expansor I²C #2: 14 entradas de falla + 2 salidas (0x21). Sin cablear |
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
| C6 | 100nF | C_0805 | Desacople de `U5`. Sin cablear |

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
| 2, 3, 4, 5 | VP, VN, D34, D35 | **Entradas de falla digitales** (solo entrada, sin pull internos; la señal `TRIP` es push-pull de 0/3.3 V). Se usan 2 al inicio (18 canales) y 4 con 24 canales |
| 13, 25, 24, 22, 21, 8, 9, 10, 6, 7, 26, 16 | D13, D16, D17, D18, D19, D25, D26, D27, D32, D33, D4, D23 | **Pines directos seguros** (12 disponibles). Con 18 canales no se usan; con 24 canales: 6 como salidas y 6 como entradas de falla |
| 11 | D14 | Reserva (JTAG), con precaución |
| 23, 28, 27, 12 | D5, D15, D2, D12 | **Evitar** (arranque) |
| 18, 19 | TX0, RX0 | **Evitar** (programación/log USB) |
| 1 | EN | Reset del ESP32 |
| 15 | VIN | +5 V del buck (vía Schottky) |
| 14, 29 | GND | GND |
| 30 | 3V3 | **No conectar** (marca de no conexión) |

### MCP23017 #1 (`U4`, SOIC-28W) — salidas
- 16 salidas (GPA0–7 = pines 21–28, GPB0–7 = pines 1–8) para 16 canales; los otros 8 canales van a las salidas directas del ESP32.
- `SDA` pin 13 y `SCK` pin 12 al ESP32; pull-ups de 4.7k (compartidos con `U5`).
- `RESET` (pin 18) **fijo a 3.3 V**; `A0`–`A2` (15–17) a GND (dirección 0x20); `VDD` pin 9 a +3.3V con 100 nF (`C` de desacople), `VSS` pin 10 a GND; `INTA`/`INTB` sin usar; `NC` pines 11 y 14.
- GPA7/GPB7 son solo salida (no importa: se usan como salidas).
- Al arrancar, el MCP23017 deja todos los pines como entradas de alta impedancia → con `R8` (pull-down) **los canales arrancan apagados**.

### MCP23017 #2 (`U5`, SOIC-28W) — entradas de falla
- Lee las 16 entradas de falla (`TRIP` de cada canal) por I²C, dirección **0x21** (`A0` a 3.3 V, `A1`/`A2` a GND). Mismo bus (`SDA`/`SCK`) y mismos pull-ups que `U4`.
- `RESET` fijo a 3.3 V; `VDD` con `C6` (100 nF) de desacople.
- **GPA7 y GPB7 son solo salida** (confirmado: el datasheet actual del MCP23017 los restringe a salida; leerlos como entrada puede corromper SDA). Para entradas de falla solo valen GPA0–6 y GPB0–6 → **14 entradas** por MCP.
- **Reparto acordado para 24 canales** (24 salidas + 24 fallas):
  - Salidas: `U4` 16 (GPA0–7, GPB0–7) + **`U5` GPA7 y GPB7 como 2 salidas extra** + 6 salidas directas del ESP32 = 24.
  - Fallas: `U5` GPA0–6 y GPB0–6 (14) + VP, VN, D34, D35 (4) + 6 pines directos libres = 24.
  - Con **18 canales** (inicial): salidas `U4` (16) + `U5` GPA7/GPB7 (2); fallas `U5` (14) + VP, VN, D34, D35 (4). **No se usa ningún pin directo.**
- Si el reparto de pines no cierra, la alternativa es un tercer MCP23017 o 3 × 74HC165 (3 pines del ESP32).

---

## 7. Alimentación (en definición)

```
Terminal de tornillo +12V (IGN) ─┬─► [fusible master: ubicación por definir] ─► plano Vbb ─► Vbb de los BTS (directo, sin diodo)
                                 │
                                 └─► fusible lógica (~1-2 A) ─► diodo Schottky (polaridad inversa) ─► TVS ─► cond. entrada ─► buck 12→5V ─┬─► Schottky ─► devkit ESP32 (VIN)
                                                                                                                                       └─► LDO 5→3.3V ─► lógica
```

### Decisiones
- **Buck: LM5164** (6–100 V, 1 A, síncrono, SO-PowerPAD-8). Elegido por simplicidad. Por debajo de ~6 V deja de regular (arranque del motor): la lógica se reinicia y los canales quedan apagados hasta que el ESP32 arranque (seguro). Alternativa descartada por ahora: TPS54360B (4,5–60 V, 3,5 A, necesita diodo externo). **No usar LMR36015** (VQFN-HR 2×3 mm, difícil de ensamblar).
- **Polaridad inversa de la lógica: diodo Schottky en serie** (≥2 A, ≥60 V; 100 V si se quiere aguantar pulsos negativos fuertes). Orden: **fusible → diodo → TVS**, para que el TVS no cortocircuite una batería invertida y, si el TVS falla en corto, se funda el fusible de la lógica y no el master.
- **Los BTS no necesitan diodo en su Vbb**: tienen protección de polaridad inversa propia (ReverSave, −16 V 2 min) con RIN = 4.7k y RIS = 1k.
- La elección del buck **no afecta la corriente de los BTS** (el buck solo alimenta la lógica; los BTS toman su Vbb directo del terminal).
- **Terminal de +12 V: orificio en la PCB para tornillo con tuerca** (cable con terminal de ojo). Zona de cobre grande alrededor, orificio metalizado conectado al plano Vbb con múltiples vías; sin máscara en el área de contacto; arandela plana y de presión. Consideraciones: esfuerzo mecánico sobre la PCB (apoyo/separador o tuerca captiva SMT), capacidad de corriente del cobre (¿cobre de 2 oz?), y **falta definir el terminal de GND** (o tornillo al chasis).
- **Fusible master del cliente, antes de todos los BTS: va EN LA PLACA** (portafusible de potencia entre el terminal de +12 V y el plano Vbb). **Valor y tipo por preguntar al cliente.** Corriente máxima real según el cliente: **25–30 A durante menos de 5 s** (dos vidrios a la vez); el resto de las salidas consume poco. Falta confirmar la corriente **continua** máxima. El fusible debe tolerar 30 A durante 5 s repetidos (revisar su curva tiempo-corriente; con derating ~75 % apunta a ≥ 40 A).
- **Terminal de GND: también con tornillo.** Como los BTS son de lado alto, las cargas retornan por el chasis, no por la placa: este terminal solo lleva la corriente de la lógica y de los pines GND de los BTS (poca). Confirmar con el cliente que ninguna carga retorna por la placa.
- **Cobre para 25–30 A durante < 5 s (cálculo de calentamiento transitorio, conservador: sin disipar calor):** el aumento de temperatura depende de la sección, no del largo. Para ΔT = 30–40 K se necesita una sección de ~0,8–0,9 mm²: **cobre externo 1 oz → ~22–25 mm de ancho; 2 oz → ~11–13 mm** (ΔT = 60 K: 18 mm / 9 mm). Ejemplo: barra de 2 oz de 15 × 60 mm → ~1 mΩ, 30 A → 0,9 W y ~29 mV de caída, ~20 K en 5 s. En régimen continuo (IPC-2221, ΔT = 20 K): 10 A → 4,7 mm (1 oz) / 2,4 mm (2 oz); 15 A → 8,3 / 4,1 mm; 20 A → 12,3 / 6,1 mm.
- **Vías en el camino de potencia (cuello de botella):** ~0,9 A por vía de 0,3 mm en 5 s (ΔT = 40 K); ~1,8 A por vía de 0,6 mm. Para 30 A: ≥ 34 vías de 0,3 mm o ≥ 17 de 0,6 mm en cada cambio de capa. Mejor mantener la corriente alta en **una sola capa externa**.
- El peor caso del BTS (≈ 12–15 A por vidrio): 0,45 W, ΔT ≈ 9 K con RthJA = 20 K/W (≈ 32 K con 70 K/W). Esto reduce la exigencia de cobre grueso: 1 oz exterior puede bastar si el bus se hace con zonas anchas en ambas caras; 2 oz sigue siendo una mejora.
- Terminal de +12 V para ~50 A: **mínimo M6** (cable ~10 mm² / 8 AWG, a confirmar con el cliente). La pared del orificio metalizado (~0,5 mm²) sola no basta: la corriente debe entrar por cobre grande en la cara del terminal de ojo, con muchas vías; alternativa: espárrago o terminal de potencia soldable, o barra de cobre soldada a la placa.
- LDO 5→3.3 V candidato: AP2112K-3.3 (600 mA, SOT-25; pieza Extended en JLCPCB). Diodo hacia el devkit: Schottky de 1 A.
- TVS de 12 V (tipo ~24–26 V de standoff; el SM8S36A es de 24 V): por verificar en datasheet; su clamp debe quedar bajo el máximo del LM5164 (100 V).

### Bloque de alimentación dibujado en el esquemático (zona x≈400–660 mm, **sin conectar** al resto)
Bloque **cableado con cables reales** entre componentes (las tres tierras locales se unen por la etiqueta `GND_PWR`). Puntos de conexión (el usuario los une con etiquetas del mismo nombre): **`VBB`** → Vbb de los BTS; **`GND_PWR`** → GND; **`VIN_ESP32`** → pin VIN del devkit (`A1` pin 15); **`V3V3_OUT`** → +3.3V; `V5` (5 V) opcional. Hay `PWR_FLAG` en `VIN_D`, `V5` y `GND_PWR`.

| Ref | Valor | Huella | Función |
|---|---|---|---|
| J1 | borne +12V M6 | MountingHole_6.4mm_M6_Pad | Entrada +12 V (red `VIN_BORNE`) |
| F1 | Fusible master | *(por definir)* | Entre `VIN_BORNE` y `VBB`. Portafusible en la placa; valor por preguntar al cliente |
| F2 | 2 A (lámina SMD) | Fuse_1206_3216Metric | Fusible de la rama de lógica (`VBB` → `VIN_F`). Huella provisional |
| D4 | Schottky ≥2 A ≥60 V (SS36) | D_SMB | Polaridad inversa (`VIN_F` → `VIN_D`) |
| D5 | TVS unidireccional ~24–26 V (SMBJ) | D_SMB | Sobre `VIN_D` a GND (símbolo `D_Zener`) |
| C7, C8 | 2.2 µF 100 V X7R | C_1210 | Entrada del LM5164 |
| C9 | 47 µF 50 V | CP_Elec_8x10 | Bulk de entrada |
| U6 | LM5164DDA | HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.1mm | Buck 12→5 V. (Huella sin vías térmicas; las vías del pad expuesto las pone el usuario, 0,6/0,3 mm) PGOOD sin usar (marca de no conexión) |
| R13 / R14 | 301 k / 95.3 k | 0805 | Divisor de realimentación (`V5` → `FB` → GND) → 4,99 V |
| R15 | 31.6 k | 0805 | RRON → Fsw ≈ 396 kHz |
| R16, C12, C13 | 390 k, 1 nF, 82 pF C0G | 0805 | Red de rizado Tipo 3 (`SW` – `RAC` – `V5`, `RAC` – `FB`) |
| R17 / R18 | 1 M / 270 k | 0805 | EN/UVLO (arranca ~7,1 V, apaga ~6,6 V) |
| L1 | 22 µH, Isat ≥ 1,8 A | L_6.3x6.3_H3 (provisional) | Inductor |
| C10 | 2.2 nF 50 V X7R | 0805 | Bootstrap (`BST`–`SW`) |
| C11 | 22 µF 16 V X7R | C_1206 | Salida 5 V |
| D6 | Schottky 1 A (SS14) | D_SMA | `V5` → `VIN_ESP32` (anti-retroalimentación USB) |
| U7 | AP2112K-3.3 | SOT-23-5 | LDO 5 → 3.3 V (`V5` → `V3V3_OUT`) |
| C14, C15 | 1 µF | 0805 | Entrada y salida del LDO |
| J2 | borne GND M5 | MountingHole_5.3mm_M5_Pad | Red `GND_PWR` |
| #FLG10–12 | PWR_FLAG | — | En `VIN_D`, `V5`, `GND_PWR` |

Notas: el TVS de **Vbb** (plano de potencia, después del fusible master) **no está colocado**; pendiente de decisión con el cliente. Huellas provisionales a confirmar: F2, L1, D4/D5/D6, J1/J2 (MountingHole con pad).

### Térmica del BTS (datasheet)
- IL(NOM) = **40 A** (TA = 85 °C), RDS(on) máx. **2 mΩ** a 150 °C, umbral de cortocircuito ICL(0) = 150 A. RthJC = 0,5 K/W; **RthJA = 20 K/W** en placa JEDEC 2s2p y **70 K/W** con cobre mínimo.
- El **tab (pin 4) es Vbb**: conviene soldarlo a una región grande de cobre de +12 V (ambas capas externas + vías térmicas al plano interno Vbb). Disipación aprox.: 10 A → 0,2 W; 20 A → 0,8 W; 40 A → 3,2 W (con 2 mΩ).
- Los pines de salida (OUT, 5–7) y las pistas de carga también deben ser anchas.

---

## 8. Hallazgos técnicos relevantes (verificados en datasheets/listados)

- **LM339: 0–70 °C.** Hermano LM2901 (variante V/NCV2901) llega a −40/+125 °C con el mismo pinout. Se decidió mantener LM339.
- **74HC132D (Nexperia):** −40/+125 °C, SOIC-14, 2–6 V. Existe versión AEC-Q100 Grado 1.
- **BTS50010-1TAD** (datasheet Rev. 1.2, leído del PDF): PG-TO263-7-10, 1,0 mΩ; está en LCSC (C2150443).
  - Alimentación: **Vs operativo 8–18 V**, máximo absoluto **28 V**; **load dump 45 V** en prueba con RI = 2 Ω, **RIS = 1 kΩ y RIN = 4.7 kΩ** (justo los valores de `R9`, `R4` y `R5`); polaridad inversa **−16 V durante 2 min** con protección propia *ReverSave* (el MOSFET se enciende solo). Recomienda RIN = 4.7 kΩ y RIS = 1 kΩ.
  - Entrada `IN`: **VIN(H) ≥ 2,2 V**, VIN(L) ≤ 0,8 V, histéresis 200 mV; corriente de entrada en alto hasta **80 µA**; máximo absoluto de `IN` = **Vs** (con `MANUAL` a 5 V no hay problema) y ±5 mA.
  - Sensado: dkILIS 44500 / **52100** / 59100; en falla `IS` entrega **3,5–8 mA** (típ. 6 mA) → con `R9` = 1k hasta unos 6 V en la entrada del comparador (verificar tolerancia del LM339). IIS máx. abs. 10 mA.
  - **El BTS tiene su propio latch de sobrecarga**: tras apagarse por sobrecorriente o temperatura, solo se reinicia poniendo `IN` en bajo más de tIN(RESETDELAY). `Q2` bajando `IN` también lo rearma.
  - Margen de `IN` alto en el peor caso: ~3,3 V − Vf(BAT54C) − (80 µA + cargas) × 4.7k ≈ 2,4 V → solo ~0,2 V sobre el mínimo de 2,2 V. Vigilar (diodo de bajo Vf).
- **MMBT2222A:** en SOT-23 el orden de pines (B=1, E=2, C=3) difiere del PN2222A TO-92. El símbolo en KiCad ya está cambiado.
- **BAT54C:** el Vf varía mucho entre fabricantes (0,5–1 V a 100 mA). Afecta el nivel de `IN`.
- **LEDs verdes:** esmeralda InGaN (Vf 2,6–3,1 V) no sirve con 3.3 V; usar verde estándar (~2,1 V).
- **JLCPCB:** algunas fichas muestran AEC-Q200 por pieza; no se confirmó filtro AEC-Q. **PCBWay:** consigue piezas por MPN del BOM. Ninguno confirmado para trazabilidad automotriz formal (no es requisito).
- Nivel de `IN`: con 3.3 V y los diodos, `IN` ≈ 2,9 V sin carga (≈ 2,4 V en el peor caso con 80 µA de entrada). Con `MANUAL` a 5 V, ≈ 4,5 V: dentro del máximo absoluto (Vs).

---

## 9. Estado del esquemático y pendientes

### Ya hecho
- Circuito de un canal completo y verificado por netlist (comparador, latch, `Q2`, entrada OR con diodos, testigo verde, LED rojo, reset RC, desacoples).
- Todas las huellas asignadas. Esquemático **anotado** (referencias renumeradas).
- `U4` (MCP23017) y `A1` (ESP32 devkit) colocados, **sin cablear**. Biblioteca propia `fusilera` creada (`libs/`).
- Circuito viejo (con 74HC74) eliminado.

### Requisito de canales actualizado (22 oct)
- **28 canales de salida:** **19 controlados** (ESP32/MCP + entrada MANUAL) y **9 siempre en alto** (sin control: el lado `ESP32 OUT` de su OR va a +3,3 V mediante la misma resistencia; no usan GPIO ni MCP). **Los 28 tienen línea de falla** hacia el micro. **Sin tercer MCP**: solo ESP32 + `U4` + `U5`.
- **Cuenta de E/S:** 19 salidas de control + 28 entradas de falla = **47 líneas** de 49 disponibles (`U4` 16 + `U5` 16 + 12 pines directos seguros + 4 solo-entrada VP/VN/D34/D35 + `D14`). GPA7/GPB7 de cada MCP son solo salida (cada MCP da 14 entradas).
- **Asignación propuesta:** salidas de control: `U4` GPA0–7 y GPB0–7 (canales 1–16), `U5` GPA7 (canal 17), `U5` GPB7 (canal 18) y `D13` (canal 19). Fallas: `U5` GPA0–6 y GPB0–6 (14, canales 1–14), VP, VN, D34, D35 (canales 15–18) y 10 pines directos `D16, D17, D18, D19, D23, D25, D26, D27, D32, D33` (canales 19–28). **Reserva: `D4` y `D14`.** Sin pines de interrupción: las fallas se leen por sondeo.
- **Materiales para 28 canales:** 28 BTS, 14 × 74HC132 (2 latches por chip, sin compuertas libres), 7 × LM339 (4 comparadores por chip, sin unidades libres), 2 MCP23017, ≈ 20 componentes por canal (≈ 560), 28 resistencias de umbral THT a mano.
- Nomenclatura de redes propuesta (sufijo por canal): `OUTk`, `FALLAk`, `ESP32_OUTk`/`MANUALk` (solo canales 1–19).

### Esquemático jerárquico: la "celda" de 4 canales (22 oct)
- **Estructura:** hoja principal (`fusilera 24 canales.kicad_sch`) + hoja `celda4.kicad_sch` instanciada como **`Celda1`** y **`Celda2`** (2 instancias, para probar la replicación del layout). 28 canales = **7 celdas idénticas**. Cada celda: 4 BTS, 1 LM339, 2 × 74HC132 y todos los componentes de los 4 canales (≈ 87 refs).
- **Referencias:** `Celda1` conserva las refs existentes (R1…R54, U1…U11…); `Celda2` usa las mismas **+100** (R101…, U101…). Los pull-ups que faltaban en los canales 3 y 4 son `R53` y `R54` (`R153`, `R154` en la `Celda2`).
- **Pines de cada celda** (etiquetas jerárquicas = pines de hoja): entradas `ESP32_OUT1–4`, `MANUAL1–4`; salidas `OUT1–4`, `FALLA1–4`. Las redes internas son locales de cada hoja (p. ej. `/Celda1/FALLA2`), por lo que ya no se unen entre canales ni entre celdas. GND, +3,3 V y +12 V son globales (símbolos de alimentación).
- **Pendiente en la hoja principal:** conectar los pines de cada celda: `ESP32_OUTk` a una salida de `U4`/`U5`/pin directo del ESP32 (canales controlados) o a +3,3 V (canales siempre en alto); `MANUALk` a su conector; `OUTk` a su conector de salida; `FALLAk` a una entrada de `U5`/ESP32. Para las 7 celdas (28 canales): copiar la hoja de celda y reanotar con *Mantener*.
- **Verificado por netlist:** conexiones de `Celda1` idénticas a las del esquemático plano original (52 redes sin cambio, 4 redes compartidas separadas por canal) y `Celda2` idéntica a `Celda1`.
- **PCB:** los 25 footprints existentes de la celda se re-vincularon a `Celda1` (se conserva su colocación). Con **F8** entrarán el resto de la `Celda1` y toda la `Celda2`. Después, replicar el layout con la herramienta de multicanal de KiCad (*Generar áreas de reglas de colocación* y *Repetir layout*); en KiCad 10 puede fallar con "no compatible component found" si los pines de hoja están conectados a redes externas distintas: desconectarlos mientras se replica.
- Umbrales `R1`, `R29`, `R49`, `R51` (y `R101`, `R129`, `R149`, `R151`) con valor `umbral`, DNP y huella THT.

### Estado del PCB a 22 oct (16:08, tras importar las dos celdas)
- 202 footprints (0 problemas de paridad), 371 segmentos, 43 vías, todo en F.Cu salvo 15 segmentos en B.Cu; **sin contorno** (`Edge.Cuts`).
- **Celda1:** 87 footprints en 78 × 66 mm; los 4 BTS (`U3`, `U8`, `U10`, `U11`) en columna (x ≈ 165, y 106–161) con 17–20 mm entre ellos y el tab (+12 V) hacia la izquierda, pines de salida hacia la derecha. Quedan 34 conexiones propias por rutear (salidas `OUT1–4`, `FALLA1–4`, parte de `IS`/`IN`).
- **Plano de GND** (`PLANO_GND_In1`, contorno provisional x 12–161, y 8,5–88): **no cubre la Celda1** (y 102–168) y debe redibujarse con el contorno real. Además las redes `GND` (celdas) y `/GND_PWR` (plano y bloque de poder) son distintas hasta unir `GND_PWR` con `GND` en el esquemático (74 conexiones de GND pendientes).
- Pendiente de rellenar zonas (tecla B): 18 avisos de espaciado entre el plano y pads PTH (`J1`, umbrales `R101`, `R129`, `R149`, `R151`) por relleno desactualizado.
- Pendiente: plano de +3,3 V (propuesto en In2), zonas de +12 V y de salida de los BTS, 260 conexiones por rutear en total.

### Estado del PCB a 23 oct (10:00)
- 202 footprints, 451 segmentos (400 F.Cu, 44 In2.Cu, 7 B.Cu), 62 vías, 0 problemas de paridad; **sin contorno** (`Edge.Cuts`). Las señales `IN`/`IS` ya empezaron a pasar por In2.
- **Celda1** en x 88–148, y 98–162 con los BTS (`U3`, `U8`, `U10`, `U11`) en x ≈ 148 (y 102, 121, 140, 157). **Celda2** colocada aparte en x 123–170, y 26–74 (sin rutear). Quedan ~32 conexiones propias de la Celda1 (sobre todo `OUT1–4` y `FALLA1–4`).
- **Plano de GND** (`PLANO_GND_In1`, red `/GND_PWR`) redibujado en x 21,8–170,3, y 92,4–172: cubre la Celda1 pero **ya no cubre el bloque de poder** (y 37–61): 32 vías de GND del bloque quedan colgando hasta ampliar el plano o añadir otra zona de GND ahí.
- **GND unificado (23 oct):** en el esquemático raíz las 3 etiquetas `GND_PWR` se sustituyeron por símbolos `power:GND` (`#PWR091–093`), así que `/GND_PWR` desapareció y `GND` suma 100 pines; el PCB se actualizó (red del plano = `GND`, 74 conexiones de GND por rutear). Netlist verificado: solo cambia esa fusión.
- **Plano de +3,3 V** (`PLANO_3V3_In2`, In2.Cu, red `+3.3V`, mismo contorno que el de GND: x 21,8–170,3, y 92,4–172, espaciado 0,3 mm, alivio térmico solo en PTH): cubre 23 de los 46 pads de +3,3 V (los de la Celda1); faltan las vías de los pads SMD, y la Celda2 y el bloque de poder quedan fuera.
- DRC: 1 error de espaciado (pad 4 de `U3`, +12 V, contra un tramo suelto de 2 mm de la red `Net-(U1A--)`), 263 conexiones sin rutear (127 de GND/+3,3 V/+12 V, 104 de la Celda2).

### Revisión de la Celda1 (23 oct, tras el commit 0009fe0)
- **Correcciones concretas:** pin 1 (GND) sin rutear en `U8` y `U10`; tramo suelto de 0,57 mm en In2 en (134,1; 108,9) de `Net-(U1A--)` con un salto de 0,15 mm en y; vía sobrante de `Net-(U1A-+)` en (100,25; 125,15); **el pin 3 (VCC) de `U1` (LM339) no está conectado a +3,3 V**: su vía (105; 115,4) cae en una isla de 130 mm² del plano de In2 encerrada por pistas de señal; unirla con la vía de `R50` (95,2; 115,4) por B.Cu o abrir un paso en In2; ~~8 puntos en F.Cu con espaciado de exactamente 0,200 mm~~ (corregidos el 23 oct: los 13 puntos con F.Cu o vías ahora cumplen ≥ 0,25 mm; los 6 puntos In2–In2 de `R27`/`U1A-`/`FALLA1` también se limpiaron; solo quedan 2 en el bloque de poder entre `Net-(D6-A)` y el pad 2 de `C11`). **Ojo:** el DRC de KiCad no detecta que la isla de +3,3 V de In2 que alimenta `U1` pin 3 está físicamente aislada (trata la zona como un solo elemento); se añadió el puente de +3,3 V en B.Cu (0,5 mm, (105; 115,4) → (104; 114,4) → (96,2; 114,4) → (95,2; 115,4)) que une la isla de `U1` pin 3 con el plano principal; DRC a 0,25 mm sin errores nuevos.
- **Mejoras antes de replicar:** `C4`/`C20` están en el lado GND de `U2`/`U9` (a 9,7 mm del pin VCC); `C2` a 10 mm de VCC de `U1`; BTS con paso desigual (18,7 / 19,0 / 16,8 mm); canal 3 con transistores en distinta posición; marca del pin 1 de los BTS sobre la vía de GND; sin vías térmicas en el tab (por verificar con JLCPCB); pin 4 (Vbb) de cada BTS sin conexión externa.
- **Pendiente de arquitectura:** salida de las 12 señales de la celda (`ESP32_OUT`, `MANUAL`, `FALLA`) hacia el controlador, tira de +12 V (hueco de 6–8 mm entre tabs, ancho útil ≈ 12 mm), zonas `OUT` y camino de +12 V desde `J1` hasta las celdas.

### Celda2 replicada (23 oct)
- La Celda2 se copió de la Celda1 por script (no con la herramienta multicanal de KiCad): 87 footprints con la misma orientación y desplazados (0; −73,4 mm), más 539 pistas y 97 vías con la red equivalente. Verificado: geometría idéntica a la entera, 0 problemas de paridad, 0 errores nuevos de DRC (a 0,25 mm) y todas las redes locales de la Celda2 rutadas.
- **Disposición actual (tras mover el usuario las celdas, 23 oct 13:51):** Celda1 en x 107,7–179, y 98–166; Celda2 girada 180° a su izquierda (x 24,6–96, y 98–166). Los planos de GND (In1) y +3,3 V (In2) se ampliaron a x 21,8–181,6, y 92,4–251,2 y cubren ambas celdas; sin contorno (`Edge.Cuts`).
- **DRC:** 0 errores de espaciado, 0 problemas de paridad; 27 conexiones sin rutear (15 de +12 V de los tabs, 10 de GND, 1 de +3,3 V y 1 de `/VBB`) y 32 vías de GND del bloque de poder sin plano.


### Celda3 añadida al esquemático (23 oct)
- Tercera instancia de `celda4.kicad_sch` en el esquemático raíz (hoja `Celda3`, página 4, bloque en (88,9; 292,1) bajo `Celda2`, 16 pines sin cablear). Referencias = las de la Celda1 + 200 (`R204`, `U201`, `C205`…). Netlist verificado: las 241 redes previas no cambian salvo `GND`, `+3.3V` y `+12V` que suman los pines nuevos; 68 redes nuevas `/Celda3/…`; 289 componentes sin referencias repetidas. Pendiente: **F8** en el PCB y copiar la disposición de la Celda1.

### Celda dorada simétrica (23 oct, en curso)
- **Decisión:** cada celda lleva 2 BTS a cada lado (canales 1 y 2 a la derecha, 3 y 4 a la izquierda) con la lógica compartida en el centro; se copiará trasladada, sin giros. **Cara superior:** 3 celdas (12 canales); **cara inferior:** 2 celdas de 4 con un BTS sin montar (7 controlados) más los 9 canales siempre activos (por definir celdas); la celda de la cara inferior será la misma volteada (F.Cu ↔ B.Cu, las capas internas no se intercambian) y en otra zona de XY que las de arriba.
- **Aplicado a la Celda1:** los canales 3 y 4 (30 footprints) se giraron 180° alrededor de (122,5; 132,05); las pistas que cruzaban hacia la lógica se borraron (quedan `IS3`, `IS4`, `FALLA3`, `FALLA4` por rutear). La Celda2 (en x 25–96) se apartó 120 mm en Y para no solapar. `U9` y su grupo (`C18`–`C20`, `R31`, `R32`) quedan en el centro-abajo, por reubicar.

### Ruteo de los grupos movidos y arquitectura (23 oct, tarde)
- **Decisión de arquitectura (usuario):** controlador (ESP32 + MCP) al centro con celdas arriba y abajo en la misma cara; 28 canales en 8 celdas de 4 (4 por cara; 4 BTS sin montar) o la distribución 12 arriba / 7 + 9 abajo. **Riesgo señalado:** el bus hacia el controlador (≈ 47 líneas) no tiene capa libre en 4 capas (In1 = GND, In2 = +3,3 V y señales internas, B.Cu = celdas de la otra cara); se recomendó un MCP23017 por celda (bus I²C) o pasar a 6 capas. Pendiente de confirmar.
- **Ruteo hecho por script (enrutador de rejilla propio, F.Cu + In2, pista 0,25 mm, espaciado ≥ 0,25 mm, columnas de tabs libres en F.Cu):** `IS3`, `IS4`, `FALLA3`, `FALLA4`, los 4 umbrales `U1A+`…`U1D+` y los pull-ups `R53`/`R54`, más 4 vías de plano (`C18`/`C19` a GND, `R31`/`R32` a +3,3 V). DRC a 0,25 mm sin errores en la celda; quedan solo los 7 de +12 V de los tabs y 2 de +3,3 V (pista del LED `D2`, isla de In2). Se probó Freerouting 2.5.0 (descargado al directorio temporal) pero dejaba pistas a 0,2 mm de los tabs y sin conectar 3–6 redes: se descartó.
- **Islas de +3,3 V en In2:** las pistas de señal de In2 encierran islas del plano (≈ 695, 134 y 19 mm²) con vías de +3,3 V; esas vías no llegan al plano principal y dependen de pistas de F.Cu. Conviene unirlas o mover señales de In2.

### Cara frontal: 3 celdas + controlador (23 oct)
- La celda dorada (Celda1, x 66–179, y 97,5–141) se copió por script a la **Celda2** (desplazada +113,5 mm en Y: y 211–254,7) y a la **Celda3** (+161,2 mm: y 258,7–302,4): 87 footprints, 549 pistas y 101 vías cada una, geometría idéntica a la entera, 0 problemas de paridad, 0 solapes de courtyard y 0 errores de espaciado nuevos (a 0,25 mm). Se borró el cobre antiguo de la Celda2 (la copia girada).
- **Disposición vertical (x común, centro lógico en x 107–140):** Celda1 (y 97–141) → controlador (`A1` ESP32 y 145–184, `U4` MCP y 188–207) → Celda2 → Celda3. La Celda3 no se pudo poner encima de la Celda1: chocaba con el bloque de poder (x ≤ 66). Los planos de GND (In1) y +3,3 V (In2) se extendieron a y = 310.
- Las líneas de la lógica hacia el controlador las rutea el usuario. Falta el `U5` (segundo MCP) aparcado fuera de la placa (x −25) y las celdas de la cara inferior.

### Revisión del estado a 26 oct (commit 173dab6)
- **Conexión micro ↔ celdas (esquemático raíz, etiquetas locales):** salidas `ESP32_OUT`: Celda1 → D23, D19, D18, TX2; Celda2 → D25, D26, D27, **D14**; Celda3 → D13, `U4` GPA0, GPA1, GPA2. Fallas `FALLA1–4`: Celda1 → RX2, D4, VP, VN; Celda2 → D34, D35, D32, D33; Celda3 → `U4` GPA3, GPA4, GPA5, GPA6. Quedan libres: `U4` GPB0–7 y GPA7 (etiqueta `U4-GPA7` sin conectar), todo `U5`, y los 12 pines directos seguros de la ESP32 están agotados. **Falta cablear** SDA/SCL, alimentación, `RESET` y direcciones de `U4`/`U5` y `VIN`/`GND`/`EN` de `A1`.
- **PCB:** contorno de 123 × 191 mm en Edge.Cuts (x −169,7…−46,7; y 25,95…217; línea 0,05 mm, sin radio); las 3 celdas, `A1` y `U4` dentro; **el bloque de poder, `J1`, `J2`, `U5` y `C6` (26 footprints) siguen fuera del contorno**. Las 505 pistas micro ↔ celdas ya están ruteadas; DRC sin errores y paridad 0; 25 conexiones sin rutear (12 de +12 V, 10 de GND, 2 de +3,3 V, 1 de `/VBB`).
- **Hallazgos abiertos:** (1) ~~2 grupos de pads de +3,3 V en la Celda2 (`U101` pin 3, `R103`, `R127`, `R153`, `R154`; `U102` pin 14, `R106`, `R128`, `R130`, `C104`) en islas de In2~~ (resuelto el 26 oct con 2 puentes de B.Cu de 0,5 mm, 10,6 y 5,4 mm; el DRC de KiCad no detecta estas islas porque trata la zona como un solo elemento, se comprueba con un análisis geométrico propio). (2) `U4` bloquea la tira de +12 V derecha. (3) Margen de solo ≈ 5 mm entre los pines de salida de los BTS y el borde. (4) 65 puntos de espaciado < 0,25 mm y 23 tramos de 0,2 mm de ancho (mínimo de JLCPCB a 2 oz: 8 mil = 0,2032 mm), sobre todo en los buses `U4-GPAx`. (5) Líneas de `U4` hacia la Celda3 de 160–215 mm. (6) `D14` (GPIO14) como salida: emite un pulso al arrancar.

### Revisión exhaustiva del 26 oct (d06c6f8)
- **Errores de esquemático que el ERC no marca:** la red `+12V` (Vbb de los 12 BTS) **no está unida** a `/VBB` (`J1`, `F2`); `/V3V3_OUT` (`U7`, `C15`) **no está unida** a `+3.3V`; `/VIN_ESP32` (`D6`) no llega al pin `VIN` de `A1`. Unir con símbolos/etiquetas globales (como se hizo con GND). Además faltan por cablear `A1` (`EN`, `GND`, `VIN`, SDA/SCL), `U4`/`U5` (`VDD`, `VSS`, SDA, SCK, `RESET`, `A0`–`A2`) y los pull-ups de SDA/SCL; 12 pines `MANUAL` y 12 `OUT` esperan conector.
- **PCB:** la tira de +12 V (pistas de 9 mm en F.Cu) ya existe en ambas columnas con travesaño en y = 211; 9 mm queda por debajo de los 11–13 mm calculados para 25–30 A / 5 s a 2 oz (ensanchar o añadir B.Cu). BTS en x ≈ −154,5 (izquierda) y −62 (derecha); margen de ≈ 5 mm entre sus pines y el borde.
- **Fabricación:** 23 tramos de 0,2 mm (`/VP`, `/VN`), 65 espaciados < 0,25 mm (53 a 0,200 mm), 62 tramos fuera de 0/45/90°, 6 vías sueltas en las celdas, 52 + 35 avisos de serigrafía, 96 pares de courtyard a < 0,2 mm. BOM sin MPN/LCSC. Sin taladros de montaje ni puntos de prueba. Los 26 footprints fuera del contorno (bloque de poder, `J1`, `J2`, `U5`, `C6`) se pasarán a la cara inferior.

### Cara inferior: Celda4 y Celda5 (26 oct)
- **Plan de celdas (7 en total, 28 canales):** cara frontal Celda1–3 (12 canales controlados). Cara inferior: **Celda4** (4 controlados) y **Celda5** (3 controlados + su canal 4, `U411`, como **salida directa/siempre activa**: su `ESP32_OUT4` va a +3,3 V desde la raíz) = 7 controlados; las 9 salidas directas restantes: canal 4 de la Celda5 + **Celda6 y Celda7** (8 canales, todos con `ESP32_OUT` a +3,3 V). Así no queda ningún BTS sin montar.
- **Hecho por script:** hojas `Celda4` y `Celda5` añadidas al esquemático raíz (páginas 5 y 6, referencias +300/+400: `U303`, `U308`, `U310`, `U311` y `U403`, `U408`, `U410`, `U411`), con sus pines sin cablear; en el PCB se crearon los 87 footprints de cada una como **copia volteada de la celda dorada en B.Cu** (espejo respecto al eje vertical de la celda; F.Cu ↔ B.Cu, In1/In2 se mantienen) con 556 pistas y 101 vías, **aparcadas debajo del contorno** (Celda4 en y ≈ 235–279, Celda5 en y ≈ 284–328). Paridad 0; DRC sin errores con las reglas del proyecto. Pendiente en cada una: GND/+3,3 V (sin planos allí), 1 conexión de `FALLA4`, +12 V.
- **Aviso:** las celdas de la cara inferior comparten In2 e In1/In2 con las de arriba: no pueden superponerse con ellas sin 6 capas, y las vías de arriba (343) ocupan B.Cu bajo cualquier componente que se coloque abajo.

### Celda4 y Celda5 colocadas y ruteadas en B.Cu (27 oct)
- **Colocación:** Celda4 con su borde superior en y≈116 mm y Celda5 debajo (separación 4 mm, termina en y≈207 mm), desplazadas +2,9 mm en x respecto al espejo rígido. Cada huella se legalizó para que sus pads no caigan sobre vías, THT ni cobre de las celdas de arriba (vías de paso: atraviesan todas las capas). Los pads +12 V de los BTS se mantienen ≥0,3 mm de las vías de arriba; los 74HC132/LM339 llevan holgura extra para poder salir.
- **Ruteo (script propio de rejilla, vías conscientes de todas las capas):** capas B.Cu e In2; pista 0,25 mm y espaciado 0,25 mm; vía 0,6/0,3 solo donde F.Cu, In2 y B.Cu están libres, separadas ≥0,8 mm entre taladros y sin vías en pads; +12 V con 0,3 mm. 124 vías de plano (GND/+3,3 V, una por pad SMD) + ~130 de señal. Las conexiones que no cabían a 0,25 mm se rescataron a 0,2/0,2 mm (mínimo del proyecto; JLC 2 oz exige 0,2032 mm: por verificar).
- **Planos:** las pistas de In2 pueden partir el plano +3,3 V; un analizador geométrico (`conn33`) detectó grupos aislados y se unieron al plano principal con pistas de +3,3 V (11 puentes). Resultado: 0 grupos aislados. *Nota:* DRC de KiCad no detecta estas islas (trata la zona como un solo elemento).
- **DRC con reglas del proyecto:** sin cortos, sin holguras ni hole-to-hole nuevos, 0 vías en pad nuevas. Quedan 2 `courtyards_overlap` (pares THT `R349/R351`… y `R401/R451`, igual que las celdas de arriba) y los 3 errores del bloque de potencia (ver abajo).
- **Pendiente de estas celdas:** 4 conexiones sin rutear en la Celda4 (pines de `U301`/`U302`/`U309`: `Net-(R303-Pad1)`, `Net-(R353-Pad1)`×2, `Net-(U301D--)`); las tiras de +12 V de las columnas de BTS inferiores (24 conexiones); líneas lógicas hacia el micro y FALLA4 interna; unificar las redes de poder (a cargo del usuario).
- **Bloque de potencia (B.Cu, movido por el usuario):** alcanza la zona de la Celda1 (y<73 mm) y provoca 2 cortos + 1 holgura (`Net-(U1B--)` en In2 contra la vía GND (−91,62); vía `Net-(U1B--)` (−77,62) contra la pista `Net-(D6-A)`). Bajar el bloque ~6–8 mm o rerutear `D6-A`.

### Pendiente — esquemático
- [ ] **Conectar `A1`, `U4` y `U5`** según la sección 6 (SDA/SCL, pull-ups, `RESET` a 3.3V, direcciones 0x20/0x21, desacoples de 100 nF, alimentación del devkit por `VIN`, no conectar `3V3`).
- [ ] Asignar qué canal va a qué salida/entrada (tabla canal → salida y canal → entrada de falla) siguiendo el reparto de la sección 6.
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
- [ ] Revisar el margen de `IN` alto (peor caso ~2,4 V frente a 2,2 V mínimos): considerar diodo de menor Vf o menor valor de `R4`/`R5` (el datasheet recomienda 4.7k).
- [ ] Verificar la huella `TO-263-7_TabPin4` contra el plano de PG-TO263-7-10.
- [ ] Verificar el código de pedido y rango de temperatura del MCP23017 (`-E/SO`), y los alias de GPIO del devkit con la placa física.
- [ ] Elegir MPN concretos de cada componente para el ensamblador (marca conocida para BAT54C, MMBT2222A; verde estándar ~2,1 V; electrolíticos SMD) y generar BOM + archivo de colocación.

### Configuración del PCB ya aplicada (22 oct 2026)
- **Stackup** (en `.kicad_pcb`): 4 capas, 1,6 mm; cobre exterior **2 oz** (70 µm) en F.Cu y B.Cu; interior 0,5 oz (17,5 µm) en In1.Cu e In2.Cu (estándar JLCPCB). Espesores de dieléctrico aproximados: los reales los fija el fabricante al cotizar. Acabado superficial por decidir.
- **Reglas** (en `.kicad_pro`): pista y espaciado mínimos 0,2 mm (JLCPCB exige > 8 mil con 2 oz); vía 0,6/0,3 mm; anillo mínimo 0,15 mm; borde 0,3 mm.
- **Clases de red:** `Default` 0,25 mm; `Potencia_12V` 2,5 mm (10 A continuos a 2 oz ≈ 2,4 mm), espaciado 0,3 mm, vías 0,8/0,4 (redes `/VBB`, `+12V`); `Entrada_Logica` 1,0 mm (rama de lógica < 0,5 A: `Net-(D4-*`, o sea `VIN_F` y `VIN_D`); `Conmutacion` 0,5 mm (`Net-(U6-SW)`); `Potencia_5V_3V3` 0,5 mm (`Net-(D6-A)`, `/VIN_ESP32`, `/V3V3_OUT`, `+3.3V`, `+5V`). Los picos de 25–30 A / < 5 s van en **zonas de cobre** de 11–13 mm de ancho (2 oz), no en pistas. Los patrones dependen de los nombres de red actuales; revisarlos al unir las etiquetas con el circuito.
- Corriente continua máxima confirmada por el cliente: **10 A**.
- Estado a 22 oct (6.ª revisión): DRC **solo** marca el contorno que falta (0 errores de taladro, 0 `hole_to_hole`, 0 problemas de paridad). `CIN`: `C7` a 4,6 mm de pista del VIN de `U6` (cumple), `C8` a 8,3 mm (secundario); `SW`–`L1` 6,2 mm; vías de GND (32) bien separadas; uniones de GND de 1 mm en `C7`, `C8`, `C11`, `C9`, `U6` pin 1. Pendiente: contorno (`Edge.Cuts`) y redibujar el plano; reforzar vías del TVS; zonas de +12 V; BTS y resto del circuito sin rutear (48 conexiones); unir el bloque al esquemático (VBB, GND_PWR, VIN_ESP32, V3V3_OUT).

### Pendiente — PCB
- [ ] El `.kicad_pcb` está **vacío** (no se ha iniciado). Cuando empiece: 4 capas, componentes a ambas caras, potencia y tierra en planos internos, **tierra de potencia vs lógica** (la medición de `IS` es sensible a caídas de tensión en GND), pistas gruesas para los BTS y disipación (TO-263), `R1` THT accesible para soldar a mano.
- [ ] **Desacoples (`C2`, `C4`, el de `U4`) lo más cerca posible de los pines de alimentación** de cada integrado, con pistas cortas.
- [ ] **Conectar el bloque de alimentación** al resto con etiquetas: `VBB` (a Vbb de los BTS), `GND_PWR` (a GND), `VIN_ESP32` (a `A1` pin 15), `V3V3_OUT` (a +3.3V). Definir huella del fusible master (`F1`) y decidir el TVS de Vbb.
- [ ] **Bus de potencia de +12 V (25–30 A en picos de < 5 s):** zonas anchas en capas externas (ver cálculo en sección 7), vías abundantes en cada cambio de capa, terminal M6 (M5 posible, por verificar según el terminal) + portafusible cerca de los BTS; definir conectores de salida por canal (corriente por canal por preguntar).
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
9. Falla hacia el ESP32 (cambió el requisito inicial): se evaluó analógico con resistencias escalonadas y se **descartó** a favor de lectura digital con un segundo MCP23017.
10. ESP32 devkit de 30 pines en zócalo (símbolo/huella propios) + MCP23017 #1 (salidas) + 8 salidas directas; `RESET` de los MCP a 3.3 V; MCP23017 #2 (`U5`, 0x21) para las entradas de falla.
11. Regulador opción A (buck 12→5 V + LDO 3.3 V) — por diseñar.
