import cv2
import numpy as np
import pytest

from fisioterapia.video import video_batches, prefetched_batches
import threading


def write_video(path,width=64,height=48,fps=30):
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),fps,(width,height))
    for i in range(12):
        writer.write(np.full((height,width,3),i*15,dtype=np.uint8))
    writer.release()


def test_decoder_preserves_every_frame_and_presentation_order(tmp_path):
    path=tmp_path/'video.mp4';write_video(path)
    batches=list(video_batches(path,batch_size=5,expected_size=(64,48)))
    assert [len(batch) for batch in batches] == [5,5,2]
    frames=[image for batch in batches for image in batch]
    assert len(frames)==12
    assert frames[0].shape==(48,64,3)
    assert frames[0].mean()<frames[-1].mean()


def test_decoder_scales_portrait_before_rgb_conversion(tmp_path):
    path=tmp_path/'portrait.mp4';write_video(path,width=720,height=1280)
    images=next(video_batches(path,batch_size=2,expected_size=(720,1280)))
    assert images[0].shape==(640,360,3)


def test_decoder_rejects_fps_and_geometry_mismatch(tmp_path):
    path=tmp_path/'video.mp4';write_video(path,fps=25)
    with pytest.raises(ValueError,match='FPS'):
        next(video_batches(path,batch_size=2,expected_size=(64,48)))
    write_video(path)
    with pytest.raises(ValueError,match='geometria'):
        next(video_batches(path,batch_size=2,expected_size=(48,64)))


def test_prefetch_reads_next_batch_while_consumer_processes_current_batch():
    ready=threading.Event()
    def source():
        yield [0]
        ready.set()
        yield [1]
        yield [2]
    batches=prefetched_batches(source())
    assert next(batches)==[0]
    assert ready.wait(2),'Próximo lote deve ser lido antes do consumidor pedir outro.'
    assert list(batches)==[[1],[2]]


def test_prefetch_preserves_decode_error_and_closes_source():
    closed=threading.Event()
    def source():
        try:
            yield [0]
            raise ValueError('frame corrompido')
        finally:
            closed.set()
    batches=prefetched_batches(source())
    assert next(batches)==[0]
    with pytest.raises(ValueError,match='corrompido'):
        next(batches)
    assert closed.is_set()


def test_prefetch_closes_decoder_if_consumer_stops_early():
    closed=threading.Event()
    def source():
        try:
            for n in range(100):yield [n]
        finally:
            closed.set()
    batches=prefetched_batches(source())
    assert next(batches)==[0]
    batches.close()
    assert closed.is_set()
