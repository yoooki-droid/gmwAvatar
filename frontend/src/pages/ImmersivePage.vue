<template>
  <main class="immersive-root">
    <div class="immersive-stage">
      <div class="immersive-avatar-wrap">
        <div class="immersive-status">
          模式：{{ modeLabel }} ｜ 数字人状态：{{ avatarStatus }} ｜ 语言：{{ currentLanguageLabel }} ｜ 文案：{{
            isPreparingScript ? '准备中' : '已就绪'
          }}
        </div>
        <BaiduAvatarPlayer
          ref="playerRef"
          :config="activeAvatarConfig"
          :script="report.scriptFinal"
          :render-mode="report.renderMode"
          :audio-pcm-base64="report.audioPcmBase64"
          :auto-play-when-ready="autoPlayEnabled"
          :loop-play="false"
          :show-toolbar="false"
          @status="avatarStatus = $event"
          @finished="handleBroadcastFinished"
        />
      </div>

      <section class="immersive-panel" :class="{ 'immersive-panel-reflection': playbackMode === 'reflection_qa' }">
        <template v-if="playbackMode === 'realtime_summary'">
          <div class="immersive-live-cards immersive-live-cards-only" :key="realtimeBatchKey">
            <p
              class="immersive-live-line"
              v-for="(item, idx) in realtimeDisplayLines"
              :key="`${realtimeBatchKey}-${idx}`"
              :style="{ animationDelay: `${idx * 120}ms` }"
            >
              {{ item }}
            </p>
          </div>
        </template>
        <template v-else>
          <div class="immersive-tag">今日播报</div>
          <h1 class="immersive-title">{{ report.title || '暂无新闻标题' }}</h1>
          <div class="immersive-highlight-cards" v-if="playbackMode !== 'reflection_qa'">
            <div class="immersive-highlight-card" v-for="(item, idx) in highlightsForView" :key="idx">
              <p>
                <span class="quote-mark quote-open">“</span>
                <span class="quote-text">{{ item }}</span>
                <span class="quote-mark quote-close">”</span>
              </p>
            </div>
          </div>
          <div class="immersive-reflection-cards" v-else>
            <div class="immersive-reflection-item" v-for="(item, idx) in reflectionsForView" :key="idx">
              <span class="reflection-index">{{ idx + 1 }}.</span>
              <p>{{ item }}</p>
            </div>
          </div>
          <div class="immersive-watermark">TPCNEWS</div>
        </template>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import BaiduAvatarPlayer from '../components/BaiduAvatarPlayer.vue';
import {
  getAvatarToken,
  getFeishuLiveRecords,
  getPlaybackMode,
  getPlaybackQueue,
  getReportReflection,
  prepareReportTranslation,
  synthesizeScriptAudio,
  translateScript,
  type PlaybackQueueItem,
} from '../services/api';

interface AvatarConfig {
  token: string;
  figureId: string | number;
  cameraId?: string | number;
  resolutionWidth?: number;
  resolutionHeight?: number;
  autoChromaKey?: boolean;
  videoBg?: string;
  ttsPer?: string;
  ttsLan?: string;
  ttsSample?: string;
  preAlertSec?: number;
  positionV2?: string;
}

interface LanguageOption {
  key: string;
  label: string;
  ttsLan: string;
}

type PlaybackMode = 'realtime_summary' | 'carousel_summary' | 'reflection_qa';

const AVATAR_POSITION_V2 = '{"location":{"top":36,"left":710,"width":608,"height":1080}}';
const localConfigKey = 'baidu_avatar_manual_config';
const activeConfigKey = 'baidu_avatar_active_config';
const localLanguageKey = 'playback_language_selection';
const queueVersionKey = 'playback_queue_version';
const runtimeVersionKey = 'playback_runtime_version';
const runtimeBroadcastChannel = 'playback_runtime_channel';
const focusReportIdKey = 'playback_focus_report_id';

