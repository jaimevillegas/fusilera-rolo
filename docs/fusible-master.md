# Fusible master `F1` (portafusibles del cliente)

Decisiones (11 nov 2026): el cliente entrega un **portafusibles hembra de 40 A**, sin marcas, de color azul. Se enchufa **desde arriba, perpendicular a la placa**, sobre **dos pestañas macho** verticales de **4,75 mm de ancho × 0,81 mm de espesor**, con las caras enfrentadas a **4,7 mm entre centros** (medidas tomadas por el usuario). Hay un fusible por placa (cada una tiene su entrada de +12 V). La rama de lógica (`F2`, 2 A) se toma **después** de `F1`.

## Esquemático

- Nueva red **`VIN_BORNE`** entre el borne `J1` y el pin 1 de `F1`; el pin 2 de `F1` es **`+12V`** (tiras y BTS, y `F2`).
- `F1`: símbolo `Device:Fuse`, valor "Portafusibles 40A", huella `fusilera:FuseHolder_2xFaston187_P4.70mm` (en `libs/fusilera.pretty`): dos pads de 4 mm con taladro de 1,4 mm a 4,7 mm; el contorno del cuerpo es **provisional** (medir el portafusibles).

## Pestañas candidatas (verticales, para soldar)

- **TE 1217133-1**: 4,75 × 0,81 mm, agujero de 1,32 mm, placa de 1,57 mm. Primera opción. *Comprobar en el plano de TE que es recta (vertical).*
- Molex 19708-4011 (recta, 4,75 × 0,81 mm) y RS PRO 4,75 × 0,8 mm.
- **No** sirve la TE 1217756-1: es de ángulo recto (pestaña paralela a la placa).
- Hoja de la familia TE 1217756-1: agujero 1,4 mm, placa 1,57–2,36 mm, 3,81 mm de pata bajo la placa, apta para soldadura por ola a 265 °C. **No indica corriente nominal.**

## Corriente: punto crítico (por resolver)

El portafusibles aguanta 40 A, pero **no encontré la corriente nominal de la pestaña soldada** (solo una cifra de 6–16 A de un anuncio de terceros, sin verificar). La ruta del fusible lleva picos de 25–30 A durante menos de 5 s y falta la corriente continua. Pasos: pedir a TE/Molex la corriente con su aumento de temperatura, usar almohadillas grandes con cobre ancho en las dos caras y sin alivio térmico, y medir la temperatura en prueba.

## Estado del PCB

- `F1` está **aparcado fuera del contorno** en master y slave.
- El pad de `J1` ya está en la red `/VIN_BORNE`: el DRC marca cortos con el tronco de +12 V hasta que se **parta el cobre**: `J1` debe llegar solo al pad 1 de `F1`, y el pad 2 de `F1` alimenta el tronco y las tiras. Diseño por hacer en KiCad (la master tiene ruteo manual).
- `replicar_celdas_pcb.py` avisa si se regenera una placa con `J1` en `VIN_BORNE` (su tronco tocaría el pad de `J1`).
- Alto del portafusibles ≈ 25 mm: comprobar holguras con la carcasa y con la otra placa del apilado.
