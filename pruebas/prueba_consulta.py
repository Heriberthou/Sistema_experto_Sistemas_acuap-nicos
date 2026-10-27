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
        """Sin hechos empieza por la causa raíz (energía); cada consulta nace de sus hechos."""
        inicio = consultar(caso_prueba.base, {})
        caso_prueba.assertEqual((inicio["fase"], inicio["pregunta"]["id"]), ("pregunta", "Q09"))
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

    def preguntadas(caso_prueba, hechos, limite=40):
        """Identificadores que el sistema pregunta, contestando Desconozco, hasta que deja de preguntar."""
        hechos, vistas = dict(hechos), []
        for _ in range(limite):
            resultado = consultar(caso_prueba.base, hechos)
            if resultado["fase"] != "pregunta":
                break
            vistas.append(resultado["pregunta"]["id"])
            hechos[vistas[-1]] = "D"
        return vistas, resultado

    def test_sin_electricidad_no_pregunta_equipos_encendidos(caso_prueba):
        """Con Q09 = No, bomba y aireador no pueden estar encendidos: no se preguntan y se informan como deducidas."""
        vistas, resultado = caso_prueba.preguntadas({"Q09": "F"})
        caso_prueba.assertTrue({"Q10", "Q11", "Q13", "Q14"}.isdisjoint(vistas))
        caso_prueba.assertEqual({d["id"] for d in resultado["deducidas"]}, {"Q10", "Q11", "Q13", "Q14"})
        caso_prueba.assertEqual(resultado["hechos"], {"Q09": "F", **{q: "D" for q in vistas}})
        con_energia, _ = caso_prueba.preguntadas({"Q09": "V"})
        caso_prueba.assertTrue({"Q10", "Q13", "Q14"} <= set(con_energia))

    def test_sin_electricidad_sigue_preguntando_la_duracion(caso_prueba):
        """Sin energía se pregunta cuánto lleva el corte; la escalera sigue solo si la respuesta anterior fue Sí."""
        vistas, _ = caso_prueba.preguntadas({"Q09": "F"})
        caso_prueba.assertIn("Q28a", vistas)
        caso_prueba.assertNotIn("Q28b", vistas)
        caso_prueba.assertTrue({"Q16", "Q12", "Q23"} & set(vistas))
        caso_prueba.assertEqual(caso_prueba.preguntadas({"Q09": "F", "Q28a": "V"})[0].count("Q28b"), 1)
        caso_prueba.assertNotIn("Q28c", caso_prueba.preguntadas({"Q09": "F", "Q28a": "V", "Q28b": "F"})[0])
        caso_prueba.assertNotIn("Q28a", caso_prueba.preguntadas({"Q09": "V"})[0])

    def test_gravedad_depende_del_tiempo_sin_energia(caso_prueba):
        """Corte reciente: sin daños esperados; corte largo: cadena de consecuencias; corte crítico: daños probables."""
        def ids(hechos):
            """Conclusiones y acciones que devuelve la consulta."""
            return {r["id"] for r in consultar(caso_prueba.base, hechos)["resultados"]}
        reciente = ids({"Q09": "F", "Q28a": "F", "Q16": "F", "Q23": "F", "Q06": "F", "Q07": "F", "Q12": "F"})
        caso_prueba.assertTrue({"C30", "C08", "C09", "C11"} <= reciente)
        caso_prueba.assertTrue({"C31", "C32", "C33", "C35", "C36", "C37", "C38"}.isdisjoint(reciente))
        largo = ids({"Q09": "F", "Q28a": "V", "Q28b": "V", "Q28c": "F", "Q16": "V", "Q12": "V", "Q23": "V", "Q07": "V"})
        caso_prueba.assertTrue({"C32", "C34", "C35", "C36", "C37", "C38", "C27", "A31", "A32"} <= largo)
        caso_prueba.assertNotIn("C33", largo)
        critico = ids({"Q09": "F", "Q28a": "V", "Q28b": "V", "Q28c": "V"})
        caso_prueba.assertIn("C33", critico)

    def test_avisos_de_corte_reciente(caso_prueba):
        """Un corte de menos de 2 h no explica algas, oxígeno crítico ni marchitez: se avisa sin cambiar hechos."""
        avisos = {a["id"] for a in consultar(caso_prueba.base, {"Q09": "F", "Q28a": "F", "Q16": "V", "Q01a": "V", "Q01b": "V", "Q21": "V", "Q23": "V"})["avisos"]}
        caso_prueba.assertTrue({"K10", "K11", "K12"} <= avisos)

    def test_consulta_desde_una_sospecha_encadena_hacia_atras(caso_prueba):
        """Con una sospecha (meta) solo se pregunta lo necesario y se termina con un veredicto en la fase «meta»."""
        def correr(objetivo, respuestas):
            """Contesta según el diccionario (F por omisión) hasta que termina la comprobación."""
            hechos, vistas = {}, []
            for _ in range(30):
                resultado = consultar(caso_prueba.base, hechos, None, False, objetivo)
                if resultado["fase"] != "pregunta":
                    return vistas, resultado
                vistas.append(resultado["pregunta"]["id"]); hechos[vistas[-1]] = respuestas.get(vistas[-1], "F")
        vistas, resultado = correr("A06", {"Q18": "V", "Q06": "V"})
        caso_prueba.assertEqual((vistas, resultado["fase"], resultado["meta"]["estado"]), (["Q18", "Q06"], "meta", "V"))
        vistas, resultado = correr("A06", {"Q18": "F"})
        caso_prueba.assertEqual((vistas, resultado["meta"]["estado"]), (["Q18"], "F"))
        vistas, resultado = correr("C32", {"Q09": "F", "Q28a": "V", "Q28b": "V"})
        caso_prueba.assertEqual((vistas, resultado["meta"]["estado"]), (["Q09", "Q28a", "Q28b"], "V"))
        vistas, resultado = correr("C04", {"Q04a": "D"})
        caso_prueba.assertEqual((resultado["meta"]["estado"], len(resultado["meta"]["sin_saber"])), ("D", 1))
        with caso_prueba.assertRaises(ValueError):
            consultar(caso_prueba.base, {}, None, False, "Z99")

    def test_otras_deducciones_por_restricciones(caso_prueba):
        """Q18 = No omite Q06-Q08; Q13 = No omite Q14; Q10 = No omite Q11."""
        for hechos, omitidas in (({"Q18": "F"}, {"Q06", "Q07", "Q08"}), ({"Q13": "F"}, {"Q14"}), ({"Q10": "F"}, {"Q11"})):
            vistas, resultado = caso_prueba.preguntadas(hechos)
            caso_prueba.assertTrue(omitidas.isdisjoint(vistas), hechos)
            caso_prueba.assertEqual({d["id"] for d in resultado["deducidas"]}, omitidas)
        _, resultado = caso_prueba.preguntadas({})
        caso_prueba.assertEqual(resultado["deducidas"], [])

    def test_deduccion_conserva_resultados_coherentes(caso_prueba):
        """Sin electricidad se deduce C08 y que el aireador no funciona (C09); una respuesta contradictoria sigue avisando K4."""
        resultado = consultar(caso_prueba.base, {"Q09": "F"})
        ids = {r["id"] for r in resultado["resultados"]}
        caso_prueba.assertTrue({"C08", "C09", "A09"} <= ids)
        conflicto = consultar(caso_prueba.base, {"Q09": "F", "Q13": "V"})
        caso_prueba.assertEqual(conflicto["fase"], "conflicto")
        caso_prueba.assertEqual([c["id"] for c in conflicto["conflictos"]], ["K4"])
        caso_prueba.assertEqual(conflicto["deducidas"][0]["por"], "Q09")

    def test_orden_previas_antes_de_dependientes(caso_prueba):
        """Primero se pregunta si hay peces, luego lo que depende de ello; y nada se pregunta dos veces."""
        vistas, _ = caso_prueba.preguntadas({})
        caso_prueba.assertEqual(len(vistas), len(set(vistas)))
        for previa, dependientes in (("Q18", ("Q06", "Q07", "Q08", "Q19")), ("Q09", ("Q10", "Q13")), ("Q10", ("Q11",)), ("Q13", ("Q14",))):
            for dependiente in dependientes:
                caso_prueba.assertLess(vistas.index(previa), vistas.index(dependiente), f"{previa} antes de {dependiente}")
        sin_peces, _ = caso_prueba.preguntadas({"Q18": "F"})
        caso_prueba.assertTrue({"Q06", "Q07", "Q08", "Q19"}.isdisjoint(sin_peces))