const languageOptions: LanguageOption[] = [
  { key: 'zh', label: '中文', ttsLan: 'Chinese' },
  { key: 'en', label: '英文', ttsLan: 'English' },
  { key: 'yue', label: '粤语', ttsLan: 'Chinese,Yue' },
  { key: 'ja', label: '日语', ttsLan: 'Japanese' },
  { key: 'id', label: '印度尼西亚语', ttsLan: 'Indonesian' },
  { key: 'ms', label: '马来西亚语', ttsLan: 'auto' },
  { key: 'hi', label: '印度语', ttsLan: 'Hindi' },
];

const languageTargetMap: Record<string, string> = {
  zh: 'Chinese',
  en: 'English',
  yue: 'Cantonese (Yue Chinese, spoken style in Traditional Chinese characters)',
  ja: 'Japanese',
  id: 'Indonesian',
  ms: 'Malay (Malaysia)',
  hi: 'Hindi',
};
const TEXT_RENDER_LANGUAGE_KEYS = new Set(['zh', 'en']);

const route = useRoute();
const playerRef = ref<InstanceType<typeof BaiduAvatarPlayer> | null>(null);
const avatarStatus = ref('初始化中');
const isPreparingScript = ref(false);

const report = reactive({
  id: '',
  title: '',
  scriptFinal: '',
  highlightsFinal: [] as string[],
  reflectionsFinal: [] as string[],
  renderMode: 'text' as 'text' | 'audio',
  audioPcmBase64: '',
});

const queueItems = ref<PlaybackQueueItem[]>([]);
const currentIndex = ref(0);
const selectedLanguageKeys = ref<string[]>(['zh']);
const currentLanguageIndex = ref(0);
const lastRenderSignature = ref('');
const audioCache = ref<Record<string, string>>({});
const textCache = ref<Record<string, { title: string; script: string; highlights: string[] }>>({});
const nonCarouselAudioCache = ref<Record<string, string>>({});

const playbackMode = ref<PlaybackMode>('carousel_summary');
const carouselScope = ref<'single' | 'loop'>('loop');
const selectedReportId = ref<number | null>(null);

const liveSummaryLines = ref<string[]>([]);
const realtimeBatchKey = ref(0);
const realtimeDisplayLines = ref<string[]>([]);
const realtimeLastHash = ref('');
const reflectionLines = ref<string[]>([]);
const reflectionLoadedReportId = ref<number | null>(null);

const baseAvatarConfig = ref<AvatarConfig | null>(null);

const currentLanguage = computed<LanguageOption>(() => {
  const key = selectedLanguageKeys.value[currentLanguageIndex.value];
  return languageOptions.find((x) => x.key === key) || languageOptions[0];
});

const currentLanguageLabel = computed(() => currentLanguage.value.label);
const autoPlayEnabled = computed(() => playbackMode.value !== 'realtime_summary');
const modeLabel = computed(() => {
  if (playbackMode.value === 'realtime_summary') return '实时总结';
  if (playbackMode.value === 'reflection_qa') return '反思';
  return '轮播会议总结';
});

const activeAvatarConfig = computed<AvatarConfig | null>(() => {
  // 语言切换时仅切换播报文案/音频，不重建数字人实例。
  return baseAvatarConfig.value;
});

const highlightsForView = computed(() => {
  const items = report.highlightsFinal.filter(Boolean).slice(0, 2);
  if (items.length >= 2) return items;
  if (items.length === 1) return [items[0], items[0]];
  return ['暂无亮点内容', '暂无亮点内容'];
});

const reflectionsForView = computed(() => {
  const items = report.reflectionsFinal.filter(Boolean).slice(0, 3);
  if (items.length) return items;
  return ['暂无反思内容', '暂无反思内容', '暂无反思内容'];
});

const updateRealtimeDisplayLines = (force = false) => {
  const source = liveSummaryLines.value
    .map((x) => String(x || '').trim())
    .filter(Boolean)
    .slice(0, 8);
  const hash = source.join('||');
  if (!force && hash && hash === realtimeLastHash.value) return;
  realtimeLastHash.value = hash;
  realtimeBatchKey.value += 1;
  realtimeDisplayLines.value = source;
};

