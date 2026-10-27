# Pruebas

```bash
python -m unittest discover -s pruebas -p 'prueba_*.py' -v
```

- `prueba_motor.py` (17 pruebas): los 36 casos T1–T32 y variantes, las 58 reglas, concordancia adelante/atrás (salvo T20), Kleene, `= D`, valores implícitos, K1–K9, calidad, sustento y entradas inválidas.
- `prueba_consulta.py`: primera pregunta, todo Desconozco, conflicto y corrección, cierre con descarte, entradas inválidas y preguntas omitidas por deducción (sin electricidad, sin peces, aireador o bomba apagados).
- `prueba_api.py`: rutas públicas, conteos de la base, `/api/casos/ejecutar` (36 de 36), rechazo de entradas y rutas privadas.

El laboratorio muestra la misma tabla (esperado frente a obtenido) y el texto «Obtenido» para pegar en la documentación.
