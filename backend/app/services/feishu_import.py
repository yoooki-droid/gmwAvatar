import json
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


@dataclass
class FeishuMeetingImportItem:
    meeting_no: str
    meeting_id: str
    topic: str
    start_time: datetime | None
    end_time: datetime | None
    minute_url: str
    minute_token: str
    minute_title: str
    minute_owner_id: str
    minute_summary_formal: str
    minute_summary_draft: str
    transcript_text: str
    transcript_status: str
    transcript_error: str


class FeishuApiClient:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        api_base: str = 'https://open.feishu.cn',
        timeout_sec: int = 20,
        verify_ssl: bool = True,
    ) -> None:
        self.app_id = (app_id or '').strip()
        self.app_secret = (app_secret or '').strip()
        self.api_base = (api_base or 'https://open.feishu.cn').rstrip('/')
        self.timeout_sec = max(5, int(timeout_sec))
        self.verify_ssl = bool(verify_ssl)

        if not self.app_id or not self.app_secret:
            raise ValueError('飞书 APP_ID 或 APP_SECRET 未配置')

        self._tenant_access_token = ''

    def _ssl_context(self):
        if self.verify_ssl:
            return None
        return ssl._create_unverified_context()  # noqa: SLF001

    def _http_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        url = f'{self.api_base}{path}'
        if query:
            encoded = urlencode(query)
            url = f'{url}?{encoded}'

        request_headers = dict(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode('utf-8')
            request_headers.setdefault('Content-Type', 'application/json; charset=utf-8')

        req = Request(url=url, data=data, headers=request_headers, method=method.upper())
        context = self._ssl_context()

        try:
            with urlopen(req, timeout=self.timeout_sec, context=context) as resp:
                raw = resp.read()
                status = resp.getcode()
                resp_headers = {k.lower(): v for k, v in resp.headers.items()}
                return status, resp_headers, raw
        except HTTPError as err:
            raw = err.read()
            status = err.code
            resp_headers = {k.lower(): v for k, v in err.headers.items()}
            return status, resp_headers, raw
        except URLError as err:
            raise RuntimeError(f'飞书接口网络异常: {err}') from err

    @staticmethod
    def _parse_json(raw: bytes) -> dict[str, Any]:
        try:
            return json.loads(raw.decode('utf-8', errors='ignore'))
        except Exception:
            return {}

    def _request_json(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        with_auth: bool = True,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if with_auth:
            headers['Authorization'] = f'Bearer {self.get_tenant_access_token()}'
        status, _, raw = self._http_request(method=method, path=path, headers=headers, query=query, body=body)
        payload = self._parse_json(raw)
        if status >= 500:
            msg = payload.get('msg') if isinstance(payload, dict) else ''
            raise RuntimeError(f'飞书服务异常({status}): {msg or "unknown"}')
        return payload

    def get_tenant_access_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token

        payload = self._request_json(
            method='POST',
            path='/open-apis/auth/v3/tenant_access_token/internal/',
            body={
                'app_id': self.app_id,
                'app_secret': self.app_secret,
            },
            with_auth=False,
        )
        if payload.get('code') != 0:
            raise RuntimeError(f'获取飞书 tenant_access_token 失败: {payload.get("msg")}')

        token = str(payload.get('tenant_access_token') or '').strip()
        if not token:
            raise RuntimeError('获取飞书 tenant_access_token 失败: token 为空')
        self._tenant_access_token = token
        return token

    @staticmethod
    def parse_meeting_no(meeting_url: str) -> str:
        raw = (meeting_url or '').strip()
        if not raw:
            raise ValueError('meeting_url 不能为空')

        # 支持直接传会议号。
        if re.fullmatch(r'\d{6,}', raw):
            return raw

        parsed = urlparse(raw)
        # 常见格式：/j/151322082
        path_match = re.search(r'/j/(\d{6,})', parsed.path or '')
        if path_match:
            return path_match.group(1)

        # 兜底：从完整链接里提取一段数字会议号。
        any_match = re.search(r'(\d{6,})', raw)
        if any_match:
            return any_match.group(1)

        raise ValueError('无法从会议链接中解析 meeting_no')

    @staticmethod
    def parse_minutes_token(minutes_url: str) -> str:
        raw = (minutes_url or '').strip()
        match = re.search(r'/minutes/([A-Za-z0-9_-]{8,})', raw)
        return match.group(1) if match else ''

    @staticmethod
    def _parse_ts(raw: Any) -> datetime | None:
        text = str(raw or '').strip()
        if not text:
            return None
        if text.isdigit():
            try:
                value = int(text)
                # 飞书时间戳可能为毫秒或秒。
                if value > 10_000_000_000:
                    value = int(value / 1000)
                return datetime.fromtimestamp(value)
            except Exception:
                return None
        return None

    @staticmethod
    def _walk_text_nodes(node: Any, path: list[str], out: list[tuple[list[str], str]]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                FeishuApiClient._walk_text_nodes(value, [*path, str(key)], out)
            return
        if isinstance(node, list):
            for value in node:
                FeishuApiClient._walk_text_nodes(value, path, out)
            return
        if isinstance(node, (str, int, float)):
            text = str(node).strip()
            if text:
                out.append((path, text))

    @staticmethod
    def _dedupe_lines(lines: list[str], limit: int = 12) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for line in lines:
            normalized = re.sub(r'\s+', ' ', str(line or '')).strip()
            if not normalized:
                continue
            if len(normalized) < 4:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
            if len(merged) >= limit:
                break
        return merged

    @classmethod
    def extract_minute_summaries(cls, minute: dict[str, Any]) -> tuple[str, str]:
        """
        会议进行中场景优先提取「正式章节总结」，草稿内容作为回退。
        """
        if not isinstance(minute, dict) or not minute:
            return '', ''

        text_nodes: list[tuple[list[str], str]] = []
        cls._walk_text_nodes(minute, [], text_nodes)

        formal_lines: list[str] = []
        draft_lines: list[str] = []
        for path_parts, text in text_nodes:
            path_text = '.'.join(path_parts).lower()
            value_text = text.lower()

            if text.startswith('http://') or text.startswith('https://'):
                continue
            if len(text) > 500:
                continue

            has_summary_signal = any(
                key in path_text or key in value_text
                for key in ['summary', 'chapter', 'outline', 'topic', 'section', 'mindmap', '总结', '章节', '议题']
            )
            if not has_summary_signal:
                continue

            is_draft = any(
                key in path_text or key in value_text
                for key in ['draft', 'live', 'ongoing', 'current', '实时', '草稿', '正在']
            )
            if is_draft:
                draft_lines.append(text)
            else:
                formal_lines.append(text)

        formal = '\n'.join(cls._dedupe_lines(formal_lines, limit=10)).strip()
        draft = '\n'.join(cls._dedupe_lines(draft_lines, limit=10)).strip()
        return formal, draft

    def list_meetings_by_no(self, meeting_no: str, start_ts: int, end_ts: int) -> list[dict[str, Any]]:
        page_token = ''
        meeting_briefs: list[dict[str, Any]] = []
        max_pages = 10

        for _ in range(max_pages):
            query = {
                'meeting_no': meeting_no,
                'start_time': start_ts,
                'end_time': end_ts,
                'page_size': 50,
            }
            if page_token:
                query['page_token'] = page_token
            payload = self._request_json('GET', '/open-apis/vc/v1/meetings/list_by_no', query=query)
            if payload.get('code') != 0:
                raise RuntimeError(f'查询会议列表失败: {payload.get("msg")}')
            data = payload.get('data') or {}
            current = data.get('meeting_briefs') or []
            if isinstance(current, list):
                meeting_briefs.extend(current)
            has_more = bool(data.get('has_more'))
            page_token = str(data.get('page_token') or '').strip()
            if not has_more or not page_token:
                break

        return meeting_briefs

    def get_meeting_detail(self, meeting_id: str) -> dict[str, Any]:
        payload = self._request_json('GET', f'/open-apis/vc/v1/meetings/{meeting_id}')
        if payload.get('code') != 0:
            return {}
        data = payload.get('data') or {}
        return data.get('meeting') or {}

    def get_recording(self, meeting_id: str) -> dict[str, Any]:
        payload = self._request_json('GET', f'/open-apis/vc/v1/meetings/{meeting_id}/recording')
        if payload.get('code') != 0:
            return {'code': payload.get('code'), 'msg': payload.get('msg'), 'recording': {}}
        data = payload.get('data') or {}
        return {'code': 0, 'msg': '', 'recording': data.get('recording') or {}}

    def get_minute(self, minute_token: str) -> dict[str, Any]:
        payload = self._request_json('GET', f'/open-apis/minutes/v1/minutes/{minute_token}')
        if payload.get('code') != 0:
            return {'code': payload.get('code'), 'msg': payload.get('msg'), 'minute': {}}
        data = payload.get('data') or {}
        return {'code': 0, 'msg': '', 'minute': data.get('minute') or {}}

    def get_transcript(self, minute_token: str) -> tuple[str, str, str]:
        status, headers, raw = self._http_request(
            method='GET',
            path=f'/open-apis/minutes/v1/minutes/{minute_token}/transcript',
            headers={'Authorization': f'Bearer {self.get_tenant_access_token()}'},
            query={
                'need_speaker': 'true',
                'need_timestamp': 'true',
                'file_format': 'txt',
            },
            body=None,
        )
        content_type = (headers.get('content-type') or '').lower()
        if 'application/json' in content_type:
            payload = self._parse_json(raw)
            code = payload.get('code')
            msg = str(payload.get('msg') or '')
            if code == 0:
                return 'ready', '', ''
            if 'not ready' in msg.lower():
                return 'not_ready', '', msg
            if 'permission' in msg.lower():
                return 'permission_denied', '', msg
            return 'error', '', msg or f'json error code={code}'

        if status >= 400:
            preview = raw.decode('utf-8', errors='ignore')
            return 'error', '', preview[:300]

        text = raw.decode('utf-8', errors='ignore').strip()
        if text:
            return 'ready', text, ''
        return 'empty', '', 'transcript 为空'

    def fetch_items_from_meeting_url(self, meeting_url: str, lookback_days: int = 30) -> list[FeishuMeetingImportItem]:
        meeting_no = self.parse_meeting_no(meeting_url)
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=max(1, int(lookback_days)))).timestamp())
        briefs = self.list_meetings_by_no(meeting_no=meeting_no, start_ts=start_time, end_ts=end_time)
        if not briefs:
            raise RuntimeError('未查询到会议记录，请确认链接和时间范围')

        items: list[FeishuMeetingImportItem] = []
        for brief in briefs:
            meeting_id = str(brief.get('id') or '').strip()
            if not meeting_id:
                continue

            detail = self.get_meeting_detail(meeting_id=meeting_id)
            topic = str(detail.get('topic') or brief.get('topic') or '').strip()
            start_raw = detail.get('start_time') or brief.get('start_time')
            end_raw = detail.get('end_time') or brief.get('end_time')

            recording_payload = self.get_recording(meeting_id=meeting_id)
            recording = recording_payload.get('recording') or {}
            minute_url = str(recording.get('url') or '').strip()
            minute_token = self.parse_minutes_token(minute_url)

            minute_title = ''
            minute_owner_id = ''
            minute_summary_formal = ''
            minute_summary_draft = ''
            transcript_status = 'missing'
            transcript_text = ''
            transcript_error = ''

            if minute_token:
                minute_payload = self.get_minute(minute_token=minute_token)
                minute = minute_payload.get('minute') or {}
                minute_title = str(minute.get('title') or '').strip()
                minute_owner_id = str(minute.get('owner_id') or '').strip()
                minute_summary_formal, minute_summary_draft = self.extract_minute_summaries(minute)
                transcript_status, transcript_text, transcript_error = self.get_transcript(minute_token=minute_token)
            else:
                recording_msg = str(recording_payload.get('msg') or '').strip()
                meeting_status = str(detail.get('status') or '').strip()
                if recording_msg.lower() == 'meeting status unexpected' or meeting_status == '2':
                    transcript_status = 'pending'
                    transcript_error = '会议进行中，录制/妙记尚未生成'
                else:
                    transcript_status = 'missing'
                    transcript_error = recording_msg or '该会议未找到可用妙记链接'

            items.append(
                FeishuMeetingImportItem(
                    meeting_no=meeting_no,
                    meeting_id=meeting_id,
                    topic=topic,
                    start_time=self._parse_ts(start_raw),
                    end_time=self._parse_ts(end_raw),
                    minute_url=minute_url,
                    minute_token=minute_token,
                    minute_title=minute_title,
                    minute_owner_id=minute_owner_id,
                    minute_summary_formal=minute_summary_formal,
                    minute_summary_draft=minute_summary_draft,
                    transcript_text=transcript_text,
                    transcript_status=transcript_status,
                    transcript_error=transcript_error,
                )
            )

        return items

    def fetch_items_from_minutes_url(self, minutes_url: str) -> list[FeishuMeetingImportItem]:
        minute_token = self.parse_minutes_token(minutes_url)
        if not minute_token:
            raise ValueError('无法从妙记链接中解析 minute_token')

        minute_payload = self.get_minute(minute_token=minute_token)
        minute = minute_payload.get('minute') or {}

        minute_title = str(minute.get('title') or '').strip()
        minute_owner_id = str(minute.get('owner_id') or '').strip()
        minute_summary_formal, minute_summary_draft = self.extract_minute_summaries(minute)
        minute_url = str(minute.get('url') or minutes_url).strip()
        create_time = self._parse_ts(minute.get('create_time'))
        duration_text = str(minute.get('duration') or '').strip()
        end_time = None
        if create_time and duration_text.isdigit():
            try:
                duration_ms = int(duration_text)
                end_time = create_time + timedelta(milliseconds=duration_ms)
            except Exception:
                end_time = None

        transcript_status, transcript_text, transcript_error = self.get_transcript(minute_token=minute_token)
        minute_error = str(minute_payload.get('msg') or '').strip()
        if minute_payload.get('code') != 0 and minute_error and minute_error not in transcript_error:
            transcript_error = f'{minute_error}；{transcript_error}'.strip('；')
            if transcript_status == 'ready':
                transcript_status = 'error'
        item = FeishuMeetingImportItem(
            meeting_no='',
            meeting_id=f'minute:{minute_token}',
            topic=minute_title,
            start_time=create_time,
            end_time=end_time,
            minute_url=minute_url,
            minute_token=minute_token,
            minute_title=minute_title,
            minute_owner_id=minute_owner_id,
            minute_summary_formal=minute_summary_formal,
            minute_summary_draft=minute_summary_draft,
            transcript_text=transcript_text,
            transcript_status=transcript_status,
            transcript_error=transcript_error,
        )
        return [item]

    def fetch_items_from_url(self, source_url: str, lookback_days: int = 30) -> list[FeishuMeetingImportItem]:
        minute_token = self.parse_minutes_token(source_url)
        if minute_token:
            return self.fetch_items_from_minutes_url(source_url)
        return self.fetch_items_from_meeting_url(meeting_url=source_url, lookback_days=lookback_days)