const getCurrentQueueItem = () => queueItems.value[currentIndex.value];

const resolveLocalizedContent = (item: PlaybackQueueItem, lang: LanguageOption) => {
  const localized = item.localized?.[lang.key];
  let title = String(localized?.title || (lang.key === 'zh' ? item.title : '') || '').trim();
  const script = String(localized?.script_final || (lang.key === 'zh' ? item.script_final : '') || '').trim();
  const highlightsRaw = localized?.highlights_final || (lang.key === 'zh' ? item.highlights_final : []) || [];
  const reflectionsRaw = localized?.reflections_final || (lang.key === 'zh' ? item.reflections_final : []) || [];
  let highlights = Array.isArray(highlightsRaw) ? highlightsRaw.map((x) => String(x).trim()).filter(Boolean).slice(0, 2) : [];
  let reflections = Array.isArray(reflectionsRaw)
    ? reflectionsRaw.map((x) => String(x).trim()).filter(Boolean).slice(0, 5)
    : [];
  if (!title && lang.key !== 'zh') title = `${lang.label}内容准备中`;
  if (!highlights.length && lang.key !== 'zh') highlights = ['翻译与音频准备中', '准备完成后将自动切换'];
  if (!reflections.length && lang.key !== 'zh') reflections = ['翻译准备中', '翻译完成后自动更新', '请稍候'];

  const renderMode = (localized?.render_mode ||
    (lang.key === 'zh' || lang.key === 'en' ? 'text' : 'audio')) as 'text' | 'audio';
  const cacheKey = `${item.id}:${lang.key}`;
  const audioPcmBase64 = String(localized?.audio_pcm_base64 || audioCache.value[cacheKey] || '').trim();
  const audioReady = Boolean(localized?.audio_ready ?? (renderMode === 'audio' ? !!audioPcmBase64 : true));
  return { title, script, highlights, reflections, renderMode, audioPcmBase64, audioReady };
};

const buildRenderSignature = (seed: string) =>
  `${seed}|${currentLanguage.value.key}|${selectedLanguageKeys.value.join(',')}|${playbackMode.value}|${carouselScope.value}`;

const fetchAudioForReportLanguage = async (reportId: number, languageKey: string): Promise<string> => {
  const cacheKey = `${reportId}:${languageKey}`;
  if (audioCache.value[cacheKey]) return audioCache.value[cacheKey];
  const data = await getPlaybackQueue({ includeAudio: true, langs: [languageKey], reportId });
  const item = (data.items || [])[0];
  const audio = String(item?.localized?.[languageKey]?.audio_pcm_base64 || '').trim();
  if (audio) {
    audioCache.value[cacheKey] = audio;
  }
  return audio;
};

const refreshSingleQueueItem = async (reportId: number, languageKey: string, includeAudio: boolean) => {
  const data = await getPlaybackQueue({
    reportId,
    includeAudio,
    langs: includeAudio ? [languageKey] : undefined,
  });
  const fresh = (data.items || [])[0];
  if (!fresh) return null;
  const idx = queueItems.value.findIndex((x) => x.id === reportId);
  if (idx >= 0) {
    queueItems.value[idx] = fresh;
  }
  return fresh;
};

