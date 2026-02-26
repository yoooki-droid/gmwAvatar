from datetime import datetime

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    title: str
    meeting_time: datetime | None = None
    speaker: str = ""
    summary_raw: str
    source_language: str | None = None
    script_final: str = ""
    highlights_final: list[str] = Field(default_factory=list)
    reflections_final: list[str] = Field(default_factory=list)
    questions_final: list[str] = Field(default_factory=list)
    question_persona: str = "board_director"
    auto_play_enabled: bool = False


class ReportUpdate(BaseModel):
    title: str | None = None
    meeting_time: datetime | None = None
    speaker: str | None = None
    summary_raw: str | None = None
    source_language: str | None = None
    script_final: str | None = None
    highlights_final: list[str] | None = None
    reflections_final: list[str] | None = None
    questions_final: list[str] | None = None
    question_persona: str | None = None
    auto_play_enabled: bool | None = None


class ReportListItem(BaseModel):
    id: int
    title: str
    speaker: str
    source_language: str
    meeting_time: datetime
    status: str
    auto_play_enabled: bool


class ReportListResponse(BaseModel):
    items: list[ReportListItem]
    total: int
    page: int
    page_size: int


class ReportDetail(BaseModel):
    id: int
    title: str
    meeting_time: datetime
    speaker: str
    source_language: str
    summary_raw: str
    script_draft: str
    script_final: str
    highlights_draft: list[str]
    highlights_final: list[str]
    reflections_final: list[str]
    questions_final: list[str]
    question_persona: str
    auto_play_enabled: bool
    status: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GenerateResponse(BaseModel):
    report_id: int
    script_draft: str
    highlights_draft: list[str]
    reflections_draft: list[str]
    questions_draft: list[str]


class GeneratePreviewRequest(BaseModel):
    title: str
    speaker: str = ""
    summary_raw: str
    question_persona: str = "board_director"


class GeneratePreviewResponse(BaseModel):
    script_draft: str
    highlights_draft: list[str]
    reflections_draft: list[str]
    questions_draft: list[str]


class TranslateScriptRequest(BaseModel):
    script_text: str
    target_language: str


class TranslateScriptResponse(BaseModel):
    translated_text: str


class SynthesizeAudioRequest(BaseModel):
    script_text: str
    language_key: str


class SynthesizeAudioResponse(BaseModel):
    language_key: str
    audio_pcm_base64: str


class PublishResponse(BaseModel):
    report_id: int
    status: str
    published_at: datetime


class ImportResponse(BaseModel):
    success_count: int
    failed_count: int
    errors: list[str]


class SourceImportRequest(BaseModel):
    source_type: str
    source_url: str
    auth_config: dict = Field(default_factory=dict)
    mapping: dict = Field(default_factory=dict)


class SourceImportResponse(BaseModel):
    task_id: str
    accepted_count: int
    message: str


class FeishuMeetingImportRequest(BaseModel):
    meeting_url: str
    lookback_days: int = Field(default=30, ge=1, le=180)
    auto_generate: bool = True
    auto_enable_playback: bool = False


class FeishuMeetingImportItem(BaseModel):
    meeting_no: str
    meeting_id: str
    minute_token: str
    minute_url: str
    title: str
    report_id: int | None
    transcript_status: str
    note: str


class FeishuMeetingImportResponse(BaseModel):
    imported_count: int
    updated_count: int
    failed_count: int
    items: list[FeishuMeetingImportItem]
    message: str


class FeishuDocxImportRequest(BaseModel):
    """飞书文档导入请求"""

    docx_url: str
    auto_generate: bool = True
    auto_enable_playback: bool = False


class FeishuDocxImportResponse(BaseModel):
    """飞书文档导入响应"""

    success: bool
    report_id: int | None
    title: str
    content_length: int
    message: str
    error: str | None = None


class FeishuDocxInspectRequest(BaseModel):
    docx_url: str


class FeishuDocxInspectResponse(BaseModel):
    ok: bool
    document_id: str
    title: str
    content_length: int
    message: str
    error: str | None = None


class FeishuDocxDiagnoseRequest(BaseModel):
    docx_url: str


class FeishuDocxDiagnoseStep(BaseModel):
    step: str
    ok: bool
    detail: str
    data: dict = Field(default_factory=dict)


class FeishuDocxDiagnoseResponse(BaseModel):
    ok: bool
    document_id: str
    steps: list[FeishuDocxDiagnoseStep]
    suggestion: str


