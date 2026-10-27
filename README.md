# Acuavida · Sistema experto acuapónico

Aplicación educativa para revisar un sistema de tilapia y lechuga, alineada con la **Documentación v3** del sistema experto. La interfaz (HTML, CSS y JavaScript) solo presenta la consulta; Python implementa encadenamiento hacia adelante y hacia atrás sobre una misma base: **34 preguntas, 29 conclusiones, 28 recomendaciones, 58 reglas, 3 fuentes y 10 restricciones (K1–K9)**.

## Ejecutar

Requiere Python 3.10 o posterior y un navegador. Sin dependencias externas ni base de datos.

```bash
python -m sistema.servidor          # --puerto 8001 para otro puerto
```

Abrir http://127.0.0.1:8000/ (no abrir el HTML directamente: necesita la API local).

## Cómo funciona la consulta

1. Todas las preguntas se responden **Sí, No o Desconozco** (atajos S, N, D). Las mediciones son escaleras de rangos (Q01a–c, Q02a–c…): cada paso descarta intervalos.
2. El servidor elige la siguiente pregunta por puntaje (reglas pendientes + restricciones), con desempate por seguridad y primeros pasos.
3. Si hay respuestas contradictorias (K1–K5, K9) se muestran para corregirlas o continuar sin esos datos.
4. Cierre tipo Akinator: el sistema propone su conclusión principal y pide confirmación (máx. 3 rondas; «No» la descarta y busca otra).
5. Resultado: acciones por urgencia con verificación, causas con nivel de sustento (Medida, Observada, Hipótesis), calidad de la consulta (Confiable, Parcial, No fiable, Insuficiente), datos faltantes y traza de reglas con fuentes.

El **laboratorio** (`/laboratorio.html`) compara ambos encadenamientos y ejecuta los 36 casos del documento (T1–T32 y variantes), mostrando esperado contra obtenido.

## Estructura

```text
conocimientos/  base_conocimientos.json (v4), casos_prueba.json
sistema/        logica, conocimientos, escaleras, validacion, calidad,
                explicacion, motor, consulta, casos, servidor
interfaz/       inicio.html, aplicacion.js, laboratorio.html/.js,
                utilidades.js, estilos.css (claro/oscuro), imagenes/
pruebas/        prueba_motor, prueba_consulta, prueba_api
documentacion/  arquitectura, guía de funciones, pruebas
```

Nombres y comentarios en español; se conservan los identificadores Q/C/A/R/F. El servidor usa solo la biblioteca estándar y una CSP estricta (`default-src 'self'`, sin estilos en línea).

## Verificación

```bash
python -m unittest discover -s pruebas -p 'prueba_*.py' -v
```

Es una guía educativa: no confirma enfermedades ni prescribe tratamientos, y no almacena consultas en el servidor.