const translateNonCarouselPayload = async (
  seedKey: string,
  payload: { title: string; script: string; highlights: string[] },
): Promise<{ title: string; script: string; highlights: string[] }> => {
  const langKey = currentLanguage.value.key;
  if (langKey === 'zh') return payload;

  const cacheKey = `${seedKey}:${langKey}`;
  if (textCache.value[cacheKey]) {
    return textCache.value[cacheKey];
  }

  const targetLanguage = languageTargetMap[langKey] || 'English';
  const translateOne = async (text: string): Promise<string> => {
    const input = text.trim();
    if (!input) return '';
    try {
      const out = await translateScript({ script_text: input, target_language: targetLanguage });
      return (out.translated_text || '').trim() || input;
    } catch {
      return input;
    }
  };

  const [translatedTitle, translatedScript] = await Promise.all([
    translateOne(payload.title),
    translateOne(payload.script),
  ]);

  const translatedHighlightsRaw = await Promise.all(payload.highlights.map((row) => translateOne(row)));
  const translatedHighlights = translatedHighlightsRaw.filter(Boolean);

  const result = {
    title: translatedTitle || payload.title,
    script: translatedScript || payload.script,
    highlights: translatedHighlights.length ? translatedHighlights : payload.highlights,
  };
  textCache.value[cacheKey] = result;
  return result;
};

const resolveNonCarouselAudio = async (
  seedKey: string,
  scriptText: string,
): Promise<{ renderMode: 'text' | 'audio'; audioPcmBase64: string }> => {
  const languageKey = currentLanguage.value.key;
  if (TEXT_RENDER_LANGUAGE_KEYS.has(languageKey)) {
    return { renderMode: 'text', audioPcmBase64: '' };
  }
  const cacheKey = `${seedKey}:${languageKey}`;
  const cachedAudio = String(nonCarouselAudioCache.value[cacheKey] || '').trim();
  if (cachedAudio) {
    return { renderMode: 'audio', audioPcmBase64: cachedAudio };
  }

  const response = await synthesizeScriptAudio({
    script_text: scriptText,
    language_key: languageKey,
  });
  const audio = String(response.audio_pcm_base64 || '').trim();
  if (!audio) {
    throw new Error('语音合成结果为空');
  }
  nonCarouselAudioCache.value[cacheKey] = audio;
  return { renderMode: 'audio', audioPcmBase64: audio };
};

const applyCarouselReport = async (force = false): Promise<boolean> => {
  const current = getCurrentQueueItem();
  if (!current) {
    report.id = '';
    report.title = '暂无可播报新闻';
    report.scriptFinal = '';
    report.highlightsFinal = [];
    report.reflectionsFinal = [];
    report.renderMode = 'text';
    report.audioPcmBase64 = '';
    isPreparingScript.value = false;
    lastRenderSignature.value = '';
    return false;
  }

  const signature = buildRenderSignature(
    `${current.id}|${current.title}|${current.script_final}|${JSON.stringify(current.highlights_final || [])}|${JSON.stringify(current.localized || {})}`,
  );
  if (!force && signature === lastRenderSignature.value) return true;
  isPreparingScript.value = true;

  try {
    const languageKey = currentLanguage.value.key;
    let localized = resolveLocalizedContent(current, currentLanguage.value);
    if (!localized.script) {
      await prepareReportTranslation(current.id, languageKey);
      const refreshed = await refreshSingleQueueItem(
        current.id,
        languageKey,
        localized.renderMode === 'audio',
      );
      if (refreshed) {
        localized = resolveLocalizedContent(refreshed, currentLanguage.value);
      }
    }

    report.id = String(current.id ?? '');
    report.title = localized.title;
    report.highlightsFinal = localized.highlights;
    report.reflectionsFinal = localized.reflections;
    report.scriptFinal = localized.script;
    report.renderMode = localized.renderMode;
    report.audioPcmBase64 = localized.audioPcmBase64;

    if (!localized.script) throw new Error('当前语言文案未就绪');

    if (localized.renderMode === 'audio' && !localized.audioPcmBase64) {
      const audio = await fetchAudioForReportLanguage(current.id, languageKey);
      if (audio) {
        report.audioPcmBase64 = audio;
      } else {
        await prepareReportTranslation(current.id, languageKey);
        const refreshed = await refreshSingleQueueItem(current.id, languageKey, true);
        const reloaded = refreshed ? resolveLocalizedContent(refreshed, currentLanguage.value) : localized;
        report.audioPcmBase64 = reloaded.audioPcmBase64 || '';
        if (!report.audioPcmBase64.trim()) throw new Error('当前语言音频未就绪');
      }
    }

    lastRenderSignature.value = signature;
    isPreparingScript.value = false;
    return true;
  } catch {
    isPreparingScript.value = false;
    return false;
  }
};

