# Conector de enlace master ↔ slave (`J10`) — borrador

Mismo conector y mismas etiquetas en ambas placas (símbolo `Conn_01x14`; huella provisional `JST_XH_B14B-XH-A_1x14_P2.50mm_Vertical`). **Por decidir**: tipo de conector (JST XH / Micro-Fit con pestillo, o regleta tipo shield) y si pasa por cable; el pinout no depende de eso.

| Pin | Red | Sentido | Nota |
|---|---|---|---|
| 1 | `LINK_5V` | slave → master | 5 V del buck de la slave; alimenta el LDO de la master |
| 2 | `LINK_5V` | slave → master | pin doble por corriente |
| 3 | `GND` | — | |
| 4 | `GND` | — | |
| 5 | `SDA` | bidireccional | I²C (ESP32 en la master, `U5` en la slave) |
| 6 | `SCL` | master → slave | |
| 7 | `ESP32_OUT15` | master → slave | desde `U4` `GPA7` |
| 8 | `ESP32_OUT16` | master → slave | desde `U4` `GPB7` |
| 9 | `ESP32_OUT17` | master → slave | desde `U4` `GPB1` |
| 10 | `ESP32_OUT18` | master → slave | desde `U4` `GPB2` |
| 11 | `ESP32_OUT19` | master → slave | desde `U4` `GPB3` |
| 12 | `FALLA27` | slave → master | hacia `U4` `GPB4` |
| 13 | `FALLA28` | slave → master | hacia `U4` `GPB5` |
| 14 | reserva | — | sin conexión |

Pendiente: un script que compare las redes de `J10` en ambos esquemáticos (hoy coinciden: se verificó a mano con el netlist) y el aviso de retroalimentación de `docs/avisos-electricos.md` (líneas 7–11).
