"""Servidor local sin dependencias externas; publica exclusivamente la carpeta interfaz/ y la API."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .inferencia import comparar, ejecutar
from .consulta import consultar
from .conocimientos import RAIZ_PROYECTO, cargar_conocimientos

BASE_CONOCIMIENTOS = cargar_conocimientos()
EJEMPLOS = json.loads((RAIZ_PROYECTO / "conocimientos" / "ejemplos.json").read_text(encoding="utf-8"))
POLITICA = json.loads((RAIZ_PROYECTO / "conocimientos" / "consulta.json").read_text(encoding="utf-8"))
ARCHIVOS_PUBLICOS = {"/": ("inicio.html", "text/html"), "/inicio.html": ("inicio.html", "text/html"),
          "/estilos.css": ("estilos.css", "text/css"), "/aplicacion.js": ("aplicacion.js", "text/javascript"),
          "/academico.html": ("academico.html", "text/html"),
          "/academico.css": ("academico.css", "text/css"), "/academico.js": ("academico.js", "text/javascript")}


class ManejadorHTTP(BaseHTTPRequestHandler):
    def responder(self, estado_http, contenido_peticion, tipo_contenido="application/json"):
        """Envía una respuesta HTTP con tipo y longitud del contenido."""
        contenido = contenido_peticion if isinstance(contenido_peticion, bytes) else json.dumps(contenido_peticion, ensure_ascii=False).encode("utf-8")
        self.send_response(estado_http)
        self.send_header("Content-Type", f"{tipo_contenido}; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(contenido)

    def do_GET(self):
        """Entrega únicamente archivos públicos y catálogos autorizados."""
        ruta = urlsplit(self.path).path
        if ruta in ARCHIVOS_PUBLICOS:
            nombre_archivo, mime = ARCHIVOS_PUBLICOS[ruta]
            self.responder(200, (RAIZ_PROYECTO / "interfaz" / nombre_archivo).read_bytes(), mime)
        elif ruta == "/api/conocimientos":
            self.responder(200, BASE_CONOCIMIENTOS)
        elif ruta == "/api/ejemplos":
            self.responder(200, EJEMPLOS)
        elif ruta == "/api/temas":
            self.responder(200, POLITICA['temas'])
        else:
            self.responder(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        """Valida una consulta JSON y delega el razonamiento en el motor."""
        ruta = urlsplit(self.path).path
        if ruta not in ("/api/inferir", "/api/comparar", "/api/consultar"):
            self.responder(404, {"error": "Ruta no encontrada"})
            return
        try:
            longitud = int(self.headers.get("Content-Length", "0"))
            if not 0 < longitud <= 32768:
                raise ValueError("Tamaño de petición inválido (máximo 32 KiB)")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Se requiere Content-Type: application/json")
            contenido_peticion = json.loads(self.rfile.read(longitud))
            if not isinstance(contenido_peticion, dict):
                raise ValueError("La petición debe ser un objeto JSON")
            hechos, objetivo = contenido_peticion.get("hechos", {}), contenido_peticion.get("objetivo", "C27")
            if ruta == "/api/consultar":
                resultado = consultar(BASE_CONOCIMIENTOS, POLITICA, hechos, contenido_peticion.get('tema', 'explorar'))
            elif ruta == "/api/comparar":
                resultado = comparar(BASE_CONOCIMIENTOS, hechos, objetivo)
            else:
                resultado = ejecutar(BASE_CONOCIMIENTOS, hechos, contenido_peticion.get("modo", "adelante"), objetivo)
            self.responder(200, resultado)
        except (ValueError, UnicodeDecodeError, TypeError) as error:
            self.responder(400, {"error": str(error)})

    def log_message(self, format, *argumentos):
        """Evita registrar las respuestas aportadas por el usuario."""
        # No registrar respuestas ni datos de las consultas.
        pass


def principal():
    """Inicia el servidor local y lo cierra de forma controlada."""
    analizador = argparse.ArgumentParser(description="Prototipo local de sistema experto acuapónico")
    analizador.add_argument("--puerto", type=int, default=8000)
    argumentos = analizador.parse_args()
    servidor = ThreadingHTTPServer(("127.0.0.1", argumentos.puerto), ManejadorHTTP)
    print(f"Sistema experto disponible en http://127.0.0.1:{argumentos.puerto}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    principal()