const applyRealtimeSummary = async (): Promise<boolean> => {
  isPreparingScript.value = true;
  try {
    updateRealtimeDisplayLines();
    const lines = liveSummaryLines.value.map((x) => String(x || '').trim()).filter(Boolean);

    if (!lines.length) {
      report.id = 'realtime';
      report.title = '会议实时总结（暂无数据）';
      report.scriptFinal = '';
      report.highlightsFinal = [];
      report.reflectionsFinal = [];
      report.renderMode = 'text';
      report.audioPcmBase64 = '';
      return false;
    }

    report.id = 'realtime';
    report.title = '会议实时总结';
    report.scriptFinal = lines.join('。') + '。';
    report.highlightsFinal = lines.slice(0, 2);
    report.reflectionsFinal = [];
    report.renderMode = 'text';
    report.audioPcmBase64 = '';
    lastRenderSignature.value = buildRenderSignature(`realtime:${report.scriptFinal}`);
    return true;
  } catch {
    return false;
  } finally {
    isPreparingScript.value = false;
  }
};

const applyReflectionSummary = async (): Promise<boolean> => {
  isPreparingScript.value = true;
  try {
    const targetId = selectedReportId.value || Number(route.params.id || '0') || queueItems.value[0]?.id;
    if (!targetId) {
      report.id = '';
      report.title = '反思（未选择新闻）';
      report.scriptFinal = '请先在调试页选择新闻并调取反思内容。';
      report.highlightsFinal = [];
      report.reflectionsFinal = ['暂无反思内容', '暂无反思内容', '暂无反思内容'];
      report.renderMode = 'text';
      report.audioPcmBase64 = '';
      return false;
    }
    selectedReportId.value = targetId;

    if (reflectionLoadedReportId.value !== targetId) {
      reflectionLines.value = [];
    }
    if (!reflectionLines.value.length) {
      try {
        const data = await getReportReflection(targetId);
        reflectionLines.value = (data.reflections || []).map((x) => x.text).filter(Boolean);
        reflectionLoadedReportId.value = targetId;
      } catch {
        reflectionLines.value = [];
        reflectionLoadedReportId.value = null;
      }
    }

    const target = queueItems.value.find((x) => x.id === targetId);
    const baseTitle = `${target?.title || '会议内容'}｜反思`;
    const baseReflections = reflectionLines.value.slice(0, 5);
    const baseScript = baseReflections.map((x, idx) => `第${idx + 1}条建议：${x}`).join('。');
    const baseHighlights = baseReflections;

    if (!baseScript.trim()) {
      report.id = String(targetId);
      report.title = baseTitle;
      report.scriptFinal = '当前暂无反思内容，请先在调试页调取反思内容。';
      report.highlightsFinal = [];
      report.reflectionsFinal = ['请先调取反思内容', '调取后将自动显示', '请稍候'];
      report.renderMode = 'text';
      report.audioPcmBase64 = '';
      return false;
    }

    const payload = await translateNonCarouselPayload(`reflection:${targetId}:${baseScript}`, {
      title: baseTitle,
      script: baseScript,
      highlights: baseHighlights,
    });

    const audioPayload = await resolveNonCarouselAudio(`reflection:${targetId}:${payload.script}`, payload.script);
    report.id = String(targetId);
    report.title = payload.title;
    report.scriptFinal = payload.script;
    report.highlightsFinal = [];
    report.reflectionsFinal = payload.highlights;
    report.renderMode = audioPayload.renderMode;
    report.audioPcmBase64 = audioPayload.audioPcmBase64;
    lastRenderSignature.value = buildRenderSignature(`reflection:${targetId}:${payload.script}`);
    return true;
  } catch {
    return false;
  } finally {
    isPreparingScript.value = false;
  }
};

