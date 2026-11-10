import hashlib
import json
import os
import tempfile
from pathlib import Path

EXERCISES = {
    1: 'Abdução do braço direito',
    2: 'Movimento dos braços entre V e W',
    3: 'Flexão com as mãos apoiadas na mesa',
    4: 'Abdução de perna',
}
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / 'data/fisioterapia'
PIPELINE_VERSION = 'rehab24-yolov8-v1'


def root_path() -> Path:
    return Path(os.getenv('FISIOTERAPIA_DATA_DIR', str(DEFAULT_ROOT))).resolve()


def digest(path: Path, algorithm: str = 'sha256') -> str:
    result = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            name = stream.name
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if name and Path(name).exists():
            Path(name).unlink()
