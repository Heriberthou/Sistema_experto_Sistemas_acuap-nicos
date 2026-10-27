# Acuavida · Sistema experto acuapónico

Aplicación educativa para revisar un sistema de tilapia y lechuga, alineada con la **Documentación v3** del sistema experto. La interfaz (HTML, CSS y JavaScript) solo presenta la consulta; Python implementa encadenamiento hacia adelante y hacia atrás sobre una misma base: **37 preguntas, 38 conclusiones, 33 recomendaciones, 73 reglas, 3 fuentes y 13 restricciones (K1–K12)**.

## Ejecutar

Requiere Python 3.10 o posterior y un navegador. Sin dependencias externas ni base de datos.

```bash
python -m sistema.servidor          # --puerto 8001 para otro puerto
```

Abrir http://127.0.0.1:8000/ (no abrir el HTML directamente: necesita la API local).

## Cómo funciona la consulta

1. Todas las preguntas se responden **Sí, No o Desconozco** (atajos S, N, D). Las mediciones son escaleras de rangos (Q01a–c, Q02a–c…): cada paso descarta intervalos.
2. El servidor elige la siguiente pregunta por puntaje (reglas pendientes + restricciones), con desempate por seguridad y primeros pasos.
   Las preguntas que una respuesta ya vuelve imposibles se omiten (por ejemplo, sin electricidad no se pregunta por bomba ni aireador): se deducen de las restricciones K1–K5, se asumen No y se informan en pantalla. Si el usuario las contesta de forma contradictoria, K1–K5 siguen avisando.
3. Si hay respuestas contradictorias (K1–K5, K9) se muestran para corregirlas o continuar sin esos datos.
4. Cierre tipo Akinator: el sistema propone su conclusión principal y pide confirmación (máx. 3 rondas; «No» la descarta y busca otra).
5. Resultado: acciones por urgencia con verificación, causas con nivel de sustento (Medida, Observada, Hipótesis), calidad de la consulta (Confiable, Parcial, No fiable, Insuficiente), datos faltantes y traza de reglas con fuentes.

El **laboratorio** (`/laboratorio.html`) compara ambos encadenamientos y ejecuta los 40 casos (T1–T36 y variantes), mostrando esperado contra obtenido.

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

## Cortes de energía: duración y cadena de consecuencias

Cuando el usuario responde que **no hay suministro eléctrico**, el sistema no se detiene en «revisar la energía»: sigue preguntando **cuánto tiempo lleva el corte** (más de 2 h, más de 12 h, más de 48 h) y relaciona el resultado con el resto de los problemas.

| Duración | Conclusión | Qué se espera |
|---|---|---|
| Menos de 2 h | C30 | Oxígeno empezando a bajar; agua, lechugas y peces aún pueden verse normales. |
| Más de 2 h | C31, C34, C37 | Oxígeno en descenso, posible acumulación de amoníaco y nitrito, peces con riesgo de asfixia. |
| Más de 12 h | C32, C35, C36, C38 | Algas por agua estancada, obstrucción de prefiltro y tuberías, lechugas marchitas o raíces oscuras. |
| Más de 48 h | C33 | Daño probable: mortalidad, raíces oscuras, tuberías con residuos. |

Sin energía también se infiere **falla de recirculación (C11)**, que activa la cadena de marchitez (C27). Los avisos K10–K12 señalan respuestas poco coherentes (por ejemplo, algas o raíces oscuras con un corte de menos de 2 h). Los umbrales de 2, 12 y 48 h son una propuesta del sistema: la fuente (OSU HLA-6729, tabla 7) solo indica que el oxígeno disminuye y recomienda respaldo y aireación manual.

## Empezar desde una sospecha (encadenamiento hacia atrás)

Además de la consulta completa (hacia adelante), la pantalla de inicio permite elegir un área y una **sospecha**, por ejemplo «Peces muertos» o «Se fue la luz». El sistema toma esa sospecha como meta, la comprueba hacia atrás y solo pregunta lo necesario. Termina con un veredicto (**sí se cumple**, **no se cumple** o **faltan datos**), las acciones recomendadas y el botón «Revisar todo mi sistema» para continuar con la consulta completa. Las sospechas disponibles están en `conocimientos/guia_consulta.json` (`partidas`) y se sirven en `GET /api/guia`; `POST /api/consultar` acepta el campo opcional `objetivo`.
