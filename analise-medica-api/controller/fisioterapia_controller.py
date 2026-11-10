from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from fisioterapia.dataset import video_path

roteador = APIRouter(prefix='/v1/fisioterapia',tags=['Fisioterapia'])


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    video_id: str = Field(pattern=r'^[a-f0-9]{20}$')


def _call(operation):
    try:
        return operation()
    except LookupError as error:
        raise HTTPException(404,str(error)) from error
    except RuntimeError as error:
        raise HTTPException(409,str(error)) from error
    except (ValueError, OSError) as error:
        raise HTTPException(503,str(error)) from error
    except ImportError as error:
        raise HTTPException(503,'Dependências de vídeo ausentes. Instale requirements-video.txt.') from error


@roteador.get('/catalogo')
def catalog(request: Request):
    return _call(lambda:request.app.state.fisioterapia.catalog())


@roteador.get('/videos/{video_id}')
def video(video_id: str, request: Request):
    service = request.app.state.fisioterapia
    return _call(lambda:FileResponse(video_path(service.root,service.video(video_id)),media_type='video/mp4'))


@roteador.post('/analises',status_code=202)
def create(body: AnalysisRequest, request: Request):
    return _call(lambda:request.app.state.fisioterapia.create(body.video_id))


@roteador.get('/analises/{job_id}')
def get(job_id: str, request: Request):
    return _call(lambda:request.app.state.fisioterapia.get(job_id))


@roteador.get('/analises/{job_id}/relatorio')
def report(job_id: str, request: Request):
    return _call(lambda:FileResponse(request.app.state.fisioterapia.report_path(job_id),
                                    media_type='application/json',filename=f'fisioterapia-{job_id}.json'))


@roteador.get('/analises/{job_id}/pose')
def pose(job_id: str, request: Request):
    return _call(lambda:request.app.state.fisioterapia.pose(job_id))
