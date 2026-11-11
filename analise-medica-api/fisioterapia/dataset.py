import csv
import re
import stat
import zipfile
from pathlib import Path

import requests

from .config import EXERCISES, digest, fingerprint, read_json, write_json

RECORD_URL = 'https://zenodo.org/api/records/13305826'


def verify_file(path: Path, checksum: str) -> None:
    algorithm, expected = checksum.split(':', 1)
    if digest(path, algorithm) != expected:
        raise ValueError(f'Arquivo com checksum inválido: {path.name}')


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            target = (base / item.filename).resolve()
            if not target.is_relative_to(base) or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('ZIP contém caminho não permitido.')
        for item in source.infolist():
            # Do not retain exercises outside this module, when encoded in the path.
            exercise = re.search(r'(?:^|/)Ex(?:ercise)?[_ -]?([1-6])(?:/|[_ -])', item.filename, re.I)
            if exercise and int(exercise[1]) not in EXERCISES:
                continue
            source.extract(item, base)


def video_path(root: Path, video: dict) -> Path:
    base = (root / 'videos').resolve()
    target = (root / video['relative_path']).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError('Vídeo ausente ou caminho não permitido no catálogo.')
    return target


def load_annotations(path: Path) -> dict:
    by_video = {}
    seen = set()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter=';')
        required = {'video_id', 'exercise_id', 'person_id', 'repetition_number', 'first_frame', 'last_frame', 'correctness'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV de segmentação sem as colunas obrigatórias.')
        for raw in reader:
            row = dict(raw)
            for key in required - {'video_id'}:
                row[key] = int(row[key])
            if row['exercise_id'] not in EXERCISES:
                continue
            key = (row['video_id'], row['repetition_number'])
            if key in seen:
                raise ValueError('Anotação de repetição duplicada.')
            seen.add(key)
            if row['correctness'] not in (0, 1) or row['first_frame'] < 1 or row['last_frame'] < row['first_frame']:
                raise ValueError('Rótulo ou intervalo de frames inválido.')
            by_video.setdefault(row['video_id'], []).append(row)
    for repetitions in by_video.values():
        repetitions.sort(key=lambda r: r['first_frame'])
        if any(a['last_frame'] >= b['first_frame'] for a, b in zip(repetitions, repetitions[1:])):
            raise ValueError('Intervalos de frames sobrepostos.')
    return by_video


def build_catalog(root: Path) -> dict:
    import cv2
    annotations = load_annotations(root / 'downloads/Segmentation.csv')
    videos = []
    identities = set()
    for path in sorted((root / 'videos').rglob('*.mp4')):
        recording = re.search(r'PM_\d+', path.stem)
        if not recording or recording[0] not in annotations:
            continue
        reps = annotations[recording[0]]
        cameras = set(re.findall(r'Camera[_ -]?(17|18)(?!\d)', path.as_posix(), re.I))
        if len(cameras) != 1:
            raise ValueError(f'Associação de câmera ausente ou ambígua: {path.name}')
        camera = int(next(iter(cameras)))
        identity = (recording[0], camera)
        if identity in identities:
            raise ValueError(f'Associação duplicada de vídeo/câmera: {identity}')
        identities.add(identity)
        if len({(r['exercise_id'], r['person_id']) for r in reps}) != 1:
            raise ValueError('Exercício/participante inconsistente no CSV.')
        capture = cv2.VideoCapture(str(path))
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS))
            count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            width, height = int(capture.get(3)), int(capture.get(4))
        finally:
            capture.release()
        if abs(fps - 30) > 0.01 or width <= 0 or height <= 0:
            raise ValueError(f'FPS/geometria incompatível com anotações de 30 FPS: {path.name}')
        if any(r['last_frame'] > count for r in reps):
            raise ValueError(f'Intervalo de frames fora do vídeo: {path.name}')
        videos.append({
            'id': fingerprint(identity)[:20], 'recording_id': recording[0],
            'exercise_id': reps[0]['exercise_id'], 'person_id': reps[0]['person_id'],
            'camera': camera, 'relative_path': path.relative_to(root).as_posix(),
            'sha256': digest(path), 'fps': fps, 'frame_count': count,
            'width': width, 'height': height, 'repetitions': reps,
        })
    if not videos:
        raise ValueError('Nenhum vídeo Ex1–Ex4 encontrado. Execute a preparação do dataset.')
    result = {
        'record': '13305826', 'frame_convention': 'source-one-based-inclusive/internal-zero-based',
        'frame_convention_evidence':'Source first_frame reaches 1; PM_045 and PM_103 last_frame equal video frame_count in both cameras. Raw frame values are preserved.',
        'annotation_sha256': digest(root / 'downloads/Segmentation.csv'),
        'exercises': [{'id': key, 'name': value} for key, value in EXERCISES.items()],
        'videos': videos,
    }
    write_json(root / 'catalog.json', result)
    return result


def load_catalog(root: Path) -> dict:
    path = root / 'catalog.json'
    if not path.exists():
        raise ValueError('Dataset não preparado. Execute: python -m fisioterapia prepare')
    return read_json(path)


def prepare(root: Path) -> dict:
    downloads = root / 'downloads'
    downloads.mkdir(parents=True, exist_ok=True)
    response = requests.get(RECORD_URL, timeout=60)
    response.raise_for_status()
    record = response.json()
    write_json(downloads / 'record.json', record)
    for name in ('Segmentation.csv', 'Segmentation.txt', 'videos.zip'):
        metadata = next(f for f in record['files'] if f['key'] == name)
        target = downloads / name
        if target.exists():
            verify_file(target, metadata['checksum'])
            continue
        partial = downloads / (name + '.part')
        ready = False
        if partial.exists() and partial.stat().st_size == metadata['size']:
            try:
                verify_file(partial, metadata['checksum'])
                ready = True
            except ValueError:
                partial.unlink()
        if not ready:
            with requests.get(metadata['links']['self'], stream=True, timeout=(30, 120)) as source:
                source.raise_for_status()
                with partial.open('wb') as output:
                    for block in source.iter_content(1024 * 1024):
                        output.write(block)
            try:
                verify_file(partial, metadata['checksum'])
            except ValueError:
                partial.unlink()
                raise
        partial.replace(target)
    marker = root / 'videos/.extracted.json'
    checksum = digest(downloads / 'videos.zip', 'md5')
    if not marker.exists() or read_json(marker).get('md5') != checksum:
        safe_extract(downloads / 'videos.zip', root / 'videos')
        write_json(marker, {'md5': checksum})
    result = build_catalog(root)
    expected = {(recording,camera) for recording in load_annotations(downloads/'Segmentation.csv') for camera in (17,18)}
    actual = {(v['recording_id'],v['camera']) for v in result['videos']}
    if actual != expected:
        raise ValueError('Dataset incompleto: faltam gravações/câmeras das anotações selecionadas.')
    return result
