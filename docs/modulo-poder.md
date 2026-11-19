# Módulo de poder (`modulo-poder/`)

Placa aparte con el bloque de poder de la slave: entra la tensión del carro (12 V) y sale 5 V y 3,3 V para microcontroladores e integrados. Esquemático, proyecto y PCB de **dos capas** generados con `herramientas/generar_modulo_poder.py`; el PCB trae las 26 huellas **dispersas, sin pistas, sin contorno y sin planos** (el cobre y el contorno los haces tú).

## Circuito

`J1`/`J2` (bornes M3 de +12 V y GND) → `F2` (fusible 2 A) → `RT1` (NTC limitador de corriente de arranque) → `D4` (Schottky SS36, polaridad inversa) → red `VIN_D`, con `D5` (TVS), `CB1` (10000 µF), `C9` (47 µF 50 V), `C7`/`C8` (2,2 µF 100 V) → `U6` LM5164 (buck, 5 V, 1 A, `L1` 22 µH) → `U7` AP2112K-3.3 (LDO, 3,3 V, 600 mA).

Salida por **`J3`, regleta JST XH de 4 pines**: 1 = +5 V, 2 = GND, 3 = +3,3 V, 4 = GND. El `PGOOD` del LM5164 queda **sin conectar** (decisión del 19 nov: no sale por la regleta). Las redes del bloque son las mismas que las de la slave (se verificó con el netlist); solo cambian lo añadido: `RT1`, `CB1` y la regleta.

## Condensador de 10000 µF (`CB1`)

Va **después** del diodo `D4` (no en el borne), para que durante una caída de tensión del arranque el diodo impida que el condensador se descargue hacia el carro y sostenga la entrada del buck. Estimación: de 12 V a 6 V un condensador de 10 mF entrega ≈ 0,54 J, lo que da del orden de 90 ms a plena carga del buck y bastante más con la carga real. El LM5164 deja de regular por debajo de ≈ 6 V.

Por dimensionar:
- **Tensión del condensador:** puesto como 35 V (huella radial D18 mm, paso 7,5 mm, ≈ 18 × 40 mm). Con 25 V sería más pequeño, pero debe resistir el recorte del TVS.
- **TVS `D5`:** puesto `SMBJ24A` (provisional, por verificar); recorta ≈ 39 V.
- **Corriente de arranque:** al conectar la batería un condensador de 10 mF absorbe un pico enorme; sin límite fundiría el fusible o haría chispa en el borne. Por eso añadí `RT1` (NTC de 10 Ω, 3 A, provisional). Hay que comprobar que `F2` (1206, 2 A) aguanta la I²t de la carga del condensador; si no, usar fusible lento o ajustar el NTC.

## Pines de `PGOOD` y `EN` del LM5164

- **`PGOOD`**: salida de colector abierto que se mantiene baja mientras los 5 V no están dentro del margen de regulación y pasa a alta impedancia cuando están bien. Queda sin conectar y sin pull-up (se quitó `R20`).
- **`EN`/UVLO**: habilita el convertidor. `R17`/`R18` forman un divisor desde la entrada que fija a qué tensión de entrada arranca; si se baja ese pin a GND, el buck se apaga. No sale a la regleta.

## Conector común: JST XH (2,5 mm)

Para todas las señales digitales de baja corriente propongo la familia **JST XH**: la misma que usa `J10` de las placas. Tiene versiones de 2, 3, 4… hasta 16 y más pines, 2,5 mm de paso, polarizada, 3 A y 250 V por pin. Ejemplo: [B4B-XH-A (LF)(SN), 4 pines, LCSC C144395](https://www.lcsc.com/product-detail/C144395.html) y [en JLCPCB](https://jlcpcb.com/partdetail/B4B-XH-A(LF)(SN)/C144395) (pieza extendida, THT por soldadura de ola). El resto de pines (2P, 8P, 12P…) son la misma familia: *no pude confirmar su disponibilidad en JLCPCB, hay que revisarla*. El lado cable es la carcasa `XHP-n` con terminales `SXH-001T-P0.6` (*números por verificar en la hoja de JST*).

## Pendiente
- Colocar, contornear y rutear el PCB de dos capas.
- Confirmar tensión del `CB1`, valor del TVS y del NTC, y la I²t del fusible.
- Medir la altura (el condensador de 10000 µF es la pieza más alta) y ajustar la huella si se cambia de modelo.
- Si el módulo sustituye al bloque de la slave, rehacer entonces la slave (por ahora no se toca).
