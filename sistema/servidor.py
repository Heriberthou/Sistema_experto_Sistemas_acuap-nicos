"""Servidor de desarrollo local: publica solo la interfaz y las rutas declaradas."""
import argparse as argumentos
import json
from http.server import BaseHTTPRequestHandler as ManejadorBase
from http.server import ThreadingHTTPServer as ServidorConcurrente
from urllib.parse import urlsplit as dividir_ruta

from .conocimientos import RAIZ_PROYECTO, cargar_conocimientos
from .motor import ejecutar, comparar
from .consulta import consultar
from .casos import evaluar_todos

BASE = cargar_conocimientos()
CASOS = json.loads((RAIZ_PROYECTO / "conocimientos/casos_prueba.json").read_text(encoding="utf-8"))
PUBLICOS = {"/": ("inicio.html", "text/html"), "/inicio.html": ("inicio.html", "text/html"),
            "/estilos.css": ("estilos.css", "text/css"), "/aplicacion.js": ("aplicacion.js", "text/javascript"),
            "/laboratorio.html": ("laboratorio.html", "text/html"),
            "/laboratorio.js": ("laboratorio.js", "text/javascript"),
            "/utilidades.js": ("utilidades.js", "text/javascript"),
            "/favicon.svg": ("imagenes/icono.svg", "image/svg+xml")}
for nombre in ("pez.png", "lechuga.png", "expresiones_pez.png", "expresiones_lechuga.png"):
    PUBLICOS[f"/imagenes/{nombre}"] = (f"imagenes/{nombre}", "image/png")


class ManejadorHTTP(ManejadorBase):
    """Traduce HTTP a funciones del sistema; no conserva sesiones ni respuestas."""

    def responder(servidor, estado, contenido, tipo="application/json"):
        """Envía JSON o bytes junto con cabeceras que evitan cargar código externo."""
        cuerpo = contenido if isinstance(contenido, bytes) else json.dumps(contenido, ensure_ascii=False, allow_nan=False).encode("utf-8")
        servidor.send_response(estado)
        servidor.send_header("Content-Type", tipo if tipo.startswith("image/") and "svg" not in tipo else f"{tipo}; charset=utf-8")
        servidor.send_header("Content-Length", str(len(cuerpo)))
        servidor.send_header("Cache-Control", "no-store")
        servidor.send_header("X-Content-Type-Options", "nosniff")
        servidor.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        servidor.end_headers()
        servidor.wfile.write(cuerpo)

    def do_GET(servidor):
        """Contrato HTTP obligatorio: sirve archivos permitidos y catálogos públicos."""
        ruta = dividir_ruta(servidor.path).path
        if ruta in PUBLICOS:
            nombre, tipo = PUBLICOS[ruta]
            servidor.responder(200, (RAIZ_PROYECTO / "interfaz" / nombre).read_bytes(), tipo)
        elif ruta == "/api/base":
            servidor.responder(200, BASE)
        elif ruta == "/api/casos":
            servidor.responder(200, CASOS)
        elif ruta == "/api/casos/ejecutar":
            servidor.responder(200, evaluar_todos(BASE, CASOS))
        else:
            servidor.responder(404, {"error": "Ruta no encontrada"})

    def do_POST(servidor):
        """Contrato HTTP obligatorio: valida JSON y ejecuta la operación solicitada."""
        ruta = dividir_ruta(servidor.path).path
        if ruta not in ("/api/consultar", "/api/inferir", "/api/comparar"):
            servidor.responder(404, {"error": "Ruta no encontrada"})
            return
        try:
            longitud = int(servidor.headers.get("Content-Length", "0"))
            if not 0 < longitud <= 32768:
                raise ValueError("La petición debe contener entre 1 y 32768 bytes")
            if servidor.headers.get_content_type() != "application/json":
                raise ValueError("Se requiere contenido JSON")
            datos = json.loads(servidor.rfile.read(longitud))
            if not isinstance(datos, dict):
                raise ValueError("La petición debe ser un objeto JSON")
            hechos = datos.get("hechos", {})
            if ruta == "/api/consultar":
                resultado = consultar(BASE, hechos, datos.get("cierre"), datos.get("continuar") is True)
            elif ruta == "/api/comparar":
                resultado = comparar(BASE, hechos, datos.get("objetivo", "A01"))
            else:
                resultado = ejecutar(BASE, hechos, datos.get("modo", "adelante"), datos.get("objetivo", "A01"))
            servidor.responder(200, resultado)
        except (ValueError, TypeError, OverflowError, KeyError, AttributeError) as error:
            servidor.responder(400, {"error": str(error)})

    def log_message(servidor, formato, *argumentos_adicionales):
        """Contrato heredado: se omite el registro para no almacenar consultas."""
        pass


def iniciar():
    """Lee el puerto y mantiene el servidor en el equipo local hasta Ctrl+C."""
    analizador = argumentos.ArgumentParser(description="Sistema experto acuapónico educativo")
    analizador.add_argument("--puerto", type=int, default=8000)
    opciones = analizador.parse_args()
    servidor = ServidorConcurrente(("127.0.0.1", opciones.puerto), ManejadorHTTP)
    print(f"Abre http://127.0.0.1:{opciones.puerto}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    iniciar()
