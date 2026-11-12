import numpy as np
import pytest

from fisioterapia.features import angle, repetition_features


def pose_sequence(n=10):
    pose = np.zeros((n, 17, 3), dtype=float)
    pose[:, :, 2] = 1
    for i, xy in {5:(.4,.2),6:(.6,.2),7:(.25,.2),8:(.75,.2),9:(.1,.2),10:(.9,.2),11:(.4,.5),12:(.6,.5),13:(.4,.7),14:(.6,.7),15:(.4,.9),16:(.6,.9)}.items():
        pose[:, i, :2] = xy
    return pose


def test_angles_use_known_geometry_and_reject_degenerate_vectors():
    assert angle(np.array([0.,1]), np.array([0.,0]), np.array([1.,0])) == pytest.approx(90)
    assert angle(np.array([0.,0]), np.array([0.,0]), np.array([1.,0])) is None


@pytest.mark.parametrize('exercise', [1,2,3,4])
def test_each_exercise_produces_measures_without_labels(exercise):
    result = repetition_features(pose_sequence(), exercise, (1920,1080))
    assert result['coverage'] == 1
    assert result['reason'] is None
    assert all(np.isfinite(v) for v in result['features'].values())
    assert len(result['series']) == 10


def test_ex1_horizontal_arm_and_straight_elbow():
    result = repetition_features(pose_sequence(), 1, (1920,1080))
    assert result['features']['ombro_direito_mean'] == pytest.approx(90)
    assert result['features']['cotovelo_direito_mean'] == pytest.approx(180)


def test_geometry_uses_image_aspect_ratio():
    p = pose_sequence()
    p[:,8,:2] = (.7,.3)
    # In a 2:1 image this vector is (0.2,0.1), not (0.1,0.1).
    result = repetition_features(p, 1, (2,1))
    assert result['features']['ombro_direito_mean'] == pytest.approx(63.4349488)


def test_measurements_are_translation_and_uniform_scale_invariant():
    a = pose_sequence()
    b = a.copy()
    b[:,:,:2] = b[:,:,:2] * .5 + .1
    original = repetition_features(a, 4)
    scaled = repetition_features(b, 4)
    assert original['features'] == pytest.approx(scaled['features'])


def test_low_confidence_is_not_interpreted_as_correct_posture():
    pose = pose_sequence()
    pose[:,8,2] = .49
    result = repetition_features(pose, 1)
    assert result['coverage'] == 0
    assert result['reason']
    assert result['features'] is None
    assert all(row['ombro_direito'] is None for row in result['series'])


def test_exactly_sixty_percent_coverage_is_accepted():
    pose = pose_sequence()
    pose[:4,8,2] = 0
    assert repetition_features(pose, 1)['reason'] is None
    pose[4,8,2] = 0
    assert repetition_features(pose, 1)['features'] is None


def test_missing_person_and_nonfinite_points_are_rejected():
    assert repetition_features(np.zeros((0,17,3)), 1)['features'] is None
    pose = pose_sequence()
    pose[:,8,0] = np.nan
    assert repetition_features(pose, 1)['features'] is None
