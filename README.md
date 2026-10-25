# Sistema experto acuapónico

Prototipo educativo para investigar condiciones simuladas en sistemas de **tilapia y lechuga**. La interfaz está desarrollada con HTML, CSS y JavaScript; el motor de reglas y los dos encadenamientos están implementados en Python. Los catálogos editables utilizan JSON.

## Requisitos y ejecución

Se requiere **Python 3.10 o posterior** y un navegador moderno. No es necesario instalar bibliotecas de Python, Node.js ni una base de datos.

Desde la carpeta principal del proyecto, ejecutar:

```powershell
python -m sistema.servidor
```

En Windows también se puede utilizar `py -3 -m sistema.servidor`. Después abrir **http://127.0.0.1:8000/** en el navegador. Para cambiar el puerto:

```powershell
python -m sistema.servidor --puerto 8001
```

Para detener el servidor, presionar `Ctrl+C`. El servidor solo escucha en el equipo local (`127.0.0.1`); no debe publicarse en Internet sin medidas adicionales. No abrir `interfaz/inicio.html` directamente: requiere la API de Python.

## Uso

El usuario selecciona un motivo de consulta, responde **Sí, No o Desconozco** y puede consultar la ayuda de cada pregunta. El sistema solicita otras preguntas cuando son pertinentes para las hipótesis exploradas. Al finalizar muestra condiciones, posibles problemas y recomendaciones, junto con las reglas que las justifican.

La consulta ordinaria combina ambos encadenamientos. El **laboratorio académico**, accesible desde el enlace de la pantalla inicial, permite ejecutar los encadenamientos por separado y compararlos.

## Carpetas y archivos

```text
sistema/
  servidor.py          Servidor HTTP y API local.
  conocimientos.py     Carga y validación de catálogos JSON.
  logica.py            Conectores Y, O y NO con estados V, F y D.
  inferencia.py        Encadenamientos hacia adelante y hacia atrás.
  consulta.py          Selección adaptativa de preguntas y resultados.
interfaz/
  inicio.html          Consulta guiada.
  estilos.css          Estilos de la consulta guiada.
  aplicacion.js        Interacción y presentación de resultados.
  academico.html       Laboratorio de inferencia.
  academico.css        Estilos del laboratorio.
  academico.js         Consultas y comparación académica.
conocimientos/
  preguntas.json       45 preguntas y ayudas estructuradas.
  reglas.json          51 reglas trazables a fuentes.
  conclusiones.json    36 condiciones e hipótesis.
  recomendaciones.json 15 verificaciones.
  fuentes.json         Identificadores de las tres fuentes.
  consistencia.json    Restricciones entre hechos relacionados.
  ejemplos.json        Casos simulados con resultados esperados.
  consulta.json        Temas iniciales y metas por investigar.
pruebas/
  test_inferencia.py   Lógica y motores de inferencia.
  test_consulta.py     Recorridos guiados, reinicio y conflictos.
  test_api.py          API y control de rutas públicas.
documentacion/
  arquitectura.md      Decisiones de arquitectura y mecanismos.
  pruebas.md           Escenarios de verificación.
```

Los identificadores académicos `Q01–Q45`, `R01–R51`, `C01–C36`, `A01–A15` y `F01–F03` se conservaron para mantener la trazabilidad con el documento del proyecto.

### Ayudas y preguntas

Cada entrada de `conocimientos/preguntas.json` tiene un campo `ayuda` con `descripcion`, `unidad`, `ejemplo_si`, `ejemplo_no` y `advertencia`. Estos valores son orientativos y no activan reglas. Las reglas referencian identificadores, no el texto de las preguntas.

### Interfaz y API

La API se encuentra en `sistema/servidor.py`. Utiliza estas rutas:

- `GET /api/conocimientos`, `/api/temas` y `/api/ejemplos`.
- `POST /api/consultar`: recibe `{"tema":"peces","hechos":{"Q16":"V"}}`.
- `POST /api/inferir`: recibe `{"modo":"adelante","objetivo":"C27","hechos":{"Q02":"V"}}`.
- `POST /api/comparar`: recibe `{"objetivo":"C27","hechos":{"Q02":"V"}}`.

Las propiedades JSON y los métodos propios utilizan nombres en español. Los nombres obligatorios de Python, JavaScript, DOM, HTTP y JSON permanecen en inglés por compatibilidad.

## Pruebas

Desde la carpeta principal:

```powershell
python -m unittest discover -s pruebas -v
```

La suite comprueba inferencia, contradicciones, desconocidos, consultas adaptativas, casos múltiples y rutas HTTP. Los archivos JavaScript también pueden comprobarse con `node --check`, aunque **Node.js no es necesario para ejecutar el proyecto**.

## Alcance

Este proyecto es educativo. Las reglas tienen límites documentales y algunas fuentes contienen tablas adaptadas de otros trabajos. El programa no identifica causas definitivas, no prescribe tratamientos y no controla equipos reales. La ejecución correcta de las pruebas no equivale a una validación científica o profesional del diagnóstico.
