from fastapi.testclient import TestClient

from main import create_app
from fisioterapia.jobs import AnalysisService
import subprocess
import sys
from pathlib import Path


def test_existing_vital_sign_routes_remain_registered(tmp_path):
    with TestClient(create_app(AnalysisService(tmp_path))) as client:
        schema = client.get('/openapi.json').json()
        assert '/v1/sinais-vitais/' in schema['paths']
        assert '/v1/sinais-vitais/datalhamento' in schema['paths']
        assert client.get('/v1/sinais-vitais/relatorio').status_code == 422


def test_api_can_start_without_optional_vision_libraries():
    code = '''
import builtins
original = builtins.__import__
def checked(name,*args,**kwargs):
    if name.split('.')[0] in {'cv2','ultralytics','sklearn','joblib','av'}:
        raise ImportError('Optional dependency blocked: '+name)
    return original(name,*args,**kwargs)
builtins.__import__ = checked
from main import create_app
assert '/v1/sinais-vitais/' in create_app().openapi()['paths']
'''
    result = subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,
                            cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == 0, result.stderr
