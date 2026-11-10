import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .config import EXERCISES, digest, fingerprint, read_json, write_json
from .dataset import load_catalog, video_path


def analysis_identity(root: Path, video: dict) -> str:
    from .training import current_experiment
    from .pose import pose_identity, pose_settings, weights_path
    experiment = current_experiment(root)
    if digest(video_path(root,video)) != video['sha256']:
        raise ValueError('Vídeo alterado. Prepare o dataset e treine novamente.')
    model = experiment['exercises'][str(video['exercise_id'])]
    fold = next((f for f in model['folds'] if video['person_id'] in f['test_participants']),None)
    if fold is None:
        raise ValueError('Não existe modelo de avaliação para este participante.')
    artifact = (root/fold['path']).resolve()
    if not artifact.is_relative_to((root/'experiments').resolve()) or digest(artifact) != fold['sha256']:
        raise ValueError('Artefato do modelo inválido. Treine novamente.')
    pose = pose_identity(video['sha256'],digest(weights_path(root)),**pose_settings(root))
    return fingerprint({'video':video,'experiment':experiment['identity'],'model':fold['sha256'],'pose':pose})


def run_analysis(root: Path, video: dict, progress) -> dict:
    from .pose import extract_pose
    from .training import current_experiment, predict_repetitions
    pose = extract_pose(root,video,lambda n,total: progress(.8*n/total))
    rows = predict_repetitions(root,video,pose)
    repetitions = []
    for row in rows:
        expected = row.pop('expected',None)
        repetitions.append(row | {'reference_label':expected,
            'agreement': row['prediction']==expected if row['prediction'] is not None and expected is not None else None})
    return {
        'video':{k:video[k] for k in ('id','recording_id','exercise_id','person_id','camera','fps')},
        'exercise':EXERCISES[video['exercise_id']],
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'model_identity':current_experiment(root)['identity'], 'pose_identity':pose['identity'],
        'pose_sha256':pose['cache_sha256'],
        'segmentation':'Intervalos de repetição fornecidos pelo REHAB24-6.',
        'summary':{'total':len(rows),'correct':sum(r['prediction']==1 for r in rows),
                   'incorrect':sum(r['prediction']==0 for r in rows),
                   'nonconclusive':sum(r['prediction'] is None for r in rows),
                   'mean_pose_coverage':sum(r['coverage'] for r in rows)/len(rows) if rows else 0},
        'repetitions':repetitions,
        'limitations':['Avaliação acadêmica binária, sem diagnóstico ou identificação da causa do erro.',
                       'Ângulos são projeções 2D e dependem do ponto de vista da câmera.',
                       'Predições usam um modelo que excluiu o participante do treinamento.'],
    }


class AnalysisService:
    def __init__(self, root: Path, runner=None):
        self.root = root.resolve()
        self.runner = runner or run_analysis
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1,thread_name_prefix='fisioterapia')
        (self.root/'jobs').mkdir(parents=True,exist_ok=True)
        for path in (self.root/'jobs').glob('*.json'):
            job = read_json(path)
            if job.get('status') in ('pendente','processando'):
                job.update(status='falhou',error='Processamento interrompido pelo reinício do servidor. Inicie uma nova análise.')
                write_json(path,job)

    def close(self):
        self.executor.shutdown(wait=True,cancel_futures=False)

    def catalog(self) -> dict:
        catalog = load_catalog(self.root)
        fields = ('id','recording_id','exercise_id','person_id','camera','fps','frame_count','width','height')
        return {'exercises':catalog['exercises'],
                'videos':[{k:v[k] for k in fields} for v in catalog['videos']]}

    def video(self, video_id: str) -> dict:
        item = next((v for v in load_catalog(self.root)['videos'] if v['id']==video_id),None)
        if item is None:
            raise LookupError('Vídeo não encontrado no catálogo.')
        return item

    def get(self, job_id: str) -> dict:
        if not re.fullmatch(r'[a-f0-9]{32}',job_id):
            raise LookupError('Análise não encontrada.')
        path = self.root/'jobs'/f'{job_id}.json'
        if not path.is_file():
            raise LookupError('Análise não encontrada.')
        return read_json(path)

    def create(self, video_id: str) -> dict:
        with self.lock:
            video = self.video(video_id)
            identity = analysis_identity(self.root,video)
            for path in (self.root/'jobs').glob('*.json'):
                job = read_json(path)
                if job.get('identity') == identity:
                    if job['status'] in ('pendente','processando'):
                        return job
                    if job['status']=='concluido' and self._result_available(job['id']):
                        return job
            job = {'id':uuid.uuid4().hex,'video_id':video_id,'identity':identity,
                   'status':'pendente','progress':0.,'error':None,
                   'created_at':datetime.now(timezone.utc).isoformat()}
            write_json(self.root/'jobs'/f"{job['id']}.json",job)
            self.executor.submit(self._run,job['id'],video)
            return job

    def _result_available(self, job_id: str) -> bool:
        report_path = self.root/'reports'/f'{job_id}.json'
        if not report_path.is_file():
            return False
        try:
            report = read_json(report_path)
            key = report['pose_identity']
            if not re.fullmatch(r'[a-f0-9]{64}',key):
                return False
            pose = self.root/'poses'/f'{key}.npz'
            return pose.is_file() and digest(pose)==report.get('pose_sha256')
        except (ValueError,OSError,KeyError):
            return False

    def _update(self, job_id: str, **changes):
        with self.lock:
            job = self.get(job_id)
            job.update(changes)
            write_json(self.root/'jobs'/f'{job_id}.json',job)

    def _run(self, job_id: str, video: dict):
        try:
            self._update(job_id,status='processando',progress=.01)
            report = self.runner(self.root,video,lambda value:self._update(job_id,progress=round(float(value),3)))
            if analysis_identity(self.root,video) != self.get(job_id)['identity']:
                raise ValueError('Dados ou modelo mudaram durante a análise. Inicie novamente.')
            write_json(self.root/'reports'/f'{job_id}.json',report)
            prefix = f'/v1/fisioterapia/analises/{job_id}'
            self._update(job_id,status='concluido',progress=1.,report_url=prefix+'/relatorio',pose_url=prefix+'/pose')
        except Exception as error:
            self._update(job_id,status='falhou',error=str(error)[:500])

    def report_path(self, job_id: str) -> Path:
        job = self.get(job_id)
        if job['status'] != 'concluido':
            raise RuntimeError('Relatório ainda não disponível para esta análise.')
        path = self.root/'reports'/f'{job_id}.json'
        if not path.is_file():
            raise ValueError('Resultado ausente. Inicie uma nova análise.')
        return path

    def result(self, job_id: str) -> dict:
        return read_json(self.report_path(job_id))

    def pose(self, job_id: str) -> dict:
        import numpy as np
        report = self.result(job_id)
        identity = report['pose_identity']
        if not re.fullmatch(r'[a-f0-9]{64}',identity):
            raise ValueError('Cache de postura inválido.')
        path = self.root/'poses'/f'{identity}.npz'
        if not path.is_file():
            raise ValueError('Cache de postura ausente. Inicie nova análise.')
        if digest(path) != report.get('pose_sha256'):
            raise ValueError('Cache de postura alterado. Inicie nova análise.')
        with np.load(path,allow_pickle=False) as stored:
            points = np.round(stored['points'].astype(float),5).tolist()
        return {'fps':report['video']['fps'],'points':points}