const applyCurrentModeContent = async (force = false): Promise<boolean> => {
  if (playbackMode.value === 'realtime_summary') {
    return applyRealtimeSummary();
  }
  if (playbackMode.value === 'reflection_qa') {
    return applyReflectionSummary();
  }
  return applyCarouselReport(force);
};

const refreshQueue = async (keepPosition = true, focusReportId: number | null = null) => {
  const currentReportId = Number(report.id || '0');
  const prevLanguageIndex = currentLanguageIndex.value;
  try {
    const data = await getPlaybackQueue();
    queueItems.value = data.items || [];
    if (!queueItems.value.length) {
      currentIndex.value = 0;
      currentLanguageIndex.value = 0;
      await applyCurrentModeContent(true);
      return;
    }

    if (keepPosition) {
      if (focusReportId && focusReportId > 0) {
        const focusIndex = queueItems.value.findIndex((x) => x.id === focusReportId);
        if (focusIndex >= 0) {
          currentIndex.value = focusIndex;
        } else {
          const currentIndexFromQueue = currentReportId ? queueItems.value.findIndex((x) => x.id === currentReportId) : -1;
          currentIndex.value = currentIndexFromQueue >= 0 ? currentIndexFromQueue : 0;
        }
      } else {
        const currentIndexFromQueue = currentReportId ? queueItems.value.findIndex((x) => x.id === currentReportId) : -1;
        currentIndex.value = currentIndexFromQueue >= 0 ? currentIndexFromQueue : 0;
      }
      currentLanguageIndex.value =
        prevLanguageIndex < selectedLanguageKeys.value.length ? prevLanguageIndex : selectedLanguageKeys.value.length - 1;
    } else {
      const startId = focusReportId && focusReportId > 0 ? focusReportId : Number(route.params.id || '0');
      const startIndex = startId ? queueItems.value.findIndex((x) => x.id === startId) : -1;
      currentIndex.value = startIndex >= 0 ? startIndex : 0;
      currentLanguageIndex.value = 0;
    }

    await applyCurrentModeContent();
  } catch {
    queueItems.value = [];
    currentIndex.value = 0;
    currentLanguageIndex.value = 0;
    report.id = '';
    report.title = '播报队列加载失败';
    report.scriptFinal = '';
    report.highlightsFinal = [];
    report.reflectionsFinal = [];
    report.audioPcmBase64 = '';
    lastRenderSignature.value = '';
    isPreparingScript.value = false;
  }
};

const loadMode = async () => {
  const queryMode = String(route.query.mode || '').trim();
  if (queryMode === 'realtime_summary' || queryMode === 'carousel_summary' || queryMode === 'reflection_qa') {
    playbackMode.value = queryMode;
  }
  try {
    const mode = await getPlaybackMode();
    if (!queryMode) {
      playbackMode.value = mode.mode;
    }
    carouselScope.value = mode.carousel_scope;
    selectedReportId.value = mode.selected_report_id;
  } catch {
    if (!queryMode) {
      playbackMode.value = 'carousel_summary';
    }
    carouselScope.value = 'loop';
    selectedReportId.value = null;
  }
};

const loadRealtimeRecords = async () => {
  try {
    const data = await getFeishuLiveRecords(20, selectedReportId.value);
    liveSummaryLines.value = (data.records || []).map((x) => x.content).filter(Boolean);
    updateRealtimeDisplayLines();
  } catch {
    liveSummaryLines.value = [];
    updateRealtimeDisplayLines(true);
  }
};

