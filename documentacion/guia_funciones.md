# Guía de funciones

- `logica.evaluar(nodo, hechos)`: evalúa el árbol de un antecedente con Kleene; `negar`, `simbolos`.
- `escaleras.habilitada(base, hechos, id)` / `completar(base, hechos)`: decide si una pregunta aplica y añade valores implícitos.
- `validacion.validar_hechos`, `revisar_consistencia` → (seguros, violaciones, avisos), `hipotesis_suspendidas`.
- `motor.adelante(base, hechos, bloqueadas)`: punto fijo de reglas. `EncadenamientoAtras`: demuestra una meta y registra preguntas consultadas. `ejecutar`, `comparar`, `filtrar_por_calidad`.
- `calidad.nivel_calidad`, `calcular_sustento`.
- `explicacion.reunir_resultados`, `explicar_resultado`, `lecturas`.
- `consulta.puntuar`, `elegir_pregunta`, `describir_pregunta`, `conclusion_principal`, `alternativa_pendiente`, `consultar`, `cerrar`.
- `casos.hechos_del_caso`, `evaluar_caso`, `evaluar_todos`.
- Interfaz: `aplicacion.js` (consulta), `laboratorio.js` (comparación y casos), `utilidades.js` (solicitudes, íconos, tema, traza, descarga). El JavaScript no calcula diagnósticos.
