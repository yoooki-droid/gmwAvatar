from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import BACKEND_DIR, settings


class Base(DeclarativeBase):
    pass


def _normalize_database_url(url: str) -> str:
    if not url.startswith('sqlite:///'):
        return url

    raw_path = url[len('sqlite:///') :]
    # sqlite 内存模式直接透传。
    if raw_path == ':memory:':
        return url

    path_obj = Path(raw_path)
    if path_obj.is_absolute():
        return url

    # 统一将相对路径固定到 backend 目录，避免不同启动目录导致连到不同库。
    abs_path = (BACKEND_DIR / path_obj).resolve()
    return f'sqlite:///{abs_path}'


DATABASE_URL = _normalize_database_url(settings.database_url)

connect_args = {'check_same_thread': False, 'timeout': 30} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA busy_timeout=30000;')
        cursor.close()


def ensure_schema_compatibility() -> None:
    inspector = inspect(engine)
    if 'meeting_reports' not in inspector.get_table_names():
        return

    columns = {col['name'] for col in inspector.get_columns('meeting_reports')}
    if 'auto_play_enabled' in columns:
        pass
    else:
        # 兼容已有数据库：补充自动播报开关字段，默认关闭。
        with engine.begin() as conn:
            if engine.dialect.name == 'mysql':
                conn.execute(text('ALTER TABLE meeting_reports ADD COLUMN auto_play_enabled TINYINT(1) NOT NULL DEFAULT 0'))
            else:
                conn.execute(text('ALTER TABLE meeting_reports ADD COLUMN auto_play_enabled BOOLEAN NOT NULL DEFAULT 0'))

    extra_report_columns = {
        'source_language': 'ALTER TABLE meeting_reports ADD COLUMN source_language VARCHAR(16) NOT NULL DEFAULT "zh"',
        'source_type': 'ALTER TABLE meeting_reports ADD COLUMN source_type VARCHAR(32) NOT NULL DEFAULT ""',
        'source_meeting_no': 'ALTER TABLE meeting_reports ADD COLUMN source_meeting_no VARCHAR(64) NOT NULL DEFAULT ""',
        'source_meeting_id': 'ALTER TABLE meeting_reports ADD COLUMN source_meeting_id VARCHAR(64) NOT NULL DEFAULT ""',
        'source_minute_token': 'ALTER TABLE meeting_reports ADD COLUMN source_minute_token VARCHAR(128) NOT NULL DEFAULT ""',
        'source_url': 'ALTER TABLE meeting_reports ADD COLUMN source_url TEXT',
    }
    for column_name, sql in extra_report_columns.items():
        if column_name in columns:
            continue
        with engine.begin() as conn:
            conn.execute(text(sql))
            if column_name == 'source_url':
                conn.execute(text('UPDATE meeting_reports SET source_url = "" WHERE source_url IS NULL'))

    if 'meeting_report_translations' in inspector.get_table_names():
        translation_columns = {col['name'] for col in inspector.get_columns('meeting_report_translations')}
        if 'audio_pcm_base64' not in translation_columns:
            with engine.begin() as conn:
                if engine.dialect.name == 'mysql':
                    conn.execute(text('ALTER TABLE meeting_report_translations ADD COLUMN audio_pcm_base64 LONGTEXT NOT NULL DEFAULT ""'))
                else:
                    conn.execute(text('ALTER TABLE meeting_report_translations ADD COLUMN audio_pcm_base64 TEXT NOT NULL DEFAULT ""'))
        if 'reviewed' not in translation_columns:
            with engine.begin() as conn:
                if engine.dialect.name == 'mysql':
                    conn.execute(text('ALTER TABLE meeting_report_translations ADD COLUMN reviewed TINYINT(1) NOT NULL DEFAULT 0'))
                else:
                    conn.execute(text('ALTER TABLE meeting_report_translations ADD COLUMN reviewed BOOLEAN NOT NULL DEFAULT 0'))
        if 'reviewed_at' not in translation_columns:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE meeting_report_translations ADD COLUMN reviewed_at DATETIME NULL'))
        if 'reflections_json' not in translation_columns:
            with engine.begin() as conn:
                conn.execute(text('ALTER TABLE meeting_report_translations ADD COLUMN reflections_json TEXT NOT NULL DEFAULT "[]"'))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
