export interface ReportListItem {
  id: number;
  title: string;
  speaker: string;
  source_language: string;
  meeting_time: string;
  status: 'draft' | 'reviewed' | 'published';
  auto_play_enabled: boolean;
}

export interface ReportDetail {
  id: number;
  title: string;
  speaker: string;
  source_language: string;
  meeting_time: string;
  summary_raw: string;
  script_draft: string;
  script_final: string;
  highlights_draft: string[];
  highlights_final: string[];
  reflections_final: string[];
  auto_play_enabled: boolean;
  status: string;
  published_at: string | null;
}

export interface PlaybackQueueItem {
  id: number;
  title: string;
  speaker: string;
  meeting_time: string;
  script_final: string;
  highlights_final: string[];
  reflections_final: string[];
  localized?: Record<
    string,
    {
      title: string;
      script_final: string;
      highlights_final: string[];
      reflections_final?: string[];
      render_mode?: 'text' | 'audio';
      audio_ready?: boolean;
      audio_pcm_base64?: string;
    }
  >;
}

export interface TranslationItem {
  language_key: string;
  status: 'missing' | 'ready';
  reviewed: boolean;
  reviewed_at: string | null;
  title: string;
  script_final: string;
  highlights_final: string[];
  reflections_final: string[];
  render_mode: 'text' | 'audio';
  audio_ready: boolean;
}

export interface PlaybackModeState {
  mode: 'realtime_summary' | 'carousel_summary' | 'reflection_qa';
  carousel_scope: 'single' | 'loop';
  selected_report_id: number | null;
  updated_at: string;
}

export interface FeishuLiveRecordItem {
  timestamp: string;
  speaker: string;
  content: string;
}

export interface ReflectionItem {
  text: string;
}

export interface FeishuMeetingImportItem {
  meeting_no: string;
  meeting_id: string;
  minute_token: string;
  minute_url: string;
  title: string;
  report_id: number | null;
  transcript_status: string;
  note: string;
}

export interface FeishuMeetingDiagnoseStep {
  step: string;
  ok: boolean;
  detail: string;
  data: Record<string, any>;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = API_BASE ? `${API_BASE}${path}` : path;
  let resp: Response;
  try {
    resp = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
      ...init,
    });
  } catch (e: any) {
    throw new Error(`网络请求失败：${String(e?.message || e)}。请检查后端服务是否启动，或是否被浏览器拦截。`);
  }
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `请求失败: ${resp.status}`);
  }
  return resp.json() as Promise<T>;
}

export async function listReports(page = 1, pageSize = 20, status?: string) {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  if (status) params.set('status', status);
  return request<{ items: ReportListItem[]; total: number; page: number; page_size: number }>(
    `/api/reports?${params.toString()}`,
  );
}

export async function getReport(id: number) {
  return request<ReportDetail>(`/api/reports/${id}`);
}

