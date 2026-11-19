# Módulo de poder (`modulo-poder/`)

Placa aparte con el bloque de poder de la slave: entra la tensión del carro (12 V) y sale 5 V y 3,3 V para microcontroladores e integrados. Esquemático, proyecto y PCB de **dos capas** generados con `herramientas/generar_modulo_poder.py`; el PCB trae las 26 huellas **dispersas, sin pistas, sin contorno y sin planos** (el cobre y el contorno los haces tú).

## Circuito

`J1`/`J2` (bornes M3 de +12 V y GND) → `F2` (fusible 2 A) → `RT1` (NTC limitador de corriente de arranque) → `D4` (Schottky SS36, polaridad inversa) → red `VIN_D`, con `D5` (TVS), `CB1` (1000 µF), `C9` (47 µF 50 V), `C7`/`C8` (2,2 µF 100 V) → `U6` LM5164 (buck, 5 V, 1 A, `L1` 22 µH) → `U7` AP2112K-3.3 (LDO, 3,3 V, 600 mA).

Salida por **`J3`, regleta JST XH de 4 pines**: 1 = +5 V, 2 = GND, 3 = +3,3 V, 4 = GND. El `PGOOD` del LM5164 queda **sin conectar** (decisión del 19 nov: no sale por la regleta). Las redes del bloque son las mismas que las de la slave (se verificó con el netlist); solo cambian lo añadido: `RT1`, `CB1` y la regleta.

## Condensador de 1000 µF (`CB1`)

Va **después** del diodo `D4` (no en el borne), para que durante una caída de tensión del arranque el diodo impida que el condensador se descargue hacia el carro y sostenga la entrada del buck. (Cambiado de 10000 µF a 1000 µF el 19 nov.) Estimación: de 12 V a 6 V un condensador de 1 mF entrega ≈ 0,054 J, lo que da del orden de 9 ms a plena carga del buck (≈ 6 W de entrada) y unos 50 ms con una carga de 1 W. Es una décima parte de lo que daba el de 10000 µF; las caídas del arranque suelen durar decenas de milisegundos, así que conviene validarlo con la carga real. El LM5164 deja de regular por debajo de ≈ 6 V.

Por dimensionar:
- **Tensión y huella del condensador:** 35 V, huella radial **D10 mm, paso 5,0 mm** (`CP_Radial_D10.0mm_P5.00mm`), la medida habitual de un 1000 µF / 35 V (ejemplo: Rubycon 35PK1000MEFC10X20, 10 × 20 mm, paso 5 mm; *comprobar la altura real en la hoja del modelo elegido*). Se giró 270° dejando el pad + donde estaba, para no mover el ruteo.
- **TVS `D5`:** puesto `SMBJ24A` (provisional, por verificar); recorta ≈ 39 V.
- **Corriente de arranque:** al conectar la batería el condensador absorbe un pico grande; sin límite, con una fuente de ≈ 30 mΩ la I²t de la carga sería del orden de 2 A²s (estimación), muy por encima de lo que aguanta un fusible 1206 de 2 A. Por eso `RT1` (NTC de 10 Ω, 3 A, provisional) reduce esa I²t a ≈ 0,007 A²s. Comprobar con el fusible elegido.

## Pines de `PGOOD` y `EN` del LM5164

- **`PGOOD`**: salida de colector abierto que se mantiene baja mientras los 5 V no están dentro del margen de regulación y pasa a alta impedancia cuando están bien. Queda sin conectar y sin pull-up (se quitó `R20`).
- **`EN`/UVLO**: habilita el convertidor. `R17`/`R18` forman un divisor desde la entrada que fija a qué tensión de entrada arranca; si se baja ese pin a GND, el buck se apaga. No sale a la regleta.

## Conector común: JST XH (2,5 mm)

Para todas las señales digitales de baja corriente propongo la familia **JST XH**: la misma que usa `J10` de las placas. Tiene versiones de 2, 3, 4… hasta 16 y más pines, 2,5 mm de paso, polarizada, 3 A y 250 V por pin. Ejemplo: [B4B-XH-A (LF)(SN), 4 pines, LCSC C144395](https://www.lcsc.com/product-detail/C144395.html) y [en JLCPCB](https://jlcpcb.com/partdetail/B4B-XH-A(LF)(SN)/C144395) (pieza extendida, THT por soldadura de ola). El resto de pines (2P, 8P, 12P…) son la misma familia: *no pude confirmar su disponibilidad en JLCPCB, hay que revisarla*. El lado cable es la carcasa `XHP-n` con terminales `SXH-001T-P0.6` (*números por verificar en la hoja de JST*).

## Contorno y fijación

Placa de **55,55 × 39,8 mm** con **4 orificios M3** (taladro de 3,2 mm, huella `MountingHole_3.2mm_M3`, sin plaquear) en las esquinas, a 3,5 mm de cada borde: `H1`…`H4`. Se ensanchó respecto a los 48 mm originales porque `J1` y `J3` ocupaban dos esquinas (se probó con 62 mm y se recortó a 55,55 mm moviendo `J1`, `J2` y `F2`); los planos de GND cubren todo el ancho. Las huellas de los orificios son solo del PCB (no están en el esquemático).

## Pendiente
- Colocar, contornear y rutear el PCB de dos capas.
- Confirmar tensión del `CB1`, valor del TVS y del NTC, y la I²t del fusible.
- Medir la altura (el condensador `CB1` es la pieza más alta) y ajustar la huella si se cambia de modelo.
- Si el módulo sustituye al bloque de la slave, rehacer entonces la slave (por ahora no se toca).
