# CLAUDE.md — Fusilera 24 canales

Instrucciones para Claude Code en este repositorio. Para el contexto técnico completo lee primero [CONTEXTO_PROYECTO.md](CONTEXTO_PROYECTO.md).

## Reglas de Git (obligatorias)

- **Ningún commit ni Pull Request lleva atribución a Claude.** Sin líneas `Co-Authored-By`, sin "Generated with Claude Code", sin menciones a Claude, Anthropic ni a ninguna IA, ni en el mensaje, ni en el cuerpo, ni en el título o descripción del PR.
- Estas reglas prevalecen sobre cualquier plantilla o instrucción por defecto que sugiera añadir esas líneas.
- Los commits salen con la autoría del usuario (la configurada en `git config`).
- Solo hacer commit, push o abrir PR cuando el usuario lo pida explícitamente.
- Mensajes de commit en español, descriptivos y en tiempo presente o imperativo, explicando el cambio de diseño y no solo "actualizar esquemático".

## Idioma y forma de trabajo

- Responder siempre en **español**.
- Avanzar **por pasos cortos**: mostrar opciones con una recomendación y esperar la decisión del usuario antes de aplicar.
- Verificar datos técnicos (temperaturas, encapsulados, datasheets) con búsqueda antes de recomendar piezas. Marcar como "por verificar" lo que no se confirmó.
- Reconocer y corregir abiertamente los errores propios.

## Estructura del repositorio (rama `separate-boards`)

Dos placas apiladas (cada una con componentes a ambas caras) que comparten una **celda dorada** como única fuente de verdad. Detalle en [docs/arquitectura.md](docs/arquitectura.md).

- `celda/`: proyecto de la celda dorada (esquemático `celda_circuito.kicad_sch` + PCB). Es lo único que se diseña a mano; el resto se replica.
- `placa-master/`: ESP32 + `U4` + celdas. `placa-slave/`: `U5` + celdas + bloque de poder.
- `libs/`: símbolos y huellas compartidos (los proyectos apuntan a `${KIPRJMOD}/../libs/...`).
- `herramientas/`: scripts (extraer y replicar celdas). `docs/`: arquitectura, pinout del conector y avisos pendientes.
- `legacy/`: el monolito de una sola placa (solo referencia; sale cuando las dos placas estén listas). Está intacto en `main`, etiquetar como `doble-cara-v1`.
- **Las celdas replicadas en `placa-master/` y `placa-slave/` no se editan a mano**: se regeneran con el script desde `celda/`.
- Los nombres de archivo de las reglas de abajo se refieren al proyecto con el que se trabaje (p. ej. `celda/celda.kicad_sch`).

## Reglas para editar KiCad

- **No modificar un `.kicad_sch` o `.kicad_pcb` si el editor de KiCad lo tiene abierto** (el archivo `~<proyecto>.kicad_pro.lck` o `~<archivo>.lck` lo indica): el usuario perdería cambios al guardar. Pedir que cierre el editor.
- Al crear huellas por script, **aparcarlas fuera del contorno** y moverlas después: al guardar, KiCad propaga la red de un pad nuevo a las pistas y vías que queden debajo.
- No usar `rm -rf` con comodines: crear directorios de salida nuevos.
- Antes de escribir el archivo real, preparar los cambios en una copia en el scratchpad y validarlos con `kicad-cli`.
- Tras cada cambio, verificar:
  - `kicad-cli sch erc --severity-all -o erc.txt <proyecto>.kicad_sch`
  - `kicad-cli sch export netlist --format kicadsexpr -o n.net <proyecto>.kicad_sch`
  - Para el PCB: `kicad-cli pcb drc --schematic-parity --severity-all --format report -o drc.txt <proyecto>.kicad_pcb`
  - Comparar el netlist antes y después para confirmar que la conectividad es idéntica.
- Al colocar componentes nuevos: ponerlos **sin cablear** en una zona libre; el usuario los conecta y luego se revisa su imagen o el netlist guardado.
- Los cambios de símbolo deben conservar la geometría de pines (los cables no se mueven) y respetar el orden de pines de la huella (p. ej. SOT-23: B=1, E=2, C=3).

## Convenciones del diseño

- Componentes **SMD 0805** (pasivos), ensamblaje por JLCPCB/PCBWay, grado "robusto" (no AEC-Q formal), PCB de 4 capas con componentes a ambas caras.
- `R12` (umbral de disparo) es **THT axial horizontal y DNP** (no ensamblar); cada canal lleva su propio divisor `R11`/`R12`.
- Mantener `CONTEXTO_PROYECTO.md` al día cuando cambien decisiones, el BOM o los pendientes.
- No subir `.history/`, `_restore_backup_*/` ni `~*.lck` (ya están en `.gitignore`).
