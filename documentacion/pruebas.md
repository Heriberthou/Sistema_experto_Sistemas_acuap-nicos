# Pruebas reproducibles

Ejecutar `python -m unittest discover -s pruebas -v` desde la raíz. Se usa `unittest`, incluido en Python. Los ejemplos públicos en `conocimientos/ejemplos.json` también se verifican automáticamente.

| Caso | Hechos | Esperado hacia adelante |
|---|---|---|
| Oxígeno y boqueo | Q02=V, Q16=V | C02, C11, C27, A01, A06 |
| Nitrato y lechugas | Q13=V, Q34=V | C10, C21, C30, A08 |
| Simultáneos | Q23=F, Q31=V, Q38=V | C19, C23, C31, A09, A11, A15 |
| Desconocidos | Q02=D, Q16=V | C11, A06; C27 indeterminada |
| Meta no sustentable | Q02=F, Q16=V | C11, A06; C27 no sustentable |
| Contradicción | Q01=V, Q03=F, Q31=V | Bloqueo Q01/Q03; C19 y A11 permanecen |
| Sin regla aplicable | Q01=F, resto ausente | Ningún resultado; no demuestra ausencia de problemas |

La suite cubre tablas de verdad, cadenas de reglas, hechos faltantes, entradas inválidas, corrección de conflictos, reinicio, justificaciones múltiples y ciclos. Compara las 51 metas en 15 conjuntos reproducibles de hechos (765 comparaciones). Las pruebas HTTP cubren interfaz, API y rechazo de rutas privadas.

Para demostrar el sistema: cargar los seis ejemplos, abrir explicaciones, cambiar de mecanismo, comparar, corregir una contradicción y reiniciar. La exportación contiene respuestas, resultados y traza de la consulta vigente.

Estas pruebas verifican correspondencia con la base recibida. No certifican validez científica de los criterios ni sustituyen el cotejo de las fuentes.

## Resultado de verificación del 25 de octubre de 2026

- 25 pruebas automatizadas aprobadas, incluidas las 765 comparaciones de metas.
- JavaScript comprobado con `node --check interfaz/aplicacion.js`, sin errores de sintaxis.
- Las pruebas automáticas verifican ambos motores y recorridos de consulta. La interfaz traducida requiere comprobación visual adicional en el navegador del usuario.
- Diseño adaptable conservado del proyecto original; no se ha efectuado una inspección visual completa en esta versión traducida.
- Los archivos JavaScript traducidos superaron la revisión de sintaxis; la interacción se revisó con un entorno simulado.

El entorno de ejecución restringido requirió permisos para abrir conexiones locales y crear archivos temporales durante las pruebas. Con esos permisos, la suite completa terminó correctamente.


## Revisión de la consulta automática

La suite actual contiene 25 pruebas aprobadas. `test_consulta.py` verifica recorridos completos sin selector de motor o meta, descarte de preguntas, desconocidos, condiciones simultáneas, reinicio y revisión de contradicciones.

- Peces boqueando, Q02=V y Q29=F: se descarta Q30 porque la regla R18 ya se cumple. Continúa con Q11 y Q12 y termina tras cuatro preguntas adicionales en este escenario.
- Si Q29=V, Q30 sí se pregunta: la secuencia cambia con la respuesta.
- Hojas amarillas y Q13=F: C30 deja de ser sustentable; no se recorren más signos vegetales para demostrar esa hipótesis. Se investigan pulgones y llegada de agua.
- Todos los datos desconocidos: el recorrido termina sin repetir preguntas ni inventar hipótesis.
- Las metas se comparan automáticamente con los mismos hechos mediante ambos mecanismos.

La interfaz anterior se conserva como laboratorio académico separado. Los recuentos y controles de algoritmos pertenecen a ese laboratorio, no a la consulta guiada.
