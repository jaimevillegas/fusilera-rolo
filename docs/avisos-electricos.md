# Avisos eléctricos pendientes de revisar

## 1. Retroalimentación entre placas por las líneas de salida (anotado 30 oct, por revisar)

Las salidas controladas de la slave que no salen de `U5` (5 según la corrección del 30 oct, ver `docs/arquitectura.md`) salen de `U4` (master) y cruzan por el conector hasta el OR de diodos (`ESP32_OUT` → resistencia → diodo → nodo `IN`) de cada celda de la slave. Las 2 fallas de la slave que lee `U4` cruzan en sentido contrario (push-pull de 0/3,3 V desde la slave).

- Si una placa queda **sin alimentación** (3,3 V local o +12 V ausente) mientras la otra empuja la línea a nivel alto, la corriente puede entrar por el diodo del OR hacia el nodo `IN` de la celda sin alimentar y polarizar parcialmente el BTS o su entrada.
- Al revés (master apagada, slave encendida), las salidas de `U4` quedan en alta impedancia o en cero: sin pull-down del lado de la slave, el nivel de esas líneas sería indefinido.
- Caso práctico a vigilar: el devkit del ESP32 puede alimentarse por USB en el banco aunque la slave (que genera el 5 V) esté apagada.

Ideas a evaluar (no decididas): pull-down de cada línea en el lado de la slave, resistencia en serie en la línea que cruza, secuencia de alimentación (la master no habilita salidas hasta ver la slave por I²C), diodo/transistor de bloqueo, `RESET` de los MCP coherente con el arranque.

## 2. Otros puntos ya anotados

- Falla de latch en `D14` (GPIO14 puede dar un pulso al arrancar; *no verificado*).
- 1 kΩ en serie en cada línea `FALLA` hacia el micro (los nodos `FALLA` cuelgan del nodo de realimentación del latch).
- Ancho y separación de 0,2 mm en las pistas heredadas frente al mínimo de JLC para 2 oz (8 mil = 0,2032 mm).
- Presupuesto de corriente de 3,3 V de las 28 celdas (para decidir cuánto margen da cada AP2112K).
