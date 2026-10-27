# Arquitectura

## Capas
- **Conocimiento** (`conocimientos/base_conocimientos.json`, versión 4): preguntas con `ayuda`, `grupo`, `padre`/`valor_padre` (escaleras) y `despues_de`; parámetros con intervalos y nivel; conclusiones (C) y recomendaciones (A) con título, verificación y prioridad; reglas R1–R58 con árbol `si`, explicación, cita y fuentes; restricciones K1–K9.
- **Lógica** (`logica.py`): Kleene V/F/D y comparación explícita `es: D` (solo R16).
- **Escaleras** (`escaleras.py`): valores implícitos. F si el padre excluye el intervalo; D si el padre es D o la pregunta habilitada no se respondió.
- **Validación** (`validacion.py`): solo V/F/D; K1–K5 y K9 vuelven D los hechos en conflicto; K6, K7a/b y K8 avisan sin cambiar hechos (K7a suspende C12, C16, C17, C20).
- **Motor** (`motor.py`): encadenamiento adelante (punto fijo) y atrás (caché, anti-ciclos, cortocircuito, pregunta primero al padre).
- **Calidad** (`calidad.py`): Confiable, Parcial, No fiable, Insuficiente; sustento Medida, Observada, Hipótesis, Pendiente.
- **Consulta** (`consulta.py`): selección de pregunta, conclusión principal, confirmación y alternativas.
- **Servidor** (`servidor.py`): API sin estado.

## API
| Ruta | Uso |
|---|---|
| GET `/api/base`, `/api/casos` | catálogos |
| GET `/api/casos/ejecutar` | ejecuta los 40 casos |
| POST `/api/consultar` | `{hechos, cierre:{descartadas,final}, continuar}` → fase `pregunta`, `conflicto`, `confirmacion` o `cerrada` |
| POST `/api/inferir`, `/api/comparar` | un mecanismo o ambos para una meta |

Cada petición lleva todos los hechos; el servidor no guarda nada.
