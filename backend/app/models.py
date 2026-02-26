from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils.timezone import now_local_naive


class MeetingReport(Base):
    __tablename__ = "meeting_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    meeting_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    speaker: Mapped[str] = mapped_column(String(120), nullable=False)
    summary_raw: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(
        String(16), default="zh", nullable=False
    )
    script_draft: Mapped[str] = mapped_column(Text, default="", nullable=False)
    script_final: Mapped[str] = mapped_column(Text, default="", nullable=False)
    question_persona: Mapped[str] = mapped_column(
        String(32), default="board_director", nullable=False
    )
    auto_play_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    source_meeting_no: Mapped[str] = mapped_column(
        String(64), default="", nullable=False
    )
    source_meeting_id: Mapped[str] = mapped_column(
        String(64), default="", nullable=False
    )
    source_minute_token: Mapped[str] = mapped_column(
        String(128), default="", nullable=False
    )
    source_url: Mapped[str] = mapped_column(Text, default="", nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_local_naive, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_local_naive, onupdate=now_local_naive, nullable=False
    )

    highlights: Mapped[list["MeetingReportHighlight"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", passive_deletes=True
    )
    reflections: Mapped[list["MeetingReportReflection"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", passive_deletes=True
    )
    questions: Mapped[list["MeetingReportQuestion"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", passive_deletes=True
    )
    translations: Mapped[list["MeetingReportTranslation"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", passive_deletes=True
    )


class MeetingReportHighlight(Base):
    __tablename__ = "meeting_report_highlights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_reports.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    highlight_text: Mapped[str] = mapped_column(String(500), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped["MeetingReport"] = relationship(back_populates="highlights")


class MeetingReportReflection(Base):
    __tablename__ = "meeting_report_reflections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_reports.id", ondelete="CASCADE"), index=True
    )
    reflection_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped["MeetingReport"] = relationship(back_populates="reflections")


class MeetingReportQuestion(Base):
    __tablename__ = "meeting_report_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_reports.id", ondelete="CASCADE"), index=True
    )
    question_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    persona_key: Mapped[str] = mapped_column(
        String(32), default="board_director", nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped["MeetingReport"] = relationship(back_populates="questions")


class MeetingReportReflectionAudio(Base):
    """每条反思 × 每种语言的预合成 TTS 音频缓存。

    唯一约束 (report_id, seq, language_key)，text_hash 用于检测文字是否变动，
    变动时后台任务重新合成并覆盖本行。
    """

    __tablename__ = "meeting_report_reflection_audios"
    __table_args__ = (
        UniqueConstraint(
            "report_id", "seq", "language_key", name="uq_reflection_audio"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_reports.id", ondelete="CASCADE"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    language_key: Mapped[str] = mapped_column(String(16), nullable=False)
    # SHA-256 of the source text used for synthesis (to detect stale cache)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    audio_pcm_base64: Mapped[str] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"), default="", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_local_naive, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_local_naive, onupdate=now_local_naive, nullable=False
    )


class MeetingReportTranslation(Base):
    __tablename__ = "meeting_report_translations"
    __table_args__ = (
        UniqueConstraint("report_id", "language_key", name="uq_report_language"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("meeting_reports.id", ondelete="CASCADE"), index=True
    )
    language_key: Mapped[str] = mapped_column(String(16), nullable=False)
    title_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    script_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    highlights_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    reflections_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    questions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    question_persona: Mapped[str] = mapped_column(
        String(32), default="board_director", nullable=False
    )
    # 预生成的 16k PCM(base64)，用于非中英文音频驱动播报。
    audio_pcm_base64: Mapped[str] = mapped_column(
        Text().with_variant(LONGTEXT, "mysql"), default="", nullable=False
    )
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_local_naive, onupdate=now_local_naive, nullable=False
    )

    report: Mapped["MeetingReport"] = relationship(back_populates="translations")


class AvatarConfig(Base):
    __tablename__ = "avatar_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    figure_id: Mapped[str] = mapped_column(String(64), nullable=False)
    camera_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_width: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    resolution_height: Mapped[int] = mapped_column(
        Integer, default=1920, nullable=False
    )
    tts_per: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tts_lan: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class PlaybackRuntimeSetting(Base):
    __tablename__ = "playback_runtime_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mode: Mapped[str] = mapped_column(
        String(32), default="carousel_summary", nullable=False
    )
    carousel_scope: Mapped[str] = mapped_column(
        String(16), default="loop", nullable=False
    )
    selected_report_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_local_naive, onupdate=now_local_naive, nullable=False
    )
