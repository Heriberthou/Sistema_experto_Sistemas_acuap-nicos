"""Recorridos adaptativos completos, sin que el usuario elija motor o meta."""
import json
import unittest
from sistema.consulta import consultar
from sistema.conocimientos import RAIZ_PROYECTO, cargar_conocimientos


class PruebasConsulta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = cargar_conocimientos()
        cls.politica = json.loads((RAIZ_PROYECTO / 'conocimientos/consulta.json').read_text(encoding='utf-8'))

    def comprobar(self, hechos, topic='peces'):
        return consultar(self.kb, self.politica, hechos, topic)

    def recorrer(self, topic, answers):
        perfil = next(p for p in self.politica['temas'] if p['id']==topic)
        hechos, asked = dict(perfil['hechos']), []
        for _ in range(46):
            resultado = self.comprobar(hechos,topic)
            if resultado['terminada']:
                return resultado, asked
            self.assertFalse(resultado['conflictos'])
            q = resultado['pregunta_siguiente']
            self.assertNotIn(q, asked)
            self.assertNotIn(q, hechos)
            asked.append(q)
            hechos[q]=answers.get(q,'D')
        self.fail('El recorrido no terminó')

    def test_cadena_automatica_y_pregunta_descartada(self):
        resultado, asked = self.recorrer('peces',{'Q02':'V','Q29':'F','Q11':'F','Q12':'F'})
        self.assertEqual(asked,['Q02','Q29','Q11','Q12'])
        self.assertNotIn('Q30',asked)  # R18 ya se satisface con Q29=F.
        self.assertIn('C27',{c['id'] for c in resultado['hipotesis']})
        self.assertTrue(all(c['coincide'] for c in resultado['analisis']['comparaciones']))
        self.assertIn('R33',resultado['analisis']['reglas_adelante'])
        self.assertIn('R33',resultado['analisis']['reglas_atras'])

    def test_cambio_de_rama_segun_respuesta(self):
        self.assertEqual(self.comprobar({'Q16':'V','Q02':'V','Q29':'V'})['pregunta_siguiente'],'Q30')
        self.assertEqual(self.comprobar({'Q16':'V','Q02':'V','Q29':'F'})['pregunta_siguiente'],'Q11')

    def test_meta_vegetal_descartada_por_negacion(self):
        resultado, asked = self.recorrer('plantas',{'Q13':'F','Q38':'F','Q41':'V'})
        self.assertEqual(asked,['Q13','Q38','Q41'])
        self.assertFalse(resultado['hipotesis'])
        self.assertEqual(next(g for g in resultado['analisis']['metas'] if g['id']=='C30')['estado'],'F')
        self.assertNotIn('Q36',asked)

    def test_desconocidos_sin_repetir_ni_confirmar(self):
        for perfil in self.politica['temas']:
            resultado, asked = self.recorrer(perfil['id'],{})
            self.assertLess(len(asked),45)
            self.assertEqual(len(asked),len(set(asked)))
            self.assertTrue(resultado['sin_resolver'])
            self.assertFalse(resultado['hipotesis'])

    def test_acumulacion_de_resultados_independientes(self):
        resultado,_ = self.recorrer('peces',{'Q02':'V','Q29':'F','Q11':'V','Q12':'V'})
        self.assertEqual({c['id'] for c in resultado['hipotesis']},{'C27','C29'})
        self.assertTrue({'A01','A03','A04'}.issubset({a['id'] for a in resultado['recomendaciones']}))

    def test_conflicto_correccion_y_evidencia_independiente(self):
        resultado = self.comprobar({'Q01':'V','Q03':'F','Q31':'V'})
        self.assertFalse(resultado['terminada'])
        self.assertIsNone(resultado['pregunta_siguiente'])
        self.assertTrue(resultado['conflictos'])
        self.assertIn('A11',{a['id'] for a in resultado['recomendaciones']})
        fixed=self.comprobar({'Q01':'V','Q03':'V','Q31':'V'})
        self.assertFalse(fixed['conflictos'])
        self.assertIsNotNone(fixed['pregunta_siguiente'])

    def test_reinicio_sin_resultados_antiguos(self):
        self.comprobar({'Q16':'V','Q02':'V'})
        self.assertFalse(self.comprobar({},'explorar')['resultados'])

    def test_validacion_temas_y_hechos(self):
        with self.assertRaises(ValueError):
            self.comprobar({},'desconocido')
        with self.assertRaises(ValueError):
            self.comprobar({'Q02':False})

    def test_revision_general_sin_inventar_problemas(self):
        answers = {q['id']:'F' for q in self.kb['preguntas']}
        answers['Q25']='V'
        resultado,_=self.recorrer('explorar',answers)
        self.assertFalse(resultado['resultados'])
        self.assertEqual(resultado['titulo'],'No podemos concluir todavía')
