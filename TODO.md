# TODO — Fusilera 24 canales (rama `separate-boards`)

Estado al 10 nov 2026. Las casillas marcadas `[x]` están hechas; el contexto de cada punto está en `docs/`.

## Decisiones y preguntas para el cliente

- [ ] **Reinicio del latch.** Con la lógica siempre en batería, un canal disparado se queda disparado hasta desconectar la batería. Ideas en `docs/ign-llave.md`: reinicio por flanco de IGN (recomendado), línea `LATCH_RST` desde el ESP32 por el pin 14 de `J10`, botón de servicio. Preguntar: ¿reinicio automático al encender el carro?, ¿puede el usuario resetear sin apagar?
- [x] **Fusible master `F1`**: portafusibles del cliente (40 A) sobre dos pestañas Faston .187; esquemático y huella hechos (`docs/fusible-master.md`).
- [ ] **Corriente de las pestañas `F1`**: confirmar la corriente nominal de la pestaña soldada (TE 1217133-1 u otra) y la corriente continua máxima del cliente.
- [ ] **Partir el cobre en `F1`** (master y slave): `J1` → pad 1 de `F1`; pad 2 → tronco y tiras de +12 V; medir el cuerpo del portafusibles para la huella.
- [ ] **TVS de Vbb** (y confirmar si hace falta uno en la línea de IGN).
- [ ] Corriente de la línea de IGN y tipo de cable, para confirmar el valor de `F901` (500 mA provisional).
- [ ] Confirmar con el cliente que ninguna carga retorna por la placa (el terminal de GND solo lleva la lógica).

## Esquemático

- [x] Conectores `J4` (salidas) y `J5` (manuales) en las dos raíces (`docs/conectores-io.md`).
- [ ] Confirmar con el cliente cuáles canales son los 4 vidrios y comprar conectores/terminales (carcasas y terminales HCS aparte).
- [ ] Añadir `F1` y el TVS (con huella provisional, ver `docs/ign-llave.md` y `docs/avisos-electricos.md`).
- [ ] Decidir si el conector de enlace `J10` es JST XH / Micro-Fit con pestillo o regleta tipo shield (hoy huella provisional JST XH).
- [ ] `EN` del ESP32 queda sin conectar (el devkit ya trae su pull-up): confirmar.
- [ ] Script que compare las redes de `J10` en ambos esquemáticos.

## PCB master (`placa-master`)

- [ ] **Plano de +3,3 V (In2) en 9 islas**, unido solo por pistas de 0,5 mm en F/B. Sacar las señales largas (`FALLAk`/`ESP32_OUTk`) de In2 a B.Cu si hay tiempo o aparece ruido.
- [ ] Terminales de ojo `J1` (M6) y `J2` (M5): los centros están a 12,8 mm; comprobar que no choquen con los terminales reales. `J2` queda a 0,62 mm del borde.
- [ ] Tiras de +12 V en 9 mm (decidido): confirmar la corriente continua; opciones: abrir máscara y estañar, pour espejo en B.Cu.
- [ ] Quedan 3 vías y 9 pistas `MANUAL` colgantes (se cierran al definir los conectores).
- [ ] Alinear las celdas 2 y 3 (desplazadas 0,15 y 0,12 mm en x) si se regenera la master.
- [ ] Verificar que el largo del devkit (≈ 51 mm) no choca con `U4` en el modelo 3D (el USB queda hacia el borde izquierdo).

## PCB slave (`placa-slave`)

- [ ] Borrar las 2 vías de `3V3_IGN` colgantes en (16,6; 85,5) y (18,4; 66,4).
- [ ] Plano de +3,3 V de In2 en 4 islas (la de 565 mm² de la celda 4 se mantiene por pistas): dejarlo o sacar señales de In2.
- [ ] `Net-(U6-FB)` mide 27 mm a 0,25 mm (nodo sensible del buck): acortar o alejar de `SW`.
- [ ] `3V3_IGN` mide ≈ 195 mm (mínimo teórico ≈ 121 mm): opcional acortarla.
- [ ] Confirmar disponibilidad en JLCPCB del `AO3401A` (`Q901`) y de `MMBT2222A` / `1N4148W`.
- [ ] Contorno: la slave mide 106 mm de ancho y la master 94,5 mm; igualarlos para el apilado.
- [ ] Verificar el balance térmico y el presupuesto de +3,3 V del LDO (`AP2112K`, θJA por confirmar en la hoja oficial) con la corriente real de las 28 celdas.

## Ambas placas

- [ ] Serigrafía: 60 avisos de serigrafía sobre cobre, 86 solapada y 21 de altura (rótulos de 0,7 mm; JLCPCB recomienda ≥ 1,0 mm). Heredado de la celda dorada: corregirlo allí.
- [ ] Colocar `J4`/`J5` (aparcados fuera del contorno) en una fila bajo `J1`/`J2`, ampliar el contorno y rutear `OUTk` (≈ 3 mm vidrios, ≈ 1 mm resto) y `MANUALk`; con eso se cierran las pistas y vías `MANUALk` colgantes.
- [ ] Revisar el aviso de retroalimentación entre placas (`docs/avisos-electricos.md`, punto 1).
- [ ] Verificar el pinout de `J10` en ambos esquemáticos con un script.

## Celda dorada (`celda/`)

- [ ] Rótulos de 0,7 mm de la serigrafía (8) y los 3 elementos colgantes que quedan.
- [ ] Contorno `Edge.Cuts` de la celda (119,6 × 48,2 mm frente al contenido real).
- [ ] Si se toca cobre de una celda en una placa, llevar el cambio a `celda/` y volver a generar la slave (la master tiene ruteo manual y no se regenera).

## Repositorio

- [ ] Etiquetar `main` como `doble-cara-v1`.
- [ ] Eliminar `legacy/` cuando las dos placas estén listas.
- [ ] Mensaje del commit `582d215` menciona `CLAUDE.md` (decidir si se reescribe; requeriría forzar el push).
- [ ] Mantener `CONTEXTO_PROYECTO.md` al día cuando cambien decisiones, BOM o pendientes (sección de BOM sin las piezas de IGN).

## Hecho recientemente

- [x] Esquemáticos raíz generados y cableados (alimentación, I²C, bloque de poder).
- [x] Tiras de +12 V, reruteos y vías de la celda 1 llevados a `celda/` y replicados por `replicar_celdas_pcb.py`.
- [x] Slave en columna, raíz colocada y ruteada, sin conexiones abiertas (0 sin conectar, sin cortos).
- [x] Interruptor de +3,3 V por IGN (`3V3_IGN`, canales 25–28) en esquemático y PCB.
- [x] `LINK_5V` a 0,5 mm en la slave y en la master; GND abierto y vía de `FALLA2` corregidos en la master.
