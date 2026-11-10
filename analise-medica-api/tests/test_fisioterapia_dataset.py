import hashlib
import json
import zipfile

import cv2
import numpy as np
import pytest

from fisioterapia.dataset import build_catalog, safe_extract, verify_file, video_path


HEADER = 'video_id;repetition_number;exercise_id;person_id;first_frame;last_frame;cam17_orientation;mocap_erroneous;exercise_subtype;lights_on;extra_person_in_cam17;extra_person_in_cam18;correctness\n'


def make_video(path, fps=30, frames=12):
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (64, 48))
    for _ in range(frames):
        writer.write(np.zeros((48, 64, 3), dtype=np.uint8))
    writer.release()


@pytest.fixture
def prepared(tmp_path):
    (tmp_path / 'downloads').mkdir()
    (tmp_path / 'downloads/Segmentation.csv').write_text(
        HEADER + 'PM_001;1;1;1;2;9;front;0;right arm;1;0;0;1\n'
    )
    make_video(tmp_path / 'videos/Ex1/Camera17/PM_001.mp4')
    return tmp_path


def test_zip_cannot_write_outside_destination(tmp_path):
    archive = tmp_path / 'unsafe.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('../escape.txt', 'bad')
    with pytest.raises(ValueError, match='caminho'):
        safe_extract(archive, tmp_path / 'videos')
    assert not (tmp_path / 'escape.txt').exists()


def test_checksum_rejects_truncated_file(tmp_path):
    path = tmp_path / 'data'
    path.write_bytes(b'truncated')
    with pytest.raises(ValueError, match='checksum'):
        verify_file(path, 'md5:d41d8cd98f00b204e9800998ecf8427e')
    verify_file(path, 'md5:' + hashlib.md5(b'truncated').hexdigest())


def test_catalog_maps_camera_and_preserves_official_intervals(prepared):
    catalog = build_catalog(prepared)
    assert len(catalog['videos']) == 1
    video = catalog['videos'][0]
    assert video['camera'] == 17
    assert video['exercise_id'] == 1
    assert video['person_id'] == 1
    assert video['width'] == 64 and video['height'] == 48
    assert video['frame_count'] == 12
    assert video['repetitions'][0]['first_frame'] == 2
    assert video['repetitions'][0]['last_frame'] == 9
    assert video_path(prepared, video).is_file()
    assert len(video['id']) == 20


def test_catalog_rejects_annotation_outside_video(prepared):
    csv = prepared / 'downloads/Segmentation.csv'
    csv.write_text(csv.read_text().replace(';2;9;', ';2;99;'))
    with pytest.raises(ValueError, match='frames'):
        build_catalog(prepared)


def test_source_first_and_last_frame_can_cover_entire_video(prepared):
    csv = prepared / 'downloads/Segmentation.csv'
    csv.write_text(csv.read_text().replace(';2;9;', ';1;12;'))
    catalog = build_catalog(prepared)
    assert catalog['videos'][0]['repetitions'][0]['last_frame'] == 12


def test_catalog_rejects_wrong_fps(prepared):
    make_video(prepared / 'videos/Ex1/Camera17/PM_001.mp4', fps=25)
    with pytest.raises(ValueError, match='FPS'):
        build_catalog(prepared)


def test_catalog_rejects_ambiguous_camera(prepared):
    make_video(prepared / 'videos/Ex1/PM_001.mp4')
    with pytest.raises(ValueError, match='câmera'):
        build_catalog(prepared)


def test_video_resolution_rejects_escape(prepared):
    with pytest.raises(ValueError, match='caminho'):
        video_path(prepared, {'relative_path': '../secret.mp4'})


def test_catalog_rejects_duplicate_repetition(prepared):
    csv = prepared / 'downloads/Segmentation.csv'
    lines = csv.read_text().splitlines()
    csv.write_text('\n'.join(lines + [lines[1]]) + '\n')
    with pytest.raises(ValueError, match='duplicada'):
        build_catalog(prepared)
