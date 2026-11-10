import threading
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from fisioterapia.config import write_json, digest
from fisioterapia.jobs import AnalysisService
from main import create_app


@pytest.fixture
def service(tmp_path,monkeypatch):
    media = tmp_path/'videos/Ex1/test.mp4'
    media.parent.mkdir(parents=True)
    media.write_bytes(b'0123456789video')
    video = dict(id='a'*20,recording_id='PM_001',exercise_id=1,person_id=1,camera=17,
                 relative_path='videos/Ex1/test.mp4',sha256='video-a',fps=30,width=64,height=48,
                 frame_count=12,repetitions=[])
    write_json(tmp_path/'catalog.json',{'exercises':[{'id':1,'name':'Braço'}],'videos':[video]})
    state = {'version':'model-a','calls':0,'release':threading.Event(),'fail':False}
    monkeypatch.setattr('fisioterapia.jobs.analysis_identity',lambda root,video: state['version'])
    def runner(root,video,progress):
        state['calls'] += 1
        state['release'].wait(3)
        if state['fail']:
            raise ValueError('Postura indisponível')
        progress(.8)
        pose_file = root/'poses'/('e'*64+'.npz')
        pose_file.parent.mkdir(exist_ok=True)
        np.savez_compressed(pose_file,points=np.zeros((12,17,3),dtype=np.float32))
        return {'video':{'id':video['id'],'fps':30},'summary':{'total':1},'repetitions':[
            {'status':'Não conclusivo','prediction':None,'reference_label':0,'coverage':.1}],
            'pose_identity':'e'*64,'pose_sha256':digest(pose_file)}
    instance = AnalysisService(tmp_path,runner=runner)
    yield instance,state
    state['release'].set()
    instance.close()


def completed(service,job):
    instance,state = service
    state['release'].set()
    for _ in range(200):
        result = instance.get(job['id'])
        if result['status'] in ('concluido','falhou'):
            return result
        time.sleep(.01)
    pytest.fail('Tarefa não terminou no prazo do teste.')


def test_duplicate_requests_share_active_job_and_completed_report(service):
    instance,state = service
    first = instance.create('a'*20)
    assert instance.create('a'*20)['id'] == first['id']
    assert completed(service,first)['status'] == 'concluido'
    assert instance.create('a'*20)['id'] == first['id']
    assert state['calls'] == 1
    assert instance.result(first['id'])['repetitions'][0]['status'] == 'Não conclusivo'


def test_model_version_invalidates_completed_result(service):
    instance,state = service
    first = instance.create('a'*20)
    completed(service,first)
    state['version'] = 'model-b'
    assert instance.create('a'*20)['id'] != first['id']


def test_deleted_pose_is_regenerated_by_new_analysis(service):
    instance,state = service
    first = instance.create('a'*20)
    completed(service,first)
    (instance.root/'poses'/('e'*64+'.npz')).unlink()
    second = instance.create('a'*20)
    assert second['id'] != first['id']
    assert completed(service,second)['status']=='concluido'
    assert len(instance.pose(second['id'])['points']) == 12


def test_failure_is_persisted_and_retry_creates_new_job(service):
    instance,state = service
    state['fail'] = True
    first = instance.create('a'*20)
    result = completed(service,first)
    assert result['status'] == 'falhou'
    assert 'Postura' in result['error']
    state['fail'] = False
    assert instance.create('a'*20)['id'] != first['id']


def test_restart_marks_interrupted_jobs_as_failed(tmp_path):
    write_json(tmp_path/'jobs'/('b'*32+'.json'),{'id':'b'*32,'status':'processando','video_id':'a'*20,'identity':'x'})
    instance = AnalysisService(tmp_path)
    try:
        result = instance.get('b'*32)
        assert result['status'] == 'falhou'
        assert 'interrompido' in result['error']
    finally:
        instance.close()


def test_api_catalog_does_not_expose_paths_or_reference_labels(service):
    instance,_ = service
    with TestClient(create_app(instance)) as client:
        response = client.get('/v1/fisioterapia/catalogo')
        assert response.status_code == 200
        video = response.json()['videos'][0]
        assert 'relative_path' not in video
        assert 'repetitions' not in video
        assert video['camera'] == 17


def test_api_task_flow_range_and_local_post_cors(service):
    instance,_ = service
    with TestClient(create_app(instance)) as client:
        headers={'Origin':'http://localhost:5500','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
        preflight = client.options('/v1/fisioterapia/analises',headers=headers)
        assert preflight.status_code == 200
        assert 'POST' in preflight.headers['access-control-allow-methods']
        response = client.post('/v1/fisioterapia/analises',json={'video_id':'a'*20})
        assert response.status_code == 202
        job = response.json()
        completed(service,job)
        assert client.get(f"/v1/fisioterapia/analises/{job['id']}").json()['status'] == 'concluido'
        report = client.get(f"/v1/fisioterapia/analises/{job['id']}/relatorio")
        assert report.status_code == 200
        assert report.json()['summary']['total'] == 1
        assert 'attachment' in report.headers['content-disposition']
        video = client.get('/v1/fisioterapia/videos/'+'a'*20,headers={'Range':'bytes=0-3'})
        assert video.status_code == 206
        assert video.content == b'0123'


def test_unknown_video_and_job_are_404_without_path_access(service):
    instance,_ = service
    with TestClient(create_app(instance)) as client:
        assert client.post('/v1/fisioterapia/analises',json={'video_id':'c'*20}).status_code == 404
        assert client.get('/v1/fisioterapia/analises/not-a-job').status_code == 404
        assert client.post('/v1/fisioterapia/analises',json={'video_id':'../secret'}).status_code == 422


def test_unprepared_dataset_has_configuration_error(tmp_path):
    service = AnalysisService(tmp_path)
    with TestClient(create_app(service)) as client:
        response = client.get('/v1/fisioterapia/catalogo')
        assert response.status_code == 503
        assert 'preparado' in response.json()['detail']


def test_report_is_unavailable_while_processing(service):
    instance,_ = service
    with TestClient(create_app(instance)) as client:
        job = client.post('/v1/fisioterapia/analises',json={'video_id':'a'*20}).json()
        assert client.get(f"/v1/fisioterapia/analises/{job['id']}/relatorio").status_code == 409
