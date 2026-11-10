import time
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline

from .config import EXERCISES, PIPELINE_VERSION, digest, fingerprint, read_json, write_json
from .dataset import load_catalog, video_path
from .features import FEATURE_VERSION, repetition_features
from .pose import extract_pose, weights_path, pose_settings, pose_engine

RF_PARAMS = dict(n_estimators=300, min_samples_leaf=2, class_weight='balanced', random_state=42, n_jobs=-1)


def grouped_folds(rows: list[dict]):
    groups = np.array([row['person_id'] for row in rows])
    if len(set(groups)) < 5:
        raise ValueError('São necessários pelo menos cinco participantes para a avaliação agrupada.')
    yield from GroupKFold(n_splits=5).split(np.arange(len(rows)), groups=groups)


def _metrics(y, predicted) -> dict:
    if not len(y):
        return {'balanced_accuracy': None, 'f1_macro': None, 'precision_incorrect':None,
                'recall_incorrect':None, 'confusion_matrix':[[0,0],[0,0]], 'count':0}
    return {'balanced_accuracy': float(balanced_accuracy_score(y,predicted)),
            'f1_macro': float(f1_score(y,predicted,labels=[0,1],average='macro',zero_division=0)),
            'precision_incorrect':float(precision_score(y,predicted,pos_label=0,zero_division=0)),
            'recall_incorrect':float(recall_score(y,predicted,pos_label=0,zero_division=0)),
            'confusion_matrix':confusion_matrix(y,predicted,labels=[0,1]).tolist(), 'count':len(y)}


def source_identity(root: Path, catalog: dict | None = None) -> str:
    catalog = catalog or load_catalog(root)
    annotation_hash = digest(root / 'downloads/Segmentation.csv')
    if catalog.get('annotation_sha256') != annotation_hash:
        raise ValueError('As anotações mudaram. Prepare o dataset e treine novamente.')
    media = []
    for video in catalog['videos']:
        path = video_path(root,video)
        info = path.stat()
        media.append([video['id'],video['sha256'],info.st_size,info.st_mtime_ns])
    return fingerprint({'catalog':catalog,'media':media,'weights':digest(weights_path(root)),
                        'pipeline':PIPELINE_VERSION,'features':FEATURE_VERSION,'rf':RF_PARAMS,
                        'sklearn':sklearn.__version__,'pose_settings':pose_settings(root),'pose_engine':pose_engine()})


def repetition_rows(video: dict, pose: dict) -> list[dict]:
    rows = []
    for rep in video['repetitions']:
        first,last = rep['first_frame']-1,rep['last_frame']-1
        result = repetition_features(pose['points'][first:last+1],video['exercise_id'],(video['width'],video['height']))
        row = {'video_id':video['id'],'exercise_id':video['exercise_id'],'person_id':video['person_id'],
               'camera':video['camera'],'repetition_number':rep['repetition_number'],
               'first_frame':rep['first_frame'],'last_frame':rep['last_frame'],
               'first_frame_index':first,'last_frame_index':last,'start_seconds':first/video['fps'],
               'end_seconds':(last+1)/video['fps'], **result}
        # Reference is optional here: it is never consumed by feature extraction or prediction.
        if 'correctness' in rep:
            row['expected'] = rep['correctness']
        rows.append(row)
    return rows


