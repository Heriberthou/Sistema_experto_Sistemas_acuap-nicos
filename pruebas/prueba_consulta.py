"""Comprueba el recorrido guiado: preguntas, conflictos, cierre tipo Akinator y reinicio."""
import unittest as pruebas
from sistema.conocimientos import cargar_conocimientos
from sistema.consulta import consultar


class PruebasConsulta(pruebas.TestCase):
    """Ejercita la política de preguntas, independiente de la interfaz."""

    @classmethod
    def setUpClass(clase):
        """Carga el catálogo vigente."""
        clase.base = cargar_conocimientos()

    def recorrer(caso_prueba, hechos, respuesta="D", cierre=None, limite=60):
        """Responde cada pregunta con un valor fijo hasta salir de la fase de preguntas."""
        hechos = dict(hechos)
        for _ in range(limite):
            resultado = consultar(caso_prueba.base, hechos, cierre)
            if resultado["fase"] != "pregunta":
                return hechos, resultado
            caso_prueba.assertNotIn(resultado["pregunta"]["id"], hechos)
            hechos[resultado["pregunta"]["id"]] = respuesta
        caso_prueba.fail("La consulta no terminó")

    def test_primera_pregunta_y_reinicio(caso_prueba):
        """Sin hechos empieza por la primera medición; cada consulta nace de sus hechos."""
        inicio = consultar(caso_prueba.base, {})
        caso_prueba.assertEqual((inicio["fase"], inicio["pregunta"]["id"]), ("pregunta", "Q01a"))
        consultar(caso_prueba.base, {"Q06": "V"})
        caso_prueba.assertFalse(consultar(caso_prueba.base, {})["resultados"])

    def test_todo_desconozco_termina_sin_repetir(caso_prueba):
        """Con todo Desconozco la consulta cierra como Insuficiente sin repetir preguntas."""
        _, resultado = caso_prueba.recorrer({})
        caso_prueba.assertEqual(resultado["fase"], "cerrada")
        caso_prueba.assertEqual(resultado["calidad"]["nivel"], "Insuficiente")

    def test_mortalidad_aparece_sin_esperar_al_final(caso_prueba):
        """A06 se muestra mientras siguen pendientes otras preguntas."""
        resultado = consultar(caso_prueba.base, {"Q06": "V"})
        caso_prueba.assertIn("A06", {r["id"] for r in resultado["resultados"]})
        caso_prueba.assertEqual(resultado["fase"], "pregunta")

    def test_conflicto_y_correccion(caso_prueba):
        """K1 detiene las preguntas y admite corrección o continuar sin esos datos."""
        resultado = consultar(caso_prueba.base, {"Q09": "F", "Q10": "V", "Q12": "V"})
        caso_prueba.assertEqual((resultado["fase"], resultado["conflictos"][0]["id"]), ("conflicto", "K1"))
        corregido = consultar(caso_prueba.base, {"Q09": "V", "Q10": "V", "Q12": "V"})
        caso_prueba.assertFalse(corregido["conflictos"])
        seguir = consultar(caso_prueba.base, {"Q09": "F", "Q10": "V", "Q12": "V"}, None, True)
        caso_prueba.assertNotEqual(seguir["fase"], "conflicto")

    def test_cierre_con_descarte_y_confirmacion(caso_prueba):
        """Un escenario con evidencia llega a confirmación; descartar pasa a otra hipótesis o cierra."""
        base = {"Q06": "F", "Q07": "V", "Q08": "V"}
        _, resultado = caso_prueba.recorrer(base)
        caso_prueba.assertIn(resultado["fase"], ("confirmacion", "cerrada"))
        if resultado["fase"] == "confirmacion":
            hechos, _ = caso_prueba.recorrer(base)
            descartadas = []
            for _ in range(5):
                actual = consultar(caso_prueba.base, hechos, {"descartadas": descartadas, "final": None})
                if actual["fase"] != "confirmacion":
                    break
                caso_prueba.assertNotIn(actual["principal"]["id"], descartadas)
                descartadas.append(actual["principal"]["id"])
            caso_prueba.assertEqual(actual["fase"], "cerrada")
            caso_prueba.assertLessEqual(len(descartadas), actual["cierre"]["maximo"])

    def test_entradas_invalidas(caso_prueba):
        """Solo se aceptan V, F o D para preguntas existentes."""
        for hechos in ({"Q01a": 15}, {"Q99": "V"}, {"Q06": "x"}):
            with caso_prueba.assertRaises(ValueError):
                consultar(caso_prueba.base, hechos)
