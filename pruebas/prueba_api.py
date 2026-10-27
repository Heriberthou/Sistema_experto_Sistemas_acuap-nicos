"""Integración HTTP con un puerto local efímero; no necesita un servidor externo."""
import json
import threading as hilos
import unittest as pruebas
from http.client import HTTPConnection as ConexionHTTP
from http.server import ThreadingHTTPServer as ServidorConcurrente
from sistema.servidor import ManejadorHTTP


class PruebasAPI(pruebas.TestCase):
    """Verifica la API, los recursos visuales y el aislamiento de archivos privados."""

    @classmethod
    def setUpClass(clase):
        """Arranca un servidor exclusivo de pruebas en un puerto disponible."""
        clase.servidor = ServidorConcurrente(('127.0.0.1', 0), ManejadorHTTP)
        clase.hilo = hilos.Thread(target=clase.servidor.serve_forever, daemon=True)
        clase.hilo.start()

    @classmethod
    def tearDownClass(clase):
        """Libera el puerto y espera a que termine el hilo de pruebas."""
        clase.servidor.shutdown(); clase.servidor.server_close(); clase.hilo.join()

    def solicitar(caso_prueba, metodo, ruta, contenido=None):
        """Realiza una petición real y devuelve estado y bytes de respuesta."""
        conexion = ConexionHTTP('127.0.0.1', caso_prueba.servidor.server_port, timeout=10)
        conexion.request(metodo, ruta, json.dumps(contenido) if contenido is not None else None, {'Content-Type': 'application/json'})
        respuesta = conexion.getresponse(); estado, cuerpo = respuesta.status, respuesta.read(); conexion.close()
        return estado, cuerpo

    def test_recursos_y_catalogos(caso_prueba):
        """Las páginas, scripts, imágenes y catálogos se sirven desde el mismo origen."""
        for ruta in ['/', '/estilos.css', '/aplicacion.js', '/utilidades.js', '/laboratorio.html', '/laboratorio.js', '/favicon.svg',
                     '/imagenes/pez.png', '/imagenes/lechuga.png', '/imagenes/expresiones_pez.png', '/imagenes/expresiones_lechuga.png', '/api/casos']:
            caso_prueba.assertEqual(caso_prueba.solicitar('GET', ruta)[0], 200, ruta)
        estado, cuerpo = caso_prueba.solicitar('GET', '/api/base')
        base = json.loads(cuerpo)
        caso_prueba.assertEqual(estado, 200)
        caso_prueba.assertEqual((len(base['preguntas']), len(base['conclusiones']), len(base['recomendaciones']), len(base['reglas'])), (37, 38, 33, 73))

    def test_casos_del_documento_pasan(caso_prueba):
        """El servidor ejecuta los 40 casos del documento y todos pasan."""
        estado, cuerpo = caso_prueba.solicitar('GET', '/api/casos/ejecutar')
        lista = json.loads(cuerpo)
        caso_prueba.assertEqual(estado, 200); caso_prueba.assertEqual(len(lista), 40)
        caso_prueba.assertEqual([c['id'] for c in lista if not c['ok']], [])

    def test_consulta_y_comparacion(caso_prueba):
        """La consulta devuelve la primera pregunta y el laboratorio compara una misma meta."""
        estado, cuerpo = caso_prueba.solicitar('POST', '/api/consultar', {'hechos': {}})
        datos = json.loads(cuerpo)
        caso_prueba.assertEqual(estado, 200); caso_prueba.assertEqual(datos['fase'], 'pregunta'); caso_prueba.assertEqual(datos['pregunta']['id'], 'Q09')
        estado, cuerpo = caso_prueba.solicitar('POST', '/api/comparar', {'hechos': {'Q06': 'V'}, 'objetivo': 'A01'})
        caso_prueba.assertEqual(estado, 200); caso_prueba.assertIn('coinciden', json.loads(cuerpo))

    def test_rechazo_y_ausencia_de_persistencia(caso_prueba):
        """Las entradas inválidas se rechazan y la consulta no recuerda peticiones anteriores."""
        for contenido in ({'hechos': {'Q01a': 15}}, {'hechos': {'Q99': 'V'}}, {'hechos': {'Q01a': 'x'}}):
            caso_prueba.assertEqual(caso_prueba.solicitar('POST', '/api/consultar', contenido)[0], 400)
        estado, cuerpo = caso_prueba.solicitar('POST', '/api/consultar', {'hechos': {}})
        caso_prueba.assertEqual(estado, 200); caso_prueba.assertEqual(json.loads(cuerpo)['hechos'], {})
        for contenido in ([1], {'hechos': {'Q06': True}}, {'objetivo': []}):
            caso_prueba.assertEqual(caso_prueba.solicitar('POST', '/api/inferir', contenido)[0], 400)
        for ruta in ['/.git/config', '/Contenido_simplificado.docx', '/../sistema/motor.py', '/api/temas']:
            caso_prueba.assertEqual(caso_prueba.solicitar('GET', ruta)[0], 404)