class FeishuMeetingInspectRequest(BaseModel):
    meeting_url: str
    lookback_days: int = Field(default=30, ge=1, le=180)


class FeishuMeetingInspectItem(BaseModel):
    meeting_no: str
    meeting_id: str
    topic: str
    start_time: datetime | None
    end_time: datetime | None
    minute_token: str
    minute_url: str
    minute_title: str
    minute_owner_id: str
    minute_summary_formal: str
    minute_summary_draft: str
    transcript_status: str
    transcript_error: str
    transcript_text: str


class FeishuMeetingInspectResponse(BaseModel):
    total: int
    items: list[FeishuMeetingInspectItem]
    message: str


class FeishuMeetingDiagnoseRequest(BaseModel):
    meeting_url: str
    lookback_days: int = Field(default=30, ge=1, le=180)


class FeishuMeetingDiagnoseStep(BaseModel):
    step: str
    ok: bool
    detail: str
    data: dict = Field(default_factory=dict)


class FeishuMeetingDiagnoseResponse(BaseModel):
    ok: bool
    meeting_no: str
    steps: list[FeishuMeetingDiagnoseStep]
    suggestion: str


class AvatarTokenResponse(BaseModel):
    token: str
    figure_id: str
    camera_id: str | None = None
    resolution_width: int
    resolution_height: int


class PlaybackQueueItem(BaseModel):
    id: int
    title: str
    speaker: str
    meeting_time: datetime
    script_final: str
    highlights_final: list[str]
    reflections_final: list[str]
    questions_final: list[str]
    question_persona: str
    localized: dict[str, dict] = Field(default_factory=dict)


class PlaybackQueueResponse(BaseModel):
    items: list[PlaybackQueueItem]
    total: int


class TranslationItem(BaseModel):
    language_key: str
    status: str
    error: str = ""
    reviewed: bool
    reviewed_at: datetime | None
    title: str
    script_final: str
    highlights_final: list[str]
    reflections_final: list[str]
    questions_final: list[str]
    question_persona: str
    render_mode: str
    audio_ready: bool


class ReportTranslationsResponse(BaseModel):
    report_id: int
    items: list[TranslationItem]


class TranslationUpdateRequest(BaseModel):
    title: str | None = None
    script_final: str | None = None
    highlights_final: list[str] | None = None
    reflections_final: list[str] | None = None
    questions_final: list[str] | None = None
    question_persona: str | None = None
    reviewed: bool | None = None


class TranslationPrepareResponse(BaseModel):
    report_id: int
    language_key: str
    status: str
    reviewed: bool
    reviewed_at: datetime | None
    title: str
    script_final: str
    highlights_final: list[str]
    reflections_final: list[str]
    questions_final: list[str]
    question_persona: str
    render_mode: str
    audio_ready: bool


class TranslationJobTriggerResponse(BaseModel):
    task_id: str
    report_id: int
    languages: list[str]
    status: str


class TranslationJobStatusItem(BaseModel):
    language_key: str
    status: str
    error: str = ""
    updated_at: datetime | None = None


class TranslationJobStatusResponse(BaseModel):
    report_id: int
    items: list[TranslationJobStatusItem]


class PlaybackModeResponse(BaseModel):
    mode: str
    carousel_scope: str
    selected_report_id: int | None
    updated_at: datetime


class PlaybackModeUpdateRequest(BaseModel):
    mode: str
    carousel_scope: str = "loop"
    selected_report_id: int | None = None


class FeishuLiveRecordItem(BaseModel):
    timestamp: datetime
    speaker: str
    content: str


class FeishuLiveRecordsResponse(BaseModel):
    source: str
    records: list[FeishuLiveRecordItem]


class ReflectionItem(BaseModel):
    text: str
    # 预合成音频（zh 版本），前端可直接播放，None 表示尚未合成
    audio_pcm_base64: str | None = None


class ReflectionAudioItem(BaseModel):
    """单条反思的某语言预合成音频，供前端异步补全其他语言时使用。"""

    seq: int
    language_key: str
    audio_pcm_base64: str


class ReflectionResponse(BaseModel):
    report_id: int
    reflections: list[ReflectionItem]


class QuestionItem(BaseModel):
    text: str


class QuestionResponse(BaseModel):
    report_id: int
    persona: str
    questions: list[QuestionItem]
