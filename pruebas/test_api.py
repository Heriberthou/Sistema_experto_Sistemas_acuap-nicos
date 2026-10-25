"""Integración HTTP en un puerto efímero local."""
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from sistema.servidor import ManejadorHTTP


class PruebasAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.servidor = ThreadingHTTPServer(('127.0.0.1',0),ManejadorHTTP)
        cls.hilo = threading.Thread(target=cls.servidor.serve_forever,daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown(); cls.servidor.server_close(); cls.hilo.join()

    def peticion(self, metodo, ruta, contenido_peticion=None):
        conexion = HTTPConnection('127.0.0.1',self.servidor.server_port,timeout=5)
        conexion.request(metodo,ruta,json.dumps(contenido_peticion) if contenido_peticion is not None else None,{'Content-Type':'application/json'})
        respuesta = conexion.getresponse()
        estado_http,datos = respuesta.status,respuesta.read()
        conexion.close()
        return estado_http,datos

    def test_interfaz_y_conocimientos(self):
        for ruta in ('/','/estilos.css','/aplicacion.js','/api/ejemplos'):
            self.assertEqual(self.peticion('GET',ruta)[0],200)
        estado_http,datos = self.peticion('GET','/api/conocimientos')
        self.assertEqual(estado_http,200)
        self.assertEqual(len(json.loads(datos)['reglas']),51)

    def test_inferencia_y_comparacion(self):
        contenido_peticion = {'hechos':{'Q02':'V','Q16':'V'},'objetivo':'C27','modo':'atras'}
        estado_http,datos = self.peticion('POST','/api/inferir',contenido_peticion)
        self.assertEqual(estado_http,200)
        self.assertEqual(json.loads(datos)['objetivo']['estado'],'V')
        estado_http,datos = self.peticion('POST','/api/comparar',contenido_peticion)
        self.assertEqual(estado_http,200)
        self.assertTrue(json.loads(datos)['misma_meta'])

    def test_entradas_invalidas_y_rutas_privadas(self):
        for contenido_peticion in ([1], {'hechos':{'Q01':'invalid'}}, {'hechos':{'C01':'V'}}, {'objetivo':[]}):
            self.assertEqual(self.peticion('POST','/api/inferir',contenido_peticion)[0],400)
        for ruta in ('/.git/config','/Contenido.docx','/../sistema/servidor.py'):
            self.assertEqual(self.peticion('GET',ruta)[0],404)

    def test_consulta_guiada_sin_modo_ni_meta(self):
        estado_http,datos=self.peticion('POST','/api/consultar',{'tema':'peces','hechos':{'Q16':'V'}})
        self.assertEqual(estado_http,200)
        resultado=json.loads(datos)
        self.assertEqual(resultado['pregunta_siguiente'],'Q02')
        self.assertIn('reglas_atras',resultado['analisis'])
        self.assertEqual(self.peticion('POST','/api/consultar',{'tema':'desconocido'})[0],400)
        self.assertEqual(self.peticion('GET','/api/temas')[0],200)
        for ruta in ('/academico.html','/academico.css','/academico.js'):
            self.assertEqual(self.peticion('GET',ruta)[0],200)
