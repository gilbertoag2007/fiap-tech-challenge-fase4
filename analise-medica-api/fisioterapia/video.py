"""Decode every frame, resizing before the expensive full-resolution RGB conversion."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import av


def prefetched_batches(iterable):
    """Overlap decoding with inference, holding at most one additional batch."""
    source=iter(iterable)
    def advance():
        try:
            return True,next(source)
        except StopIteration:
            return False,None
    try:
        with ThreadPoolExecutor(max_workers=1,thread_name_prefix='video-decode') as executor:
            future=executor.submit(advance)
            try:
                while True:
                    available,batch=future.result()
                    if not available:
                        break
                    future=executor.submit(advance)
                    yield batch
            finally:
                future.cancel()
    finally:
        # Executor has joined before closing a generator owned by its worker.
        close=getattr(source,'close',None)
        if close:
            close()


def video_batches(path: Path, batch_size: int, expected_size: tuple):
    if batch_size < 1:
        raise ValueError('Tamanho de lote inválido.')
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_count = 2
        if stream.average_rate is None or abs(float(stream.average_rate)-30) > .01:
            raise ValueError('FPS incompatível com as anotações de 30 FPS.')
        if (stream.width,stream.height) != expected_size:
            raise ValueError('A geometria decodificada não corresponde ao catálogo.')
        ratio = min(1.,640/max(expected_size))
        width,height = (max(1,round(value*ratio)) for value in expected_size)
        reformatter = av.video.reformatter.VideoReformatter()
        batch=[]
        first_time=None
        for index,frame in enumerate(container.decode(stream)):
            if frame.time is None:
                raise ValueError('Frame sem timestamp de apresentação.')
            if first_time is None:
                first_time=frame.time
            if abs((frame.time-first_time)-index/30) > 1/60:
                raise ValueError('Timeline variável incompatível com os índices oficiais.')
            image=reformatter.reformat(frame,width=width,height=height,format='bgr24',interpolation='BILINEAR').to_ndarray()
            batch.append(image)
            if len(batch)==batch_size:
                yield batch
                batch=[]
        if batch:
            yield batch