export async function createReport(payload: {
  title: string;
  meeting_time?: string;
  speaker?: string;
  summary_raw: string;
  source_language?: string;
  script_final: string;
  highlights_final: string[];
  reflections_final?: string[];
  auto_play_enabled?: boolean;
}) {
  return request<ReportDetail>('/api/reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateReport(
  id: number,
  payload: Partial<{
    title: string;
    meeting_time: string;
    speaker: string;
    summary_raw: string;
    source_language: string;
    script_final: string;
    highlights_final: string[];
    reflections_final: string[];
    auto_play_enabled: boolean;
  }>,
) {
  return request<ReportDetail>(`/api/reports/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteReport(id: number) {
  return request<{ ok: boolean; deleted_id: number }>(`/api/reports/${id}`, {
    method: 'DELETE',
  });
}

export async function generateReport(id: number) {
  return request<{ report_id: number; script_draft: string; highlights_draft: string[]; reflections_draft: string[] }>(
    `/api/reports/${id}/generate`,
    {
      method: 'POST',
    },
  );
}

export async function generateReportPack(id: number) {
  return request<{ report_id: number; script_draft: string; highlights_draft: string[]; reflections_draft: string[] }>(
    `/api/reports/${id}/generate-pack`,
    {
      method: 'POST',
    },
  );
}

export async function generatePreview(payload: { title: string; speaker?: string; summary_raw: string }) {
  return request<{ script_draft: string; highlights_draft: string[]; reflections_draft: string[] }>('/api/reports/generate-preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function translateScript(payload: { script_text: string; target_language: string }) {
  return request<{ translated_text: string }>('/api/reports/translate-script', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function synthesizeScriptAudio(payload: { script_text: string; language_key: string }) {
  return request<{ language_key: string; audio_pcm_base64: string }>('/api/reports/synthesize-audio', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function publishReport(id: number) {
  return request<{ report_id: number; status: string; published_at: string }>(`/api/reports/${id}/publish`, {
    method: 'POST',
  });
}

export async function latestPublishedReport() {
  return request<ReportDetail>('/api/reports/published/latest');
}

export async function getReportTranslations(id: number) {
  return request<{ report_id: number; items: TranslationItem[] }>(`/api/reports/${id}/translations`);
}

export async function prepareReportTranslation(id: number, languageKey: string) {
  return request<{
    report_id: number;
    language_key: string;
    status: 'missing' | 'ready';
    reviewed: boolean;
    reviewed_at: string | null;
    title: string;
    script_final: string;
    highlights_final: string[];
    reflections_final: string[];
    render_mode: 'text' | 'audio';
    audio_ready: boolean;
  }>(`/api/reports/${id}/translations/${languageKey}/prepare`, {
    method: 'POST',
  });
}

export async function updateReportTranslation(
  id: number,
  languageKey: string,
  payload: Partial<{
    title: string;
    script_final: string;
    highlights_final: string[];
    reflections_final: string[];
    reviewed: boolean;
  }>,
) {
  return request<{
    report_id: number;
    language_key: string;
    status: 'missing' | 'ready';
    reviewed: boolean;
    reviewed_at: string | null;
    title: string;
    script_final: string;
    highlights_final: string[];
    reflections_final: string[];
    render_mode: 'text' | 'audio';
    audio_ready: boolean;
  }>(`/api/reports/${id}/translations/${languageKey}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function getReportReflection(id: number) {
  return request<{ report_id: number; reflections: ReflectionItem[] }>(`/api/reports/${id}/reflection`);
}

export async function getPlaybackQueue(options?: { includeAudio?: boolean; langs?: string[]; reportId?: number }) {
  const params = new URLSearchParams();
  if (options?.includeAudio) params.set('include_audio', 'true');
  if (options?.langs?.length) params.set('langs', options.langs.join(','));
  if (options?.reportId) params.set('report_id', String(options.reportId));
  const query = params.toString();
  const path = query ? `/api/reports/playback/queue?${query}` : '/api/reports/playback/queue';
  return request<{ items: PlaybackQueueItem[]; total: number }>(path);
}

export async function getPlaybackMode() {
  return request<PlaybackModeState>('/api/playback/mode');
}

export async function updatePlaybackMode(payload: {
  mode: 'realtime_summary' | 'carousel_summary' | 'reflection_qa';
  carousel_scope?: 'single' | 'loop';
  selected_report_id?: number | null;
}) {
  return request<PlaybackModeState>('/api/playback/mode', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function getFeishuLiveRecords(limit = 12, reportId?: number | null) {
  const query = new URLSearchParams();
  query.set('limit', String(limit));
  if (reportId && reportId > 0) {
    query.set('report_id', String(reportId));
  }
  return request<{ source: string; records: FeishuLiveRecordItem[] }>(`/api/playback/live-records?${query.toString()}`);
}

export async function getAvatarToken() {
  return request<{
    token: string;
    figure_id: string;
    camera_id?: string;
    resolution_width: number;
    resolution_height: number;
  }>('/api/avatar/token', {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export async function importFeishuMeeting(payload: {
  meeting_url: string;
  lookback_days?: number;
  auto_generate?: boolean;
  auto_enable_playback?: boolean;
}) {
  return request<{
    imported_count: number;
    updated_count: number;
    failed_count: number;
    items: FeishuMeetingImportItem[];
    message: string;
  }>('/api/reports/import/feishu-meeting', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function inspectFeishuMeeting(payload: { meeting_url: string; lookback_days?: number }) {
  return request<{
    total: number;
    items: Array<{
      meeting_no: string;
      meeting_id: string;
      topic: string;
      start_time: string | null;
      end_time: string | null;
      minute_token: string;
      minute_url: string;
      minute_title: string;
      minute_owner_id: string;
      transcript_status: string;
      transcript_error: string;
      transcript_text: string;
    }>;
    message: string;
  }>('/api/reports/import/feishu-meeting/inspect', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function diagnoseFeishuMeeting(payload: { meeting_url: string; lookback_days?: number }) {
  return request<{
    ok: boolean;
    meeting_no: string;
    steps: FeishuMeetingDiagnoseStep[];
    suggestion: string;
  }>('/api/reports/import/feishu-meeting/diagnose', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
