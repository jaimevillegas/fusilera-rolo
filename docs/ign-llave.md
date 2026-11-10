# Canales directos dependientes de la llave (IGN)

Requisito del cliente (5 nov 2026): master y slave van conectadas a la **batería** (con tensión aunque el carro esté apagado). Cuatro de los BTS directos solo deben activarse cuando se enciende el switch del carro; el cliente entrega una línea de 12 V que solo tiene tensión con el switch.

Decisiones (5 nov): los canales son el **25 al 28** (celda 7 de la slave); `MANUALk` sigue funcionando por el OR aunque no haya IGN; el borne de IGN es un orificio con tornillo **M3**, como el de +12 V pero más pequeño (solo lleva la señal de control, no la corriente de las cargas, que sale de la tira de +12 V).

## Circuito (slave, `placa-slave.kicad_sch`)

`3V3_IGN` es un interruptor P-MOS de +3,3 V comandado por la línea de la llave. Reemplaza al amarre a +3,3 V de `ESP32_OUT25…28`.

| Ref | Valor | Función |
|---|---|---|
| `J3` | borne M3 (`MountingHole_3.2mm_M3_Pad`) | entrada de la línea de 12 V de la llave (`IGN`) |
| `F901` | 500 mA, 1206 | fusible de la línea (valor por confirmar) |
| `D901` | 1N4148W, SOD-123 | polaridad inversa |
| `R904` / `R905` | 100 kΩ / 47 kΩ | base de `Q902` y pull-down (apagado con la línea flotante) |
| `Q902` | MMBT2222A | baja la puerta de `Q901` cuando hay IGN |
| `R903` | 100 kΩ | puerta de `Q901` a +3,3 V (apagado por defecto) |
| `Q901` | AO3401A (P-MOS, SOT-23) | entrega +3,3 V a `3V3_IGN` |

Umbral de encendido de la línea: ≈ 2,6 V (0,6 V del diodo + 0,65 V de la base con el divisor 100 k / 47 k). La carga son los OR de los 4 canales: ≈ 30–50 µA por canal. Datasheet del BTS50010-1TAD (Rev. 1.2): entrada `IN` -0,3 V…V_S, ±5 mA; los parámetros se dan con V_IN ≥ 2,2 V (encendido) y ≤ 0,8 V (apagado). *Por verificar*: disponibilidad en JLCPCB del AO3401A y el valor del fusible según el cable del cliente.

## Estado

- Esquemático de la slave actualizado con `herramientas/generar_raiz.py` (ERC sin avisos nuevos salvo 2 `lib_symbol_mismatch` de los símbolos nuevos).
- `placa-slave.kicad_pcb`: las 8 huellas nuevas están **aparcadas fuera del contorno** (a la derecha), sin rutear; los pads de `R605`, `R620`, `R638` y `R640` (pin 2) y las pistas que ya tenían `R638`/`R640` pasaron a la red `/3V3_IGN`. Falta colocar las piezas, rutear `IGN`, el interruptor y la red `3V3_IGN` hasta esos 4 pads, y cerrar las demás conexiones de +3,3 V abiertas de la slave.

## Pendiente para hablar con el cliente: reinicio del latch

El latch (74HC132) de cada canal solo se reinicia al quitar la alimentación (RC `R6`/`C3` de encendido). Con la lógica siempre en batería, un canal disparado se queda disparado hasta desconectar la batería. Ideas para proponer:

1. **Reinicio por flanco de IGN (solo hardware, recomendado):** un pulso bajo a la entrada de reset de todos los latches cada vez que la llave pasa de apagado a encendido. Reproduce el comportamiento original (reiniciar al ciclar el carro). Requiere una red común `LATCH_RST` en las dos placas (el pin 14 de `J10`, hoy de reserva, podría llevarla de la slave a la master).
2. **Reinicio desde el ESP32:** una línea `LATCH_RST` activada por firmware (también por el pin 14 de `J10`), por ejemplo tras apagar la carga, con un comando o al cambiar de estado de IGN. Se puede combinar con la 1 (OR).
3. **Botón de servicio:** un pulsador que baje `LATCH_RST`, para banco y mantenimiento.
4. **Reinicio por canal:** requeriría una línea por canal (28); descartado por el número de pines.

Preguntas para el cliente: ¿el reinicio debe ser automático al encender el carro?, ¿puede el usuario resetear sin apagar?, ¿qué canales deben reiniciarse juntos?
