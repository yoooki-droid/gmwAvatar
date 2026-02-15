from fastapi import APIRouter, HTTPException

from ..config import settings
from ..schemas import AvatarTokenResponse

router = APIRouter(prefix='/api/avatar', tags=['avatar'])


@router.post('/token', response_model=AvatarTokenResponse)
def get_avatar_token():
    if not settings.baidu_avatar_token or not settings.baidu_figure_id:
        raise HTTPException(status_code=400, detail='请先在后端环境变量配置百度数字人 token 和 figure_id')

    return AvatarTokenResponse(
        token=settings.baidu_avatar_token,
        figure_id=settings.baidu_figure_id,
        camera_id=settings.baidu_camera_id,
        resolution_width=settings.baidu_resolution_width,
        resolution_height=settings.baidu_resolution_height,
    )
