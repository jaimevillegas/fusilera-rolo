# Conectores de E/S hacia el arnés (`J4` y `J5`)

Decisión (10 nov 2026): un conector de salidas de los BTS y otro de entradas manuales por placa, uno al lado del otro en la parte inferior, para cableado interno de caja. Las cargas retornan por el chasis, así que cada salida usa un solo pin.

## Corrientes

- Vidrios: 4 canales (cuáles los decide el cliente en el montaje). Estimación de diseño ≤ 10 A por vidrio; peor caso 15 A con dos a la vez (estimación alta).
- Luces, bocina y switches: sin carga significativa.
- Mini-Fit Jr: 9 A (rating conservador) a 13 A por circuito con terminales HCS (`45750`) y cable de 16 AWG. Los 4 vidrios a 10 A caben con HCS; el pico de 15 A es corto. Pistas de las salidas: ≈ 3 mm para los vidrios y ≈ 1 mm para el resto (2 oz, por verificar con las cargas reales).

## Conectores

| Placa | `J4` salidas BTS (`OUTk`) | `J5` manuales (`MANUALk` + 3,3 V + GND) |
|---|---|---|
| Master | Mini-Fit Jr 2 × 6, `5569-12A2` (Molex 39-30-1120): `OUT1…12` en los pines 1…12 | Micro-Fit 3.0 2 × 7, `43045-1400`: `MANUAL1…12` en 1…12, `+3,3 V` en 13, GND en 14 |
| Slave | Mini-Fit Jr 2 × 8, `5569-16A2` (Molex 39-30-1160): `OUT13…28` en los pines 1…16 | Micro-Fit 3.0 2 × 9, `43045-1800`: `MANUAL13…28` en 1…16, `+3,3 V` en 17, GND en 18 |

Lado cable (se compra aparte y se crimpa): carcasa `39-01-2125` (12) / `39-01-2165` (16) con terminales `45750-3112` (HCS, 16 AWG); carcasa `43025-1400` (14) / `43025-1800` (18) con terminales `43030-0001` (20–24 AWG). Los pines van en el orden del símbolo `Conn_02xNN_Top_Bottom` (fila 1 = pines 1…N/2, fila 2 = el resto, como un ATX).

## Estado (10 nov)

- Esquemáticos de master y slave actualizados con `herramientas/generar_raiz.py`; el ERC ya no tiene etiquetas sueltas de `OUTk`/`MANUALk`.
- PCB: las huellas `J4` y `J5` están **aparcadas fuera del contorno** (a la derecha). Falta colocarlas en una fila bajo `J1`/`J2` (en la slave no caben en la misma fila que `J1`/`J2`), ampliar el contorno y rutear.
- Ensamblaje: los conectores de placa son THT; la hembra (carcasa y terminales) va aparte. Se propone soldar los 4 conectores a mano y pedir solo el ensamblaje SMD. Disponibilidad en JLCPCB: por confirmar.
- Distribución sugerida de pines: no poner los 4 vidrios en pines contiguos del mismo conector.
