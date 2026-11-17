"""Public, deterministic synthetic demonstration. No clinical data or inference."""
import csv
import io
import math

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

NOTICE = 'Demonstração com dados sintéticos. Sem inferência de IA ou validação clínica.'
PATIENTS = [dict(id=f'demo-{i:03}', cpf=f'0000000000{i}', nome=f'Paciente demonstrativo {i}',
                 idade=35 + i * 10, genero='Não informado', prontuario='Cenário sintético para demonstração; nenhum dado pessoal real.')
            for i in (1, 2)]
CHANNELS = [('HR', 'HR', 'Frequência cardíaca', 75, 4), ('SpO2', 'SpO2', 'Saturação de oxigênio', 97, 1),
            ('NBPs', 'NBP Sys', 'Pressão sistólica', 120, 6), ('NBPd', 'NBP Dias', 'Pressão diastólica', 80, 4),
            ('PULSE', 'PULSE', 'Pulso periférico', 74, 4), ('RESP', 'RESP', 'Frequência respiratória', 16, 2)]
EXERCISES = ['Abdução do braço direito', 'Abdução dos braços', 'Flexão dos braços', 'Abdução da perna']
VIDEOS = [dict(id=f'{i:020x}', recording_id=f'EXEMPLO_{i:03}', exercise_id=i,
               person_id='DEMO', camera=17, fps=10, width=640, height=360, frame_count=120, demo=True)
          for i in range(1, 5)]


def patient(id: str | None, cpf: str | None):
    if not id and not cpf:
        raise HTTPException(422, 'Informe id ou cpf.')
    found = next((p for p in PATIENTS if (not id or p['id'] == id) and (not cpf or p['cpf'] == cpf)), None)
    if not found:
        raise HTTPException(404, 'Paciente demonstrativo não localizado.')
    return found


def video_for(identifier):
    found = next((v for v in VIDEOS if v['id'] == identifier), None)
    if not found:
        raise HTTPException(404, 'Exemplo demonstrativo não localizado.')
    return found


def create_demo_app():
    app = FastAPI(title='Prontuário Digital — Demonstração', description=NOTICE, version='0.3.0')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'mode': 'demo'}

    @app.get('/v1/sinais-vitais/paciente')
    def patients():
        return PATIENTS

    @app.post('/v1/sinais-vitais/')
    def import_disabled():
        raise HTTPException(403, 'Importação desativada nesta demonstração gratuita. ' + NOTICE)

    @app.get('/v1/sinais-vitais/datalhamento')
    def details(id: str | None = None, cpf: str | None = None):
        p = patient(id, cpf)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['tempo_segundos'] + [c[1] for c in CHANNELS])
        for t in range(120):
            writer.writerow([t] + [round(base + amplitude * math.sin(t / 12 + j + int(p['id'][-1])), 2)
                                   for j, (_, _, _, base, amplitude) in enumerate(CHANNELS)])
        return Response(output.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="sinais-sinteticos.csv"'})

    @app.get('/v1/sinais-vitais/relatorio')
    def vital_report(id: str | None = None, cpf: str | None = None):
        p = patient(id, cpf)
        return {'demo': True, 'aviso': NOTICE, 'dados_do_paciente': p,
                'tempo_analisado': {'duracao_formatada': '2 minutos (sintéticos)'},
                'sinais_vitais': {code: {'descricao': label, 'status': 'Não Conclusivo',
                                        'observacao': NOTICE + ' Curva ilustrativa produzida por função matemática.'}
                                  for code, _, label, _, _ in CHANNELS}}

    @app.get('/v1/sinais-vitais/tabela-referencia')
    def references(sinal: str | None = None):
        values = {c[0]: {'observacao': 'Faixas clínicas não disponibilizadas no modo demonstrativo.'} for c in CHANNELS}
        if sinal is None:
            return {'sinais_vitais': values}
        if sinal not in values:
            raise HTTPException(404, 'Sinal não localizado.')
        return {'sinal': sinal, 'tabela': values[sinal]}

    @app.get('/v1/fisioterapia/catalogo')
    def catalog():
        return {'demo': True, 'notice': NOTICE, 'exercises': [dict(id=i, name=name) for i, name in enumerate(EXERCISES, 1)], 'videos': VIDEOS}

    class DemoAnalysis(BaseModel):
        video_id: str

    def task(identifier):
        video_for(identifier)
        return {'id': identifier, 'video_id': identifier, 'status': 'concluido', 'progress': 1, 'demo': True}

    @app.post('/v1/fisioterapia/analises', status_code=202)
    def create(body: DemoAnalysis):
        return task(body.video_id)

    @app.get('/v1/fisioterapia/analises/{job_id}')
    def get_task(job_id: str):
        return task(job_id)

    @app.get('/v1/fisioterapia/analises/{job_id}/relatorio')
    def report(job_id: str):
        video = video_for(job_id)
        return {'demo': True, 'exercise': EXERCISES[video['exercise_id'] - 1], 'video': video,
                'summary': {'total': 3, 'correct': 1, 'incorrect': 1, 'nonconclusive': 1},
                'limitations': [NOTICE, 'Não há vídeo real nem processamento de postura neste ambiente.'],
                'repetitions': [dict(repetition_number=i + 1, start_seconds=i * 4, end_seconds=(i + 1) * 4,
                                     first_frame_index=i * 40, status=status + ' (simulado)', prediction=prediction,
                                     reference_label=None, coverage=1 if i < 2 else .4,
                                     reason=NOTICE, series=[{'ombro_direito': round(45 + 40 * math.sin(j / 12), 2)} for j in range(40)])
                                for i, (status, prediction) in enumerate([('Correto', 1), ('Incorreto', 0), ('Não conclusivo', None)])]}

    @app.get('/v1/fisioterapia/analises/{job_id}/pose')
    def pose(job_id: str):
        video_for(job_id)
        return {'demo': True, 'fps': 10, 'points': []}

    return app
