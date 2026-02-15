import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import MeetingReport, PlaybackRuntimeSetting
from ..schemas import FeishuLiveRecordItem, FeishuLiveRecordsResponse, PlaybackModeResponse, PlaybackModeUpdateRequest
from ..utils.timezone import now_local_naive

router = APIRouter(prefix='/api/playback', tags=['playback'])

ALLOWED_MODES = {'realtime_summary', 'carousel_summary', 'reflection_qa'}
ALLOWED_CAROUSEL_SCOPES = {'single', 'loop'}


def _split_summary_lines(text: str) -> list[str]:
    if not text.strip():
        return []
    parts = re.split(r'[\n。！？!?]+', text)
    return [p.strip() for p in parts if p.strip()]


def _extract_section_block(text: str, section_title: str) -> str:
    if not text.strip():
        return ''
    marker = f'【{section_title}】'
    idx = text.find(marker)
    if idx < 0:
        return ''
    block = text[idx + len(marker):]
    next_idx = block.find('【')
    if next_idx >= 0:
        block = block[:next_idx]
    return block.strip()


def _extract_formal_lines_from_summary_raw(summary_raw: str, limit: int) -> list[str]:
    def _normalize_lines(block_text: str) -> list[str]:
        lines = [x.strip() for x in re.split(r'[\n。！？!?]+', block_text) if x.strip()]
        merged: list[str] = []
        seen: set[str] = set()
        for line in lines:
            normalized = re.sub(r'\s+', ' ', line).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
            if len(merged) >= limit:
                break
        return merged

    # 优先：飞书正式章节；回退：AI 章节纪要。
    block = _extract_section_block(summary_raw, '会议章节总结（正式）')
    if block:
        normalized = _normalize_lines(block)
        if normalized:
            return normalized

    ai_block = _extract_section_block(summary_raw, 'AI章节纪要')
    if ai_block:
        normalized = _normalize_lines(ai_block)
        if normalized:
            return normalized

    return []


def _extract_live_fallback_lines(summary_raw: str, limit: int) -> list[str]:
    if not summary_raw.strip():
        return []

    # 仅展示章节总结相关区块，避免展示会议号/实例ID/妙记链接等元信息。
    for section in ['会议章节总结（正式）', '会议实时草稿']:
        block = _extract_section_block(summary_raw, section)
        if not block:
            continue
        lines = [x.strip() for x in re.split(r'[\n。！？!?]+', block) if x.strip()]
        cleaned: list[str] = []
        seen: set[str] = set()
        for line in lines:
            normalized = re.sub(r'\s+', ' ', line).strip()
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(normalized)
            if len(cleaned) >= limit:
                break
        if cleaned:
            return cleaned

    # 没有章节总结内容时返回空列表，由前端按“无内容”处理。
    return []


def _build_live_summary_lines(report: MeetingReport, limit: int) -> list[str]:
    if (report.source_type or '').strip() == 'feishu_meeting':
        raw_lines = _extract_formal_lines_from_summary_raw(report.summary_raw, limit=limit)
        if not raw_lines:
            raw_lines = _extract_live_fallback_lines(report.summary_raw, limit=limit)
        return raw_lines[:limit]

    lines: list[str] = []

    final_highlights = sorted([h for h in report.highlights if h.kind == 'final'], key=lambda x: x.seq)
    for row in final_highlights:
        text = (row.highlight_text or '').strip()
        if text:
            lines.append(text)

    script = (report.script_final or report.script_draft or '').strip()
    if script:
        paragraphs = [p.strip() for p in re.split(r'[\n\r]+', script) if p.strip()]
        if not paragraphs:
            paragraphs = [script]
        for p in paragraphs:
            if p:
                lines.append(p)

    if not lines:
        raw_lines = _extract_formal_lines_from_summary_raw(report.summary_raw, limit=limit)
        if not raw_lines:
            raw_lines = _extract_live_fallback_lines(report.summary_raw, limit=limit)
        lines.extend(raw_lines)

    # 去重并裁剪，保持顺序稳定。
    merged: list[str] = []
    seen: set[str] = set()
    for line in lines:
        normalized = re.sub(r'\s+', ' ', line).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
        if len(merged) >= limit:
            break
    return merged


def _get_or_create_runtime_setting(db: Session) -> PlaybackRuntimeSetting:
    row = db.query(PlaybackRuntimeSetting).order_by(PlaybackRuntimeSetting.id.asc()).first()
    if row:
        return row

    row = PlaybackRuntimeSetting(
        mode='carousel_summary',
        carousel_scope='loop',
        selected_report_id=None,
        updated_at=now_local_naive(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _to_mode_response(row: PlaybackRuntimeSetting) -> PlaybackModeResponse:
    return PlaybackModeResponse(
        mode=row.mode,
        carousel_scope=row.carousel_scope,
        selected_report_id=row.selected_report_id,
        updated_at=row.updated_at,
    )


@router.get('/mode', response_model=PlaybackModeResponse)
def get_playback_mode(db: Session = Depends(get_db)):
    row = _get_or_create_runtime_setting(db)
    return _to_mode_response(row)


@router.put('/mode', response_model=PlaybackModeResponse)
def update_playback_mode(payload: PlaybackModeUpdateRequest, db: Session = Depends(get_db)):
    mode = payload.mode.strip()
    if mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail='mode 不支持')

    carousel_scope = payload.carousel_scope.strip() if payload.carousel_scope else 'loop'
    if carousel_scope not in ALLOWED_CAROUSEL_SCOPES:
        raise HTTPException(status_code=400, detail='carousel_scope 不支持')

    if payload.selected_report_id is not None:
        report = db.get(MeetingReport, payload.selected_report_id)
        if report is None:
            raise HTTPException(status_code=400, detail='selected_report_id 对应新闻不存在')

    row = _get_or_create_runtime_setting(db)
    row.mode = mode
    row.carousel_scope = carousel_scope
    row.selected_report_id = payload.selected_report_id
    row.updated_at = now_local_naive()

    db.commit()
    db.refresh(row)
    return _to_mode_response(row)


@router.get('/live-records', response_model=FeishuLiveRecordsResponse)
def get_live_records(
    limit: int = Query(12, ge=1, le=100),
    report_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    report = None
    if report_id is not None:
        report = db.get(MeetingReport, report_id)
    if report is None:
        runtime = _get_or_create_runtime_setting(db)
        if runtime.selected_report_id:
            report = db.get(MeetingReport, runtime.selected_report_id)
    if report is None:
        report = db.query(MeetingReport).order_by(MeetingReport.updated_at.desc(), MeetingReport.id.desc()).first()
    if report is None:
        return FeishuLiveRecordsResponse(source='feishu_pending', records=[])

    lines = _build_live_summary_lines(report, limit=limit)

    now = now_local_naive()
    records: list[FeishuLiveRecordItem] = []
    for idx, line in enumerate(lines):
        records.append(
            FeishuLiveRecordItem(
                timestamp=now - timedelta(seconds=(len(lines) - idx) * 25),
                speaker=(report.speaker or '会议记录').strip() or '会议记录',
                content=line,
            )
        )

    return FeishuLiveRecordsResponse(
        source='feishu_placeholder',
        records=records,
    )
