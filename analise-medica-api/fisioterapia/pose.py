import os
from pathlib import Path

import cv2
import numpy as np

from .config import PIPELINE_VERSION, digest, fingerprint, read_json, write_json
from .dataset import video_path


class PersonTracker:
    """Conservative spatial continuity; ambiguity leaves a gap, never a new identity."""
    def __init__(self):
        self.box = None
        self.gap = 0
        self.lost = False

    def _missing(self):
        if self.box is not None:
            self.gap += 1
            if self.gap > 15:
                self.lost = True
        return None

    def select(self, boxes: np.ndarray) -> int | None:
        if self.lost:
            return None
        if not len(boxes):
            return self._missing()
        if self.box is None:
            areas = np.maximum(0, boxes[:,2]-boxes[:,0]) * np.maximum(0, boxes[:,3]-boxes[:,1])
            order = np.argsort(areas)[::-1]
            if len(order) > 1 and areas[order[1]] >= areas[order[0]] * .7:
                return None
            selected = int(order[0])
        else:
            x1 = np.maximum(boxes[:,:2], self.box[:2])
            x2 = np.minimum(boxes[:,2:], self.box[2:])
            intersection = np.prod(np.maximum(0, x2-x1), axis=1)
            area = np.prod(np.maximum(0, boxes[:,2:]-boxes[:,:2]), axis=1)
            previous = np.prod(self.box[2:]-self.box[:2])
            iou = intersection / np.maximum(area+previous-intersection, 1e-9)
            order = np.argsort(iou)[::-1]
            if iou[order[0]] < .15 or (len(order)>1 and iou[order[1]] > iou[order[0]]*.8):
                return self._missing()
            selected = int(order[0])
        self.box = boxes[selected].copy()
        self.gap = 0
        return selected


def pose_settings(root: Path) -> dict:
    path = root / 'runtime.json'
    return read_json(path) if path.is_file() else {'device':'cpu','batch':1}


def pose_engine() -> dict:
    import cv2
    import torch
    import ultralytics
    import av
    return {'pipeline':PIPELINE_VERSION,'ultralytics':ultralytics.__version__,
            'torch':str(torch.__version__),'opencv':cv2.__version__,
            'imgsz':640,'conf':.25,'tracker':'spatial-v2-gap15','av':av.__version__,
            'decoder':'pyav-bilinear640-v1'}


def pose_identity(video_hash: str, weights_hash: str, device: str = 'cpu', batch: int = 1) -> str:
    return fingerprint({'engine':pose_engine(),'video':video_hash,'weights':weights_hash,'device':device,'batch':batch})


def weights_path(root: Path) -> Path:
    path = root / 'models/yolov8n-pose.pt'
    if not path.is_file():
        raise ValueError('Pesos YOLOv8 ausentes. Execute: python -m fisioterapia weights')
    return path


def extract_pose(root: Path, video: dict, progress=None) -> dict:
    from ultralytics import YOLO
    from .video import video_batches, prefetched_batches
    path = video_path(root, video)
    actual_hash = digest(path)
    if actual_hash != video['sha256']:
        raise ValueError('Vídeo mudou. Execute novamente a preparação do catálogo.')
    weights = weights_path(root)
    settings = pose_settings(root)
    identity = pose_identity(actual_hash, digest(weights), **settings)
    folder = root / 'poses'
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder / f'{identity}.npz'
    meta = cache.with_suffix('.json')
    if cache.exists() and meta.exists():
        info = read_json(meta)
        if info.get('identity') == identity:
            try:
                if info.get('cache_sha256') != digest(cache):
                    raise ValueError('Cache de postura alterado.')
                with np.load(cache, allow_pickle=False) as source:
                    points = source['points']
                    if points.shape != (video['frame_count'],17,3) or not np.isfinite(points).all():
                        raise ValueError('Cache de postura incompleto.')
                    return {'points': points, **info}
            except (ValueError,OSError,KeyError):
                pass  # Invalid local cache is regenerated, never treated as a prediction.
    model = YOLO(str(weights))
    cv2.setNumThreads(1)
    tracker = PersonTracker()
    frames = []
    # One thread avoids oversubscribing CPU during this serial local job.
    import torch
    torch.set_num_threads(2)
    batches = video_batches(path,settings['batch'],(video['width'],video['height']))
    for batch in prefetched_batches(batches):
        results = model.predict(batch, **settings, imgsz=640, conf=.25, verbose=False)
        for result in results:
            result = result.cpu()
            boxes = result.boxes.xyxy.numpy() if result.boxes is not None else np.empty((0,4))
            selected = tracker.select(boxes)
            points = np.zeros((17,3), dtype=np.float32)
            if selected is not None and result.keypoints is not None:
                points[:,:2] = result.keypoints.xyn[selected].numpy()
                points[:,2] = result.keypoints.conf[selected].numpy()
            frames.append(points)
        if progress:
            progress(len(frames), video['frame_count'])
    points = np.asarray(frames, dtype=np.float32)
    if len(points) != video['frame_count']:
        raise ValueError('Decodificação incompleta: número de frames diferente do catálogo.')
    temporary = cache.with_suffix('.tmp.npz')
    np.savez_compressed(temporary, points=points)
    os.replace(temporary, cache)
    info = {'identity': identity, 'video_sha256': actual_hash, 'weights_sha256': digest(weights),
            'frame_count': len(points), 'fps': video['fps'], 'width':video['width'], 'height':video['height'],
            'cache_sha256':digest(cache),'engine':pose_engine(),'settings':settings}
    write_json(meta, info)
    if progress:
        progress(len(points), len(points))
    return {'points':points, **info}
