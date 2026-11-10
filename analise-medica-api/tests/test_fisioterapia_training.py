import copy

import pytest

from fisioterapia.training import grouped_folds, train_records, predict_rows, source_identity, repetition_rows
from fisioterapia.config import digest


def records():
    return [dict(video_id=f'p{person}-c{camera}', person_id=person, camera=camera,
                 exercise_id=exercise, repetition_number=label+1, expected=label,
                 features={'movement': float(label*10), 'optional': None}, coverage=1., reason=None)
            for exercise in (1,2,3,4) for person in range(1,11) for camera in (17,18) for label in (0,1)]


def test_grouped_folds_never_share_a_person_or_camera_between_splits():
    rows = records()
    for train, test in grouped_folds(rows):
        train_people = {rows[i]['person_id'] for i in train}
        test_people = {rows[i]['person_id'] for i in test}
        assert train_people.isdisjoint(test_people)
        for person in test_people:
            assert {rows[i]['camera'] for i in test if rows[i]['person_id']==person} == {17,18}


def test_insufficient_participants_is_an_explicit_error():
    with pytest.raises(ValueError, match='participantes'):
        list(grouped_folds(records()[:4]))


def test_training_and_prediction_do_not_need_expected_label(tmp_path):
    rows = records()
    manifest = train_records(tmp_path, rows, 'source-a')
    test = copy.deepcopy(rows[0])
    del test['expected']
    result = predict_rows(tmp_path, [test], manifest)[0]
    assert result['status'] == 'Incorreto'
    assert test['person_id'] not in result['training_participants']
    metrics = manifest['exercises']['1']['metrics']
    assert metrics['balanced_accuracy'] == 1.
    assert metrics['recall_incorrect'] == 1.
    assert metrics['coverage'] == 1.
    assert metrics['confusion_matrix'] == [[20,0],[0,20]]


def test_invalid_pose_is_nonconclusive_not_a_default_class(tmp_path):
    rows = records()
    manifest = train_records(tmp_path, rows, 'source-a')
    invalid = dict(rows[0], features=None, coverage=.1, reason='Sem postura')
    result = predict_rows(tmp_path, [invalid], manifest)[0]
    assert result['status'] == 'Não conclusivo'
    assert result['prediction'] is None


def test_training_rejects_single_class(tmp_path):
    rows = [r for r in records() if r['expected']==1]
    with pytest.raises(ValueError, match='classes'):
        train_records(tmp_path, rows, 'source-a')


def test_training_identity_changes_when_source_changes(tmp_path):
    first = train_records(tmp_path, records(), 'source-a')
    second = train_records(tmp_path, records(), 'source-b')
    assert first['identity'] != second['identity']


def test_unknown_participant_is_not_silently_evaluated_in_sample(tmp_path):
    rows = records()
    manifest = train_records(tmp_path, rows, 'source-a')
    with pytest.raises(ValueError, match='participante'):
        predict_rows(tmp_path, [dict(rows[0],person_id=999)], manifest)


def test_participant_with_no_valid_pose_still_has_held_out_group(tmp_path):
    rows = records()
    for row in rows:
        if row['person_id']==10:
            row.update(features=None,coverage=0.,reason='Sem postura')
    manifest = train_records(tmp_path,rows,'no-pose-person')
    for exercise in ('1','2','3','4'):
        folds = manifest['exercises'][exercise]['folds']
        assert any(10 in fold['test_participants'] for fold in folds)
        assert manifest['exercises'][exercise]['metrics']['nonconclusive'] == 4
        assert manifest['exercises'][exercise]['metrics']['nonconclusive_by_label'] == {'0':2,'1':2}
        assert manifest['exercises'][exercise]['metrics']['recall_incorrect_all'] == .9


def test_estimator_version_change_invalidates_training_source(tmp_path,monkeypatch):
    import ultralytics
    (tmp_path/'downloads').mkdir()
    (tmp_path/'downloads/Segmentation.csv').write_text('annotations')
    (tmp_path/'models').mkdir()
    (tmp_path/'models/yolov8n-pose.pt').write_bytes(b'weights-test')
    catalog = {'videos':[],'annotation_sha256':digest(tmp_path/'downloads/Segmentation.csv')}
    original = source_identity(tmp_path,catalog)
    monkeypatch.setattr(ultralytics,'__version__','test-new-version')
    assert source_identity(tmp_path,catalog) != original


def test_source_one_based_frames_map_to_video_start_and_inclusive_end():
    import numpy as np
    video = {'id':'x','exercise_id':1,'person_id':1,'camera':17,'width':64,'height':48,'fps':30,
             'repetitions':[{'first_frame':1,'last_frame':12,'repetition_number':1}]}
    rows = repetition_rows(video,{'points':np.zeros((12,17,3))})
    assert len(rows[0]['series']) == 12
    assert rows[0]['start_seconds'] == 0
    assert rows[0]['end_seconds'] == .4
    assert rows[0]['first_frame_index'] == 0
