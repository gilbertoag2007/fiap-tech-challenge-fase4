import numpy as np

from fisioterapia.pose import PersonTracker, pose_identity


def test_tracker_keeps_identity_when_larger_person_enters():
    tracker = PersonTracker()
    assert tracker.select(np.array([[0,0,100,200]])) == 0
    assert tracker.select(np.array([[5,0,105,200],[200,0,400,400]])) == 0


def test_tracker_rejects_ambiguous_initial_choice():
    tracker = PersonTracker()
    assert tracker.select(np.array([[0,0,100,200],[150,0,250,200]])) is None


def test_tracker_does_not_jump_to_different_person_after_occlusion():
    tracker = PersonTracker()
    tracker.select(np.array([[0,0,100,200]]))
    assert tracker.select(np.empty((0,4))) is None
    assert tracker.select(np.array([[500,500,600,700]])) is None


def test_pose_cache_depends_on_video_weights_and_config():
    base = pose_identity('video-a', 'weights-a')
    assert base != pose_identity('video-b', 'weights-a')
    assert base != pose_identity('video-a', 'weights-b')
    assert base != pose_identity('video-a', 'weights-a', device='mps', batch=8)


def test_tracker_rejects_overlapping_replacement_after_long_occlusion():
    tracker = PersonTracker()
    assert tracker.select(np.array([[0,0,100,200]])) == 0
    for _ in range(16):
        assert tracker.select(np.empty((0,4))) is None
    assert tracker.select(np.array([[5,0,105,200]])) is None
