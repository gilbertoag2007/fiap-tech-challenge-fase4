"""Medidas projetadas em 2D; não representam limites clínicos."""
import numpy as np

FEATURE_VERSION = 'geometry-2d-v1'
MIN_CONFIDENCE = .5
MIN_COVERAGE = .6


def angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
    u, v = a - b, c - b
    denominator = np.linalg.norm(u) * np.linalg.norm(v)
    if not np.isfinite(denominator) or denominator < 1e-9:
        return None
    return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / denominator, -1, 1))))


def _frame_measures(frame: np.ndarray, exercise: int) -> dict:
    def valid(*ids):
        return all(np.isfinite(frame[i]).all() and frame[i, 2] >= MIN_CONFIDENCE for i in ids)

    def joint(a, b, c):
        return angle(frame[a, :2], frame[b, :2], frame[c, :2]) if valid(a,b,c) else None

    def lean():
        if not valid(5,6,11,12):
            return None
        shoulder = (frame[5,:2] + frame[6,:2]) / 2
        hip = (frame[11,:2] + frame[12,:2]) / 2
        return angle(shoulder, hip, hip + np.array([0.,-1.]))

    if exercise == 1:
        return {'ombro_direito': joint(8,6,12), 'cotovelo_direito': joint(6,8,10), 'inclinacao_tronco': lean()}
    if exercise == 2:
        right, left = joint(8,6,12), joint(7,5,11)
        return {'ombro_direito': right, 'ombro_esquerdo': left,
                'cotovelo_direito': joint(6,8,10), 'cotovelo_esquerdo': joint(5,7,9),
                'assimetria_bracos': abs(right-left) if right is not None and left is not None else None}
    if exercise == 3:
        sides = [(6,8,10,12,16), (5,7,9,11,15)]
        side = max(sides, key=lambda ids: min(frame[i,2] if np.isfinite(frame[i]).all() else 0 for i in ids))
        s,e,w,h,a = side
        return {'cotovelo': joint(s,e,w), 'alinhamento_corporal': joint(s,h,a)}
    if exercise == 4:
        sides = [(5,11,13,15), (6,12,14,16)]
        measured = [(joint(s,h,k), (s,h,k,a)) for s,h,k,a in sides]
        usable = [(value, side) for value,side in measured if value is not None]
        if usable:
            hip_angle, (_,h,k,a) = min(usable, key=lambda row: row[0])
            abduction, knee = 180-hip_angle, joint(h,k,a)
        else:
            abduction, knee = None, None
        separation = None
        if valid(5,6,11,12,15,16):
            torso = np.linalg.norm((frame[5,:2]+frame[6,:2]-frame[11,:2]-frame[12,:2])/2)
            if torso > 1e-9:
                separation = float(np.linalg.norm(frame[15,:2]-frame[16,:2])/torso)
        return {'abducao_perna': abduction, 'joelho': knee, 'separacao_pernas': separation, 'inclinacao_tronco': lean()}
    raise ValueError('Exercício fora do escopo Ex1–Ex4.')


ESSENTIAL = {1: ('ombro_direito','cotovelo_direito'),
             2: ('ombro_direito','ombro_esquerdo','cotovelo_direito','cotovelo_esquerdo'),
             3: ('cotovelo','alinhamento_corporal'), 4: ('abducao_perna','joelho')}


def repetition_features(points: np.ndarray, exercise: int, image_size: tuple = (1,1)) -> dict:
    points = np.array(points, dtype=float, copy=True)
    if points.ndim != 3 or points.shape[1:] != (17,3) or exercise not in ESSENTIAL:
        raise ValueError('Geometria ou exercício inválido.')
    if len(image_size) != 2 or min(image_size) <= 0:
        raise ValueError('Dimensões da imagem inválidas.')
    points[:,:,:2] *= np.asarray(image_size)
    rows = [_frame_measures(frame, exercise) for frame in points]
    valid = [all(row[k] is not None for k in ESSENTIAL[exercise]) for row in rows]
    coverage = sum(valid) / len(rows) if rows else 0.
    reason = None if coverage >= MIN_COVERAGE else 'Postura insuficiente: menos de 60% dos frames com pontos essenciais confiáveis.'
    features = {}
    if reason is None:
        for key in sorted(rows[0]):
            values = np.array([np.nan if row[key] is None else row[key] for row in rows])
            finite = values[np.isfinite(values)]
            stats = {'mean': np.mean, 'std': np.std, 'min': np.min, 'max': np.max,
                     'q10': lambda x: np.quantile(x,.1), 'q50': np.median, 'q90': lambda x: np.quantile(x,.9),
                     'range': np.ptp}
            for suffix, fn in stats.items():
                features[f'{key}_{suffix}'] = float(fn(finite)) if len(finite) else None
            # Only adjacent valid frames; never bridge an occlusion.
            diffs = np.abs(np.diff(values))
            diffs = diffs[np.isfinite(diffs)]
            features[f'{key}_variation'] = float(np.mean(diffs)) if len(diffs) else None
    return {'features': features if reason is None else None, 'coverage': coverage, 'series': rows, 'reason': reason}
