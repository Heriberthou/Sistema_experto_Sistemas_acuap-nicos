"""Orquestación automática: deriva hechos y busca premisas relevantes por metas.

Los temas son alcance de consulta, no hipótesis elegidas por el usuario.
La política de navegación no altera las reglas de conocimiento.
"""
from .inferencia import EncadenamientoAtras, consistencia, adelante, validar_hechos, ESTADOS


def consultar(base_conocimientos, politica, hechos, tema):
    """Coordina una consulta adaptativa y reúne problemas y verificaciones sustentados."""
    validar_hechos(base_conocimientos, hechos)
    perfil = next((p for p in politica['temas'] if p['id'] == tema), None)
    if perfil is None:
        raise ValueError('Tema de consulta desconocido')
    hechos_seguros, conflictos, bloqueados = consistencia(base_conocimientos, hechos)
    memoria, pasos = adelante(base_conocimientos, hechos_seguros)
    metas = list(perfil['metas'])
    for rama in politica['seguimientos']:
        if memoria.get(rama['cuando']) == 'V':
            metas.extend(g for g in rama['metas'] if g not in metas)

    # Primero se derivan resultados; después se investigan las metas abiertas.
    busqueda = EncadenamientoAtras(base_conocimientos, hechos_seguros)
    estados_metas, candidatas, comparaciones = [], [], []
    for objetivo in metas:
        valor = busqueda.demostrar(objetivo)
        faltantes = sorted(busqueda.premisas_pendientes(objetivo))
        estados_metas.append({'id': objetivo, 'estado': valor, 'etiqueta': ESTADOS[valor], 'faltantes': faltantes})
        for pregunta in faltantes:
            if pregunta not in hechos and pregunta not in bloqueados and pregunta not in candidatas:
                candidatas.append(pregunta)
        comparaciones.append({'objetivo': objetivo, 'sustentada_adelante': memoria.get(objetivo) == 'V',
                            'estado_atras': valor, 'coincide': (memoria.get(objetivo) == 'V') == (valor == 'V')})

    # Si una respuesta vuelve imposible o suficiente una meta, premisas_pendientes ya no
    # devuelve sus preguntas. Nunca se usa D como F ni un límite artificial.
    siguiente_id = candidatas[0] if candidatas and not conflictos else None
    salidas = base_conocimientos['conclusiones'] + base_conocimientos['recomendaciones']
    resultados = [{**elemento, 'justificaciones': [s['regla'] for s in pasos if s['conclusion'] == elemento['id']]}
               for elemento in salidas if memoria.get(elemento['id']) == 'V']
    hipotesis = [elemento for elemento in resultados if elemento['tipo'] == 'Hipótesis']
    recomendaciones = [elemento for elemento in resultados if elemento['tipo'] == 'Verificación']
    condiciones = [elemento for elemento in resultados if elemento['tipo'] == 'Condición']
    terminada = not candidatas and not conflictos
    sin_resolver = [s['id'] for s in estados_metas if s['estado'] == 'D']
    if conflictos:
        titulo = 'Revisemos dos respuestas'
        resumen = 'Hay respuestas que no coinciden. Corrígelas para continuar con la misma muestra o período.'
    elif not terminada:
        titulo = 'Vamos a entender qué ocurre'
        resumen = 'La siguiente pregunta depende de lo que has respondido.'
    elif hipotesis:
        titulo = 'Esto es lo que encontramos'
        resumen = 'Estas posibilidades coinciden con tus respuestas. Las siguientes verificaciones ayudan a aclararlas.'
    elif resultados:
        titulo = 'Esto es lo que conviene revisar'
        resumen = 'Tus observaciones permiten recomendar estas verificaciones, aunque no confirman una causa.'
    else:
        titulo = 'No podemos concluir todavía'
        resumen = 'No hay información suficiente o una regla aplicable a este caso. Esto no significa que todo esté bien.'
    return {'tema': tema, 'hechos': hechos, 'terminada': terminada, 'pregunta_siguiente': siguiente_id,
            'titulo': titulo, 'resumen': resumen, 'conflictos': conflictos,
            'hipotesis': hipotesis, 'recomendaciones': recomendaciones, 'condiciones': condiciones,
            'resultados': resultados, 'traza': pasos, 'sin_resolver': sin_resolver,
            'nota_alcance': 'La revisión se limita al motivo elegido y a los indicios encontrados; no descarta otros problemas.',
            'analisis': {'metas': estados_metas, 'reglas_adelante': [s['regla'] for s in pasos],
                         'reglas_atras': [s['regla'] for s in busqueda.pasos],
                         'reglas_examinadas_atras': busqueda.reglas_visitadas,
                         'traza_atras': busqueda.pasos, 'preguntas_sugeridas': candidatas,
                         'comparaciones': comparaciones}}