const loadAvatarConfig = async () => {
  const activeRaw = window.localStorage.getItem(activeConfigKey);
  if (activeRaw) {
    try {
      const active = JSON.parse(activeRaw);
      if (active?.token && active?.figureId) {
        baseAvatarConfig.value = {
          token: String(active.token),
          figureId: String(active.figureId),
          cameraId: active.cameraId ? String(active.cameraId) : undefined,
          resolutionWidth: Number(route.query.rw || active.resolutionWidth || 1920),
          resolutionHeight: Number(route.query.rh || active.resolutionHeight || 1080),
          ttsLan: 'auto',
          autoChromaKey: true,
          positionV2: String(route.query.positionV2 || active.positionV2 || AVATAR_POSITION_V2),
          videoBg: '#F3F4FB',
          ttsPer: 'LITE_presenter_female',
          ttsSample: '16000',
          preAlertSec: 120,
        };
        return;
      }
    } catch {
      // 忽略损坏的生效配置。
    }
  }

  const raw = window.localStorage.getItem(localConfigKey);
  if (raw) {
    try {
      const local = JSON.parse(raw);
      if (local?.token && local?.figureId) {
        baseAvatarConfig.value = {
          token: String(local.token || ''),
          figureId: String(local.figureId || ''),
          cameraId: local.cameraId ? String(local.cameraId) : undefined,
          resolutionWidth: Number(route.query.rw || local.resolutionWidth || 1920),
          resolutionHeight: Number(route.query.rh || local.resolutionHeight || 1080),
          ttsLan: 'auto',
          autoChromaKey: true,
          positionV2: String(route.query.positionV2 || local.positionV2 || AVATAR_POSITION_V2),
          videoBg: '#F3F4FB',
          ttsPer: 'LITE_presenter_female',
          ttsSample: '16000',
          preAlertSec: 120,
        };
        return;
      }
    } catch {
      // 忽略损坏的本地配置。
    }
  }

  try {
    const data = await getAvatarToken();
    baseAvatarConfig.value = {
      token: data.token,
      figureId: data.figure_id,
      cameraId: data.camera_id,
      resolutionWidth: Number(route.query.rw || data.resolution_width || 1920),
      resolutionHeight: Number(route.query.rh || data.resolution_height || 1080),
      ttsLan: 'auto',
      autoChromaKey: true,
      positionV2: String(route.query.positionV2 || AVATAR_POSITION_V2),
      videoBg: '#F3F4FB',
      ttsPer: 'LITE_presenter_female',
      ttsSample: '16000',
      preAlertSec: 120,
    };
    return;
  } catch {
    // 后端未配置时，回退到本地手动配置。
  }
  baseAvatarConfig.value = null;
};

const loadLanguageSelection = (preferQuery = false) => {
  if (preferQuery) {
    const queryLangs = String(route.query.langs || '')
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean);
    if (queryLangs.length) {
      const valid = queryLangs.filter((x) => languageOptions.some((opt) => opt.key === x));
      if (valid.length) {
        selectedLanguageKeys.value = valid;
        return;
      }
    }
  }

  const raw = window.localStorage.getItem(localLanguageKey);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return;
    const valid = parsed.filter((x) => languageOptions.some((opt) => opt.key === x));
    if (valid.length) selectedLanguageKeys.value = valid;
  } catch {
    // 忽略损坏的本地配置。
  }
};

const applyRuntimeLanguages = (langs: unknown) => {
  if (!Array.isArray(langs)) return;
  const valid = langs
    .map((x) => String(x))
    .filter((x) => languageOptions.some((opt) => opt.key === x));
  if (!valid.length) return;
  selectedLanguageKeys.value = valid;
  currentLanguageIndex.value = 0;
};

const syncFromRuntimeConfig = async () => {
  const focusReportId = Number(window.localStorage.getItem(focusReportIdKey) || '0') || null;
  loadLanguageSelection(false);
  currentLanguageIndex.value = 0;
  reflectionLoadedReportId.value = null;
  await Promise.all([loadAvatarConfig(), loadMode()]);
  await refreshQueue(true, focusReportId);
  if (playbackMode.value === 'realtime_summary') {
    await loadRealtimeRecords();
    await applyRealtimeSummary();
    return;
  }
  if (playbackMode.value === 'reflection_qa') {
    const ok = await applyReflectionSummary();
    if (ok) {
      window.setTimeout(() => playCurrentOnPlayer(), 80);
    }
    return;
  }
  const ok = await applyCarouselReport(true);
  if (ok) {
    window.setTimeout(() => playCurrentOnPlayer(), 80);
  }
};

