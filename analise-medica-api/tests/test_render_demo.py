import csv
import io
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from main import create_app


def demo(monkeypatch):
    monkeypatch.setenv('DEMO_MODE', '1')
    monkeypatch.setenv('FRONTEND_ORIGINS', 'https://demo.example.com')
    return TestClient(create_app())


def test_demo_health_and_synthetic_vital_signs(monkeypatch):
    with demo(monkeypatch) as client:
        assert client.get('/health').json() == {'status': 'ok', 'mode': 'demo'}
        patient = client.get('/v1/sinais-vitais/paciente').json()[0]
        assert patient['id'] == 'demo-001'
        assert 'sintético' in patient['prontuario']
        report = client.get('/v1/sinais-vitais/relatorio', params={'id': patient['id']}).json()
        assert report['demo'] is True
        assert len(report['sinais_vitais']) == 6
        assert 'tabela' in client.get('/v1/sinais-vitais/tabela-referencia?sinal=HR').json()
        rows = list(csv.DictReader(io.StringIO(client.get('/v1/sinais-vitais/datalhamento?id=demo-001').text)))
        assert len(rows) == 120
        assert {'HR', 'SpO2', 'NBP Sys', 'NBP Dias', 'PULSE', 'RESP'} <= rows[0].keys()
        assert client.get('/v1/sinais-vitais/relatorio').status_code == 422
        assert client.get('/v1/sinais-vitais/relatorio?id=unknown').status_code == 404
        assert client.post('/v1/sinais-vitais/', json={'id': 'demo-001'}).status_code == 403


def test_demo_exercise_reports_and_cors(monkeypatch):
    with demo(monkeypatch) as client:
        catalog = client.get('/v1/fisioterapia/catalogo').json()
        assert catalog['demo'] is True
        assert len(catalog['exercises']) == 4
        for video in catalog['videos']:
            task = client.post('/v1/fisioterapia/analises', json={'video_id': video['id']})
            assert task.status_code == 202
            result = client.get('/v1/fisioterapia/analises/' + task.json()['id'] + '/relatorio').json()
            assert result['demo'] is True
            assert result['summary']['total'] == len(result['repetitions'])
            assert all(rep['reference_label'] is None for rep in result['repetitions'])
        assert client.post('/v1/fisioterapia/analises', json={'video_id': 'missing'}).status_code == 404
        assert client.get('/v1/fisioterapia/analises/missing/relatorio').status_code == 404
        assert client.get('/health', headers={'Origin': 'https://demo.example.com'}).headers['access-control-allow-origin'] == 'https://demo.example.com'
        assert 'access-control-allow-origin' not in client.get('/health', headers={'Origin': 'https://evil.example.com'}).headers


def test_demo_starts_without_heavy_dependencies():
    code = '''
import builtins, os
os.environ['DEMO_MODE'] = '1'
original = builtins.__import__
def checked(name, *args, **kwargs):
    if name.split('.')[0] in {'pandas','numpy','wfdb','openai','cv2','ultralytics','sklearn','joblib','av'}:
        raise ImportError('Heavy dependency blocked: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = checked
from main import app
assert app.openapi()['info']['title'] == 'Prontuário Digital — Demonstração'
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == 0, result.stderr
