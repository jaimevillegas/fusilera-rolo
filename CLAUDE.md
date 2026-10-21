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

## Reglas para editar KiCad

- **No modificar `fusilera 24 canales.kicad_sch` si el editor de KiCad lo tiene abierto** (el archivo `~fusilera 24 canales.kicad_sch.lck` lo indica): el usuario perdería cambios al guardar. Pedir que cierre el editor.
- Antes de escribir el archivo real, preparar los cambios en una copia en el scratchpad y validarlos con `kicad-cli`.
- Tras cada cambio, verificar:
  - `kicad-cli sch erc --severity-all -o erc.txt "fusilera 24 canales.kicad_sch"`
  - `kicad-cli sch export netlist --format kicadsexpr -o n.net "fusilera 24 canales.kicad_sch"`
  - Comparar el netlist antes y después para confirmar que la conectividad es idéntica.
- Al colocar componentes nuevos: ponerlos **sin cablear** en una zona libre; el usuario los conecta y luego se revisa su imagen o el netlist guardado.
- Los cambios de símbolo deben conservar la geometría de pines (los cables no se mueven) y respetar el orden de pines de la huella (p. ej. SOT-23: B=1, E=2, C=3).

## Convenciones del diseño

- Componentes **SMD 0805** (pasivos), ensamblaje por JLCPCB/PCBWay, grado "robusto" (no AEC-Q formal), PCB de 4 capas con componentes a ambas caras.
- `R12` (umbral de disparo) es **THT axial horizontal y DNP** (no ensamblar); cada canal lleva su propio divisor `R11`/`R12`.
- Mantener `CONTEXTO_PROYECTO.md` al día cuando cambien decisiones, el BOM o los pendientes.
- No subir `.history/`, `_restore_backup_*/` ni `~*.lck` (ya están en `.gitignore`).