const playCurrentOnPlayer = () => {
  if (playbackMode.value === 'realtime_summary') return;
  if (isPreparingScript.value) return;
  if (report.renderMode === 'audio') {
    if (!report.audioPcmBase64.trim()) return;
    (playerRef.value as any)?.speakAudio?.(report.audioPcmBase64);
    return;
  }
  if (!report.scriptFinal.trim()) return;
  (playerRef.value as any)?.speakText?.(report.scriptFinal);
};

const getPlaySignature = () => {
  const audioSign = `${report.audioPcmBase64.length}:${report.audioPcmBase64.slice(0, 36)}`;
  return `${report.id}|${report.renderMode}|${report.scriptFinal}|${audioSign}|${playbackMode.value}`;
};

const handleBroadcastFinished = async () => {
  if (playbackMode.value === 'realtime_summary') return;
  if (isPreparingScript.value) return;
  const previousSignature = getPlaySignature();

  if (selectedLanguageKeys.value.length > 1 && currentLanguageIndex.value < selectedLanguageKeys.value.length - 1) {
    currentLanguageIndex.value += 1;
    const ok = await applyCurrentModeContent();
    if (!ok) return;
    if (getPlaySignature() === previousSignature) {
      window.setTimeout(() => playCurrentOnPlayer(), 420);
    }
    return;
  }

  currentLanguageIndex.value = 0;

  if (playbackMode.value === 'carousel_summary') {
    if (carouselScope.value === 'loop' && queueItems.value.length > 1) {
      currentIndex.value = (currentIndex.value + 1) % queueItems.value.length;
    }
    const ok = await applyCarouselReport();
    if (!ok) return;
    if (getPlaySignature() === previousSignature) {
      window.setTimeout(() => playCurrentOnPlayer(), 420);
    }
    return;
  }

  const ok = await applyCurrentModeContent(true);
  if (!ok) return;
  if (getPlaySignature() === previousSignature) {
    window.setTimeout(() => playCurrentOnPlayer(), 420);
  }
};

let queuePollTimer: number | null = null;
let runtimeChannel: BroadcastChannel | null = null;
const onStorageChanged = (event: StorageEvent) => {
  if (event.key === queueVersionKey) {
    void refreshQueue();
    return;
  }
  if (event.key === runtimeVersionKey || event.key === localLanguageKey) {
    void syncFromRuntimeConfig();
  }
};

onMounted(async () => {
  loadLanguageSelection(true);
  await Promise.all([loadAvatarConfig(), loadMode(), refreshQueue(false)]);
  await loadRealtimeRecords();
  updateRealtimeDisplayLines(true);
  await applyCurrentModeContent(true);

  window.addEventListener('storage', onStorageChanged);
  if (typeof window.BroadcastChannel !== 'undefined') {
    try {
      runtimeChannel = new window.BroadcastChannel(runtimeBroadcastChannel);
      runtimeChannel.onmessage = (event: MessageEvent) => {
        if (event.data?.type === 'runtime-sync') {
          applyRuntimeLanguages(event.data?.langs);
          void syncFromRuntimeConfig();
        }
      };
    } catch {
      runtimeChannel = null;
    }
  }
  queuePollTimer = window.setInterval(async () => {
    await loadMode();
    if (playbackMode.value === 'realtime_summary') {
      await loadRealtimeRecords();
      await applyRealtimeSummary();
      return;
    }
    if (playbackMode.value === 'reflection_qa') {
      await applyReflectionSummary();
      return;
    }
    await refreshQueue();
  }, 6000);
});

onUnmounted(() => {
  window.removeEventListener('storage', onStorageChanged);
  if (runtimeChannel) {
    runtimeChannel.close();
    runtimeChannel = null;
  }
  if (queuePollTimer) {
    window.clearInterval(queuePollTimer);
    queuePollTimer = null;
  }
});
</script>
