# Revisión del PCB de la master (30 oct 2026)

Revisión de `placa-master/placa-master.kicad_pcb` tal como quedó tras los ajustes manuales hechos en KiCad (commit `8dcaf03`), comparada con la versión generada por `herramientas/replicar_celdas_pcb.py`. No se modificó ningún archivo; esto son solo observaciones.

## Qué se hizo a mano

- Contorno nuevo de **94,5 × 170 mm** (x 5,5…100; y −108…62). Las 3 celdas van en **columna** (paso 38,62 mm, separación 3,2 mm) en vez de en fila.
- Raíz arriba: `A1` (ESP32), `U4`, `J10`, `U7`/`C14`/`C15`/`C6`/`D6`, `R901`/`R902`. `J1` (+12 V, M6) y `J2` (GND, M5) abajo.
- Las **tiras de +12 V** (9 mm en F.Cu: una por lado, unidas por un tronco inferior que sale de `J1`) y el ruteo de las huellas de la raíz.

## Estado medido

- DRC con paridad y relleno de zonas: **0 errores de paridad**, sin errores de espaciado ni cortos; 98 violaciones: 42 `silk_overlap`, 31 `silk_over_copper`, 12 `text_height`, 9 `track_dangling`, 4 `via_dangling` y 1 `unconnected_items`.
- Todo el +12 V y la señalización de la raíz están conectados.
- Si el relleno de zonas está desactualizado al guardar, `kicad-cli` muestra 8 falsos errores de espaciado vía–plano; se van al rellenar (B) y guardar.

## Observaciones

1. **Las celdas ya no son copias de la dorada.** El reruteo interno es distinto en cada celda (por ejemplo `Net-(Q4-C)`, `Net-(U1B--)`, `FALLAk`, `ESP32_OUTk`), y `celda/` no lo tiene. La slave no lo heredará y volver a generar la master lo pierde. Decidir si se lleva a la celda dorada.
2. **Desalineación en x** de las celdas 2 y 3: 0,15 y 0,12 mm respecto de la celda 1. Las tiras de +12 V tienen por eso pequeños quiebres de 0,1–0,2 mm.
3. *(decidido 31 oct: se dejan en 9 mm)* **Ancho de las tiras de +12 V.** 9 mm en 2 oz y una sola capa equivale a ΔT ≈ 60 K para 25–30 A durante < 5 s según `CONTEXTO_PROYECTO.md` (para ΔT 30–40 K pedía 11–13 mm). El tronco inferior lleva la corriente de la tira derecha. Opciones: abrir máscara y estañar, pour espejo en B.Cu con vías, o ensanchar. Falta confirmar la corriente continua con el cliente.
4. *(31 oct: se dejan así, por revisar con los terminales reales)* **Terminales.** `J1` (pad 12,8 mm) y `J2` (pad 10,6 mm) tienen los centros a 12,8 mm; con terminales de ojo reales M6/M5 pueden chocar entre sí. El pad de `J2` queda a 0,62 mm del borde. *Por verificar con los terminales elegidos.*
5. **Plano de +3,3 V (In2) fragmentado** en 9 islas (4 en la versión generada) por las señales que cruzan In2. Hoy todas las islas tienen una vía de +3,3 V y la conectividad se sostiene con pistas de 0,5 mm en F/B, pero el plano ya no es un plano. GND (In1) sigue en una sola isla.
6. ✅ *(corregido 31 oct: vía de GND sobre la pista `C15.2`–`C6.2`)* **1 conexión de GND abierta** cerca de `C14`/`C15`/`C6`: dos tramos de pista entre (88,8; −79,1) y (91; −76) en F.Cu.
7. **Restos del reruteo:** ✅ vía `/FALLA2` sobrante en (89,6; 10,3) borrada (31 oct); quedan 3 vías `/MANUAL` y 9 pistas `/MANUAL` colgantes (estas son de los conectores `MANUALk`, aún sin definir).
8. ✅ *(corregido 31 oct: `LINK_5V` a 0,5 mm salvo el rodeo junto al pad 2 de `U7`, que sigue a 0,25 mm por espaciado)* **Anchos:** `LINK_5V` va a 0,25 mm (alimenta el LDO y el ESP32 a través de `D6`); conviene 0,5 mm. `SDA`/`SCL` a 0,25 mm están bien.
9. **Serigrafía:** siguen los 42/31/12 avisos de la celda dorada (rótulos de 0,7 mm; mínimo recomendado de JLCPCB 1,0 mm).
10. **Pendiente de definir:** fusible `F1`, TVS, conectores `MANUALk`/`OUTk`, y confirmar de qué lado queda el USB del devkit (hoy `VIN` está a la izquierda, junto al borde).
