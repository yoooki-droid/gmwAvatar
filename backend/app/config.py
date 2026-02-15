from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = (BACKEND_DIR / 'gmwavatar.db').resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = 'gmwAvatar Backend'
    app_env: str = 'dev'
    app_host: str = '0.0.0.0'
    app_port: int = 8000

    database_url: str = f'sqlite:///{DEFAULT_SQLITE_PATH}'

    cors_allow_origins: str = '*'

    timezone: str = 'Asia/Shanghai'

    azure_endpoint_url: str | None = None
    azure_base_url: str | None = None
    azure_deployment_name: str = 'gpt-5.2-chat'
    azure_deployment_fallbacks: str = 'gpt-4o'
    azure_openai_api_key: str | None = None
    azure_api_version: str = '2025-01-01-preview'
    azure_tts_deployment_name: str | None = None
    azure_tts_default_voice: str = 'alloy'
    azure_request_timeout_sec: int = 45
    azure_request_retry_count: int = 3
    azure_request_retry_backoff_sec: float = 1.2
    azure_speech_key: str | None = None
    azure_speech_key_secondary: str | None = None
    azure_speech_region: str | None = None
    azure_speech_endpoint: str | None = None
    azure_speech_tts_path: str = '/tts/cognitiveservices/v1'
    azure_speech_output_format: str = 'raw-16khz-16bit-mono-pcm'
    azure_ssl_skip_verify: bool = False

    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_api_base: str = 'https://open.feishu.cn'
    feishu_timeout_sec: int = 20
    feishu_verify_ssl: bool = True

    baidu_avatar_token: str | None = None
    baidu_figure_id: str | None = None
    baidu_camera_id: str | None = None
    baidu_resolution_width: int = 1920
    baidu_resolution_height: int = 1080


settings = Settings()
