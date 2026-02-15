from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.avatar import router as avatar_router
from .api.playback import router as playback_router
from .api.reports import router as reports_router
from .config import settings
from .database import Base, engine, ensure_schema_compatibility


Base.metadata.create_all(bind=engine)
ensure_schema_compatibility()

app = FastAPI(title=settings.app_name)

origins = [x.strip() for x in settings.cors_allow_origins.split(',') if x.strip()]
if not origins:
    origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/healthz')
def healthz():
    return {'ok': True}


@app.get('/readyz')
def readyz():
    return {'ok': True}


app.include_router(reports_router)
app.include_router(avatar_router)
app.include_router(playback_router)