def train_records(root: Path, rows: list[dict], source: str) -> dict:
    start = time.monotonic()
    identity = fingerprint({'source':source,'feature_version':FEATURE_VERSION,'rf':RF_PARAMS,'sklearn':sklearn.__version__})
    directory = root / 'experiments' / identity
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {'identity':identity,'source_identity':source,'feature_version':FEATURE_VERSION,
                'rf_parameters':RF_PARAMS,'sklearn_version':sklearn.__version__,'exercises':{},
                'frame_convention':'source-one-based-inclusive/internal-zero-based','segmentation':'official_intervals',
                'limitations':['Classificação acadêmica binária; não identifica tipo ou gravidade do erro.',
                               'Intervalos de repetição fornecidos pelo dataset; não detectados automaticamente.']}
    predictions = []
    for exercise in EXERCISES:
        all_rows = [r for r in rows if r['exercise_id']==exercise]
        if not all_rows:
            raise ValueError(f'Não há dados do exercício {exercise}.')
        usable = [r for r in all_rows if r['features'] is not None]
        if not usable or set(r['expected'] for r in usable) != {0,1}:
            raise ValueError(f'Exercício {exercise}: treino exige as duas classes e postura válida.')
        names = sorted(usable[0]['features'])
        if any(sorted(r['features']) != names for r in usable):
            raise ValueError('Esquema de features inconsistente.')
        x = np.asarray([[r['features'][k] for k in names] for r in usable],dtype=float)
        y = np.asarray([r['expected'] for r in usable])
        predicted = np.zeros(len(usable), dtype=int)
        baseline = np.zeros(len(usable), dtype=int)
        groups = []
        for fold,(train_all,test_all) in enumerate(grouped_folds(all_rows)):
            train_groups = {all_rows[i]['person_id'] for i in train_all}
            test_groups = {all_rows[i]['person_id'] for i in test_all}
            train_idx = np.array([i for i,r in enumerate(usable) if r['person_id'] in train_groups],dtype=int)
            test_idx = np.array([i for i,r in enumerate(usable) if r['person_id'] in test_groups],dtype=int)
            if set(y[train_idx]) != {0,1}:
                raise ValueError(f'Exercício {exercise}, grupo {fold}: duas classes necessárias no treino.')
            model = make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),RandomForestClassifier(**RF_PARAMS))
            model.fit(x[train_idx], y[train_idx])
            if len(test_idx):
                predicted[test_idx] = model.predict(x[test_idx])
            dummy = DummyClassifier(strategy='most_frequent').fit(x[train_idx],y[train_idx])
            if len(test_idx):
                baseline[test_idx] = dummy.predict(x[test_idx])
            train_people = sorted(set(usable[i]['person_id'] for i in train_idx))
            test_people = sorted(test_groups)
            model_path = directory / f'ex{exercise}-fold{fold}.joblib'
            joblib.dump(model,model_path)
            groups.append({'fold':fold,'training_participants':train_people,'test_participants':test_people,
                           'path':model_path.relative_to(root).as_posix(),'sha256':digest(model_path)})
        metrics = _metrics(y,predicted)
        metrics.update(coverage=len(usable)/len(all_rows),total=len(all_rows),nonconclusive=len(all_rows)-len(usable))
        metrics['nonconclusive_by_label'] = {
            str(label):sum(r['features'] is None and r['expected']==label for r in all_rows) for label in (0,1)
        }
        incorrect_total=sum(r['expected']==0 for r in all_rows)
        detected_incorrect=int(np.sum((y==0)&(predicted==0)))
        metrics['recall_incorrect_all'] = detected_incorrect/incorrect_total if incorrect_total else None
        dummy_metrics = _metrics(y,baseline)
        by_camera = {}
        by_person = {}
        for key,target in [('camera',by_camera),('person_id',by_person)]:
            for value in sorted(set(r[key] for r in all_rows)):
                indices = [i for i,r in enumerate(usable) if r[key]==value]
                total = sum(r[key]==value for r in all_rows)
                summary = _metrics(y[indices],predicted[indices])
                summary.update(total=total,nonconclusive=total-len(indices),coverage=len(indices)/total)
                target[str(value)] = summary
        manifest['exercises'][str(exercise)] = {'feature_names':names,'folds':groups,'metrics':metrics,
                'baseline':dummy_metrics,'by_camera':by_camera,'by_person':by_person,
                'above_baseline':metrics['balanced_accuracy']>dummy_metrics['balanced_accuracy']}
        for i,row in enumerate(usable):
            predictions.append({k:v for k,v in row.items() if k not in ('features','series')} | {'prediction':int(predicted[i])})
    manifest['duration_seconds'] = round(time.monotonic()-start,3)
    write_json(directory/'evaluation.json',manifest)
    write_json(directory/'predictions.json',predictions)
    write_json(root/'experiment.json',manifest)
    return manifest


def train(root: Path) -> dict:
    catalog = load_catalog(root)
    source = source_identity(root,catalog)
    rows = []
    for video in catalog['videos']:
        print(f"Features {video['recording_id']} câmera {video['camera']}",flush=True)
        for row in repetition_rows(video,extract_pose(root,video)):
            row.pop('series',None)
            rows.append(row)
    return train_records(root,rows,source)


def current_experiment(root: Path) -> dict:
    path = root/'experiment.json'
    if not path.exists():
        raise ValueError('Classificadores ausentes. Execute: python -m fisioterapia train')
    manifest = read_json(path)
    if manifest['source_identity'] != source_identity(root):
        raise ValueError('Experimento desatualizado. Execute novamente a extração e o treinamento.')
    return manifest


def predict_rows(root: Path, rows: list[dict], manifest: dict) -> list[dict]:
    results = []
    loaded = {}
    for row in rows:
        result = {k:v for k,v in row.items() if k != 'features'}
        result['measures'] = row['features']
        if row['features'] is None:
            results.append(result | {'status':'Não conclusivo','prediction':None,'training_participants':[]})
            continue
        info = manifest['exercises'][str(row['exercise_id'])]
        fold = next((f for f in info['folds'] if row['person_id'] in f['test_participants']),None)
        if fold is None or row['person_id'] in fold['training_participants']:
            raise ValueError('Não existe modelo que excluiu este participante do treinamento.')
        path = (root/fold['path']).resolve()
        if not path.is_relative_to((root/'experiments').resolve()) or digest(path)!=fold['sha256']:
            raise ValueError('Artefato do modelo inválido. Treine novamente.')
        if str(path) not in loaded:
            # Only locally generated, hash-verified artifacts; never accept model uploads.
            loaded[str(path)] = joblib.load(path)
        vector = np.asarray([[row['features'][k] for k in info['feature_names']]],dtype=float)
        label = int(loaded[str(path)].predict(vector)[0])
        results.append(result | {'status':'Correto' if label else 'Incorreto','prediction':label,
                                'training_participants':fold['training_participants'],'fold':fold['fold']})
    return results


def predict_repetitions(root: Path, video: dict, pose: dict) -> list[dict]:
    return predict_rows(root,repetition_rows(video,pose),current_experiment(root))
