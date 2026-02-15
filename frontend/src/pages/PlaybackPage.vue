<template>
  <main class="page debug-page">
    <section class="hero debug-hero">
      <div class="avatar-panel">
        <BaiduAvatarPlayer
          ref="playerRef"
          v-if="debugAvatarEnabled"
          :config="activeAvatarConfig"
          :script="report.scriptFinal"
          :render-mode="report.renderMode"
          :audio-pcm-base64="report.audioPcmBase64"
          :auto-play-when-ready="autoPlayEnabled"
          :show-toolbar="true"
          @status="avatarStatus = $event"
          @finished="handleBroadcastFinished"
        />
        <div v-else class="avatar-stage avatar-empty">
          当前未加载数字人。你可以先设置模式、语言与队列，点击“加载数字人”后会按当前配置播报。
        </div>
      </div>

      <div class="content-panel debug-panel">
        <div class="tag">数字人调试页</div>
        <h1 class="title debug-title">{{ report.title || '未选择新闻' }}</h1>
        <p class="meta">模式：{{ currentModeLabel }} ｜ 当前语言：{{ currentLanguageLabel }}</p>
        <p class="meta" v-if="playbackMode === 'carousel_summary'">
          自动播报队列：{{ queueItems.length }} 条 ｜ 当前第 {{ currentOrderLabel }} 条 ｜ 轮播策略：{{ carouselScopeLabel }}
        </p>
        <p class="meta" v-else-if="playbackMode === 'reflection_qa'">
          反思建议：{{ reflectionItems.length }} 条 ｜ 新闻ID：{{ selectedReflectionReportId || '-' }}
        </p>
        <p class="meta" v-else>
          实时总结记录：{{ liveRecords.length }} 条
        </p>
        <div class="script-box global-action-bar">
          <button class="btn" @click="saveAllConfig">保存配置</button>
          <button class="btn primary" @click="saveConfigAndApply">保存并立即执行</button>
          <button class="btn dark" :disabled="!canOpenImmersive" @click="openImmersivePage">打开沉浸式播报页</button>
          <span class="status-text">{{ configInfo }}</span>
        </div>

        <div class="script-box layer-card">
          <h2>语言层</h2>
          <div class="language-box">
            <h3>播报语言（可多选）</h3>
            <div class="language-grid">
              <label class="language-item" v-for="opt in languageOptions" :key="opt.key">
                <input
                  type="checkbox"
                  :checked="selectedLanguageKeys.includes(opt.key)"
                  @change="toggleLanguage(opt.key, $event)"
                />
                <span>{{ opt.label }}</span>
              </label>
            </div>
            <p class="hint">轮播模式下会按“同一条新闻的多语言播完，再到下一条”。</p>
          </div>
        </div>

        <div class="script-box layer-card">
          <h2>模式层</h2>
          <div class="actions mode-switch-row">
            <button class="btn" :class="{ primary: playbackMode === 'realtime_summary' }" @click="switchMode('realtime_summary')">
              读取会议实时总结
            </button>
            <button class="btn" :class="{ primary: playbackMode === 'carousel_summary' }" @click="switchMode('carousel_summary')">
              轮播会议总结
            </button>
            <button class="btn" :class="{ primary: playbackMode === 'reflection_qa' }" @click="switchMode('reflection_qa')">
              会议反思
            </button>
          </div>
          <div class="script-box" v-if="playbackMode === 'carousel_summary'">
            <div class="actions">
              <button class="btn" :class="{ primary: carouselScope === 'single' }" @click="setCarouselScope('single')">
                仅播放当前新闻
              </button>
              <button class="btn" :class="{ primary: carouselScope === 'loop' }" @click="setCarouselScope('loop')">
                循环播放已开启新闻
              </button>
              <button class="btn" :disabled="queueItems.length <= 1" @click="playPrev">上一条</button>
              <button class="btn" :disabled="queueItems.length <= 1" @click="playNext">下一条</button>
              <button class="btn primary" @click="refreshQueue">刷新队列</button>
            </div>
          </div>

          <div class="script-box" v-if="playbackMode === 'realtime_summary'">
            <div class="actions">
              <button class="btn primary" @click="loadRealtimeSummary">读取实时记录</button>
              <button class="btn" @click="openFeishuPanel">绑定飞书会议</button>
              <span class="status-text">数据源：{{ liveSourceLabel }}</span>
            </div>
            <div class="realtime-preview">
              <p class="realtime-preview-title">实时小结预览</p>
              <p class="realtime-preview-empty" v-if="!liveRecords.length">当前暂无实时小结，先点击“读取实时记录”。</p>
              <ul class="realtime-preview-list" v-else>
                <li v-for="(item, idx) in liveRecords.slice(0, 6)" :key="`${idx}-${item.timestamp}`">
                  {{ item.content }}
                </li>
              </ul>
            </div>
          </div>

          <div class="script-box" v-if="playbackMode === 'reflection_qa'">
            <div class="page-actions">
              <label style="flex: 1">
                <span>选择新闻</span>
                <select class="field" :value="String(selectedReflectionReportId || '')" @change="onReflectionReportChanged">
                  <option value="" disabled>请选择新闻</option>
                  <option v-for="item in reflectionReportOptions" :key="item.id" :value="String(item.id)">
                    {{ item.id }} - {{ item.title }}
                  </option>
                </select>
              </label>
            </div>
            <div class="actions">
              <button class="btn primary" :disabled="!selectedReflectionReportId || isLoadingReflection" @click="loadReflection">
                {{ isLoadingReflection ? '调取中...' : '调取反思内容' }}
              </button>
              <span class="status-text">反思内容在新闻编辑页查看与维护</span>
            </div>
          </div>
        </div>

        <div class="script-box layer-card">
          <h2>数字人测试</h2>
          <div class="actions">
            <button class="btn" @click="loadAvatarToken">从后端读取数字人配置</button>
            <button class="btn dark" @click="toggleDebugAvatar">
              {{ debugAvatarEnabled ? '不加载数字人' : '加载数字人' }}
            </button>
          </div>
          <div class="actions">
          <button
            class="btn dark"
            :disabled="
              playbackMode === 'realtime_summary' ||
              isPreparingScript ||
              (report.renderMode === 'audio' ? !report.audioPcmBase64 : !report.scriptFinal)
            "
            @click="startBroadcast"
          >
            {{ playbackMode === 'realtime_summary' ? '实时模式静默待机' : '立即播报当前' }}
          </button>
          <span class="status-text">数字人状态：{{ avatarStatus }}</span>
          </div>
        </div>

        <div class="script-box layer-card">
          <div class="actions" style="justify-content: space-between">
            <h2 style="margin: 0">数字人高级配置（默认隐藏）</h2>
            <button class="btn ghost" @click="toggleFixedConfigSection">
              {{ showFixedConfigSection ? '隐藏固定参数区' : '显示固定参数区' }}
            </button>
          </div>

          <div v-if="showFixedConfigSection">
            <label>
              <span>token（必填）</span>
              <textarea v-model="avatarForm.token" class="field textarea" placeholder="粘贴百度曦灵 token" />
            </label>
            <div class="page-actions">
              <label style="flex: 1">
                <span>figureId（必填）</span>
                <input v-model="avatarForm.figureId" class="field" placeholder="例如 211868" />
              </label>
              <label style="flex: 1">
                <span>cameraId（可选）</span>
                <input v-model="avatarForm.cameraId" class="field" placeholder="可选" />
              </label>
            </div>
            <div class="page-actions">
              <label style="flex: 1">
                <span>分辨率宽</span>
                <input v-model.number="avatarForm.resolutionWidth" class="field" type="number" min="400" step="2" />
              </label>
              <label style="flex: 1">
                <span>分辨率高</span>
                <input v-model.number="avatarForm.resolutionHeight" class="field" type="number" min="400" step="2" />
              </label>
            </div>
          </div>

          <div class="actions">
            <button class="btn" @click="saveManualConfig">仅保存数字人参数</button>
            <button class="btn dark" @click="loadAvatarInDebug">加载数字人（当前调试页）</button>
            <button class="btn" @click="clearManualConfig">清空手动配置</button>
          </div>
        </div>
      </div>
    </section>

    <div class="panel-mask" v-if="showFeishuPanel" @click.self="closeFeishuPanel">
      <section class="panel-card">
        <h3>绑定飞书会议（实时总结）</h3>
        <p class="panel-desc">输入会议链接后，可先诊断权限，再导入会议内容。</p>
        <label>
          <span>飞书会议链接</span>
          <input
            v-model.trim="feishuLinkInput"
            class="field"
            placeholder="https://vc.feishu.cn/j/151322082 或 https://tpc.feishu.cn/minutes/xxxx"
          />
        </label>
        <label>
          <span>回溯天数</span>
          <input v-model.number="feishuLookbackDays" class="field" type="number" min="1" max="180" />
        </label>
        <p class="panel-hint" v-if="feishuBindResult">{{ feishuBindResult }}</p>
        <div class="panel-actions">
          <button class="btn ghost" :disabled="feishuWorking" @click="closeFeishuPanel">取消</button>
          <button class="btn" :disabled="feishuWorking" @click="runFeishuDiagnose">
            {{ feishuWorking ? '处理中...' : '先诊断权限' }}
          </button>
          <button class="btn primary" :disabled="feishuWorking" @click="bindAndImportFeishu">
            {{ feishuWorking ? '处理中...' : '绑定并导入' }}
          </button>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import BaiduAvatarPlayer from '../components/BaiduAvatarPlayer.vue';
import {
  diagnoseFeishuMeeting,
  getAvatarToken,
  getFeishuLiveRecords,
  getPlaybackMode,
  getPlaybackQueue,
  getReportReflection,
  importFeishuMeeting,
  inspectFeishuMeeting,
  listReports,
  prepareReportTranslation,
  synthesizeScriptAudio,
  translateScript,
  type ReportListItem,
  type FeishuLiveRecordItem,
  type PlaybackQueueItem,
  type ReflectionItem,
  updatePlaybackMode,
} from '../services/api';

interface DebugReport {
  id: string;
  title: string;
  speaker: string;
  scriptFinal: string;
  renderMode: 'text' | 'audio';
  audioPcmBase64: string;
}

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
type CarouselScope = 'single' | 'loop';

const AVATAR_POSITION_V2 = '{"location":{"top":36,"left":710,"width":608,"height":1080}}';
const localConfigKey = 'baidu_avatar_manual_config';
const activeConfigKey = 'baidu_avatar_active_config';
const localLanguageKey = 'playback_language_selection';
const queueVersionKey = 'playback_queue_version';
const runtimeVersionKey = 'playback_runtime_version';
const runtimeBroadcastChannel = 'playback_runtime_channel';
const focusReportIdKey = 'playback_focus_report_id';
const fixedConfigCollapsedKey = 'playback_fixed_config_collapsed';
const FEISHU_MEETING_LINK_KEY = 'playback_feishu_meeting_link';

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

const avatarStatus = ref('等待连接');
const configInfo = ref('');
const debugAvatarEnabled = ref(false);
const isPreparingScript = ref(false);
const showFixedConfigSection = ref(true);

const playbackMode = ref<PlaybackMode>('carousel_summary');
const carouselScope = ref<CarouselScope>('loop');
const selectedReflectionReportId = ref<number | null>(null);
const selectedRealtimeReportId = ref<number | null>(null);

const queueItems = ref<PlaybackQueueItem[]>([]);
const currentIndex = ref(0);
const selectedLanguageKeys = ref<string[]>(['zh']);
const currentLanguageIndex = ref(0);
const lastRenderSignature = ref('');
const audioCache = ref<Record<string, string>>({});
const textCache = ref<Record<string, { title: string; script: string; highlights: string[] }>>({});
const nonCarouselAudioCache = ref<Record<string, string>>({});

const liveRecords = ref<FeishuLiveRecordItem[]>([]);
const liveSourceLabel = ref('未读取');
const showFeishuPanel = ref(false);
const feishuLinkInput = ref('');
const feishuLookbackDays = ref(30);
const feishuWorking = ref(false);
const feishuBindResult = ref('');
const reflectionItems = ref<ReflectionItem[]>([]);
const reflectionLoadedReportId = ref<number | null>(null);
const reflectionReportOptions = ref<ReportListItem[]>([]);
const isLoadingReflection = ref(false);

const baseAvatarConfig = ref<AvatarConfig | null>(null);
const avatarForm = reactive({
  token: '',
  figureId: '',
  cameraId: '',
  resolutionWidth: 1920,
  resolutionHeight: 1080,
});

const report = reactive<DebugReport>({
  id: '',
  title: '',
  speaker: '',
  scriptFinal: '',
  renderMode: 'text',
  audioPcmBase64: '',
});

const currentLanguage = computed<LanguageOption>(() => {
  const key = selectedLanguageKeys.value[currentLanguageIndex.value];
  return languageOptions.find((x) => x.key === key) || languageOptions[0];
});

const currentLanguageLabel = computed(() => currentLanguage.value.label);
const currentOrderLabel = computed(() => (queueItems.value.length ? currentIndex.value + 1 : 0));
const canOpenImmersive = computed(() => !!(baseAvatarConfig.value?.token && baseAvatarConfig.value?.figureId));
const autoPlayEnabled = computed(() => playbackMode.value !== 'realtime_summary');
const carouselScopeLabel = computed(() => (carouselScope.value === 'single' ? '仅当前新闻' : '循环全部开启新闻'));
const currentModeLabel = computed(() => {
  if (playbackMode.value === 'realtime_summary') return '读取会议实时总结';
  if (playbackMode.value === 'reflection_qa') return '会议反思';
  return '轮播会议总结';
});

const activeAvatarConfig = computed<AvatarConfig | null>(() => {
  // 语言切换时仅切换播报文案/音频，不重建数字人实例。
  return baseAvatarConfig.value;
});

const notifyImmersiveSync = (snapshot: {
  version: string;
  focusReportId: number | null;
  langs: string[];
  mode: PlaybackMode;
  carouselScope: CarouselScope;
  selectedReportId: number | null;
}) => {
  window.localStorage.setItem(runtimeVersionKey, snapshot.version);
  if (typeof window.BroadcastChannel !== 'undefined') {
    try {
      const channel = new window.BroadcastChannel(runtimeBroadcastChannel);
      channel.postMessage({
        type: 'runtime-sync',
        version: snapshot.version,
        focusReportId: snapshot.focusReportId,
        langs: snapshot.langs,
        mode: snapshot.mode,
        carouselScope: snapshot.carouselScope,
        selectedReportId: snapshot.selectedReportId,
      });
      channel.close();
    } catch {
      // 部分浏览器/策略下 BroadcastChannel 可能不可用，已由 localStorage 事件兜底。
    }
  }
};

const publishRuntimeSnapshot = () => {
  const focusReportId = Number(report.id || '0');
  const modeSelectedReportId =
    playbackMode.value === 'realtime_summary' ? selectedRealtimeReportId.value : selectedReflectionReportId.value;
  const snapshot = {
    version: String(Date.now()),
    focusReportId: focusReportId > 0 ? focusReportId : null,
    langs: [...selectedLanguageKeys.value],
    mode: playbackMode.value,
    carouselScope: carouselScope.value,
    selectedReportId: modeSelectedReportId,
  };

  if (focusReportId > 0) {
    window.localStorage.setItem(focusReportIdKey, String(focusReportId));
  } else {
    window.localStorage.removeItem(focusReportIdKey);
  }
  window.localStorage.setItem(localLanguageKey, JSON.stringify(selectedLanguageKeys.value));
  notifyImmersiveSync(snapshot);
};

const getCurrentQueueItem = () => queueItems.value[currentIndex.value];

const resolveLocalizedPayload = (item: PlaybackQueueItem, lang: LanguageOption) => {
  const localized = item.localized?.[lang.key];
  const renderMode = (localized?.render_mode ||
    (lang.key === 'zh' || lang.key === 'en' ? 'text' : 'audio')) as 'text' | 'audio';
  const script = String(localized?.script_final || '').trim();
  const cacheKey = `${item.id}:${lang.key}`;
  const audioPcmBase64 = String(localized?.audio_pcm_base64 || audioCache.value[cacheKey] || '').trim();
  const audioReady = Boolean(localized?.audio_ready ?? (renderMode === 'audio' ? !!audioPcmBase64 : true));
  return { script, renderMode, audioPcmBase64, audioReady };
};

const buildRenderSignature = (item: PlaybackQueueItem, languageKey: string) =>
  `${item.id}|${languageKey}|${item.script_final}|${JSON.stringify(item.localized || {})}|${playbackMode.value}|${carouselScope.value}`;

const fetchAudioForReportLanguage = async (reportId: number, languageKey: string): Promise<string> => {
  const cacheKey = `${reportId}:${languageKey}`;
  if (audioCache.value[cacheKey]) return audioCache.value[cacheKey];
  const data = await getPlaybackQueue({ includeAudio: true, langs: [languageKey], reportId });
  const item = (data.items || [])[0];
  const audio = String(item?.localized?.[languageKey]?.audio_pcm_base64 || '').trim();
  if (audio) audioCache.value[cacheKey] = audio;
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
    report.title = '暂无开启自动播报的新闻';
    report.speaker = '';
    report.scriptFinal = '';
    report.renderMode = 'text';
    report.audioPcmBase64 = '';
    isPreparingScript.value = false;
    lastRenderSignature.value = '';
    return false;
  }

  const signature = buildRenderSignature(current, currentLanguage.value.key);
  if (!force && signature === lastRenderSignature.value) return true;
  isPreparingScript.value = true;
  try {
    const languageKey = currentLanguage.value.key;
    let localized = resolveLocalizedPayload(current, currentLanguage.value);
    if (!localized.script) {
      await prepareReportTranslation(current.id, languageKey);
      const refreshed = await refreshSingleQueueItem(
        current.id,
        languageKey,
        localized.renderMode === 'audio',
      );
      if (refreshed) {
        localized = resolveLocalizedPayload(refreshed, currentLanguage.value);
      }
    }

    report.id = String(current.id || '');
    report.title = current.title || '';
    report.speaker = current.speaker || '';
    report.scriptFinal = localized.script;
    report.renderMode = localized.renderMode;
    report.audioPcmBase64 = localized.audioPcmBase64;

    if (!localized.script) {
      throw new Error('当前语言文案未就绪');
    }
    if (localized.renderMode === 'audio' && !localized.audioPcmBase64) {
      const audio = await fetchAudioForReportLanguage(current.id, languageKey);
      if (audio) {
        report.audioPcmBase64 = audio;
      } else {
        await prepareReportTranslation(current.id, languageKey);
        const refreshed = await refreshSingleQueueItem(current.id, languageKey, true);
        const reloaded = refreshed ? resolveLocalizedPayload(refreshed, currentLanguage.value) : localized;
        report.audioPcmBase64 = reloaded.audioPcmBase64 || '';
        if (!report.audioPcmBase64.trim()) {
          throw new Error('当前语言音频未就绪');
        }
      }
    }

    lastRenderSignature.value = signature;
    isPreparingScript.value = false;
    return true;
  } catch (e: any) {
    isPreparingScript.value = false;
    configInfo.value = `文案准备失败：${String(e.message || e)}`;
    return false;
  }
};

const applyRealtimeSummary = async (): Promise<boolean> => {
  try {
    const lines = liveRecords.value.map((x) => x.content.trim()).filter(Boolean);
    if (!lines.length) {
      report.id = 'realtime';
      report.title = '会议实时总结（暂无数据）';
      report.speaker = '会议记录';
      report.scriptFinal = '';
      report.renderMode = 'text';
      report.audioPcmBase64 = '';
      return false;
    }

    report.id = 'realtime';
    report.title = '会议实时总结';
    report.speaker = liveRecords.value[0]?.speaker || '会议记录';
    report.scriptFinal = lines.join('。') + '。';
    report.renderMode = 'text';
    report.audioPcmBase64 = '';
    return true;
  } catch (e: any) {
    configInfo.value = `实时总结准备失败：${String(e.message || e)}`;
    return false;
  }
};

const applyReflectionSummary = async (): Promise<boolean> => {
  try {
    if (!selectedReflectionReportId.value) {
      report.id = '';
      report.title = '反思建议（未就绪）';
      report.speaker = '';
      report.scriptFinal = '请先选择新闻并调取反思内容。';
      report.renderMode = 'text';
      report.audioPcmBase64 = '';
      return false;
    }

    const targetId = selectedReflectionReportId.value;
    if (reflectionLoadedReportId.value !== targetId) {
      reflectionItems.value = [];
    }
    if (!reflectionItems.value.length) {
      try {
        const data = await getReportReflection(targetId);
        reflectionItems.value = data.reflections || [];
        reflectionLoadedReportId.value = targetId;
      } catch {
        reflectionItems.value = [];
        reflectionLoadedReportId.value = null;
      }
    }
    if (!reflectionItems.value.length) {
      report.id = '';
      report.title = '反思建议（未就绪）';
      report.speaker = '';
      report.scriptFinal = '当前新闻暂无反思内容，请先在新闻编辑页生成并保存。';
      report.renderMode = 'text';
      report.audioPcmBase64 = '';
      return false;
    }

    const target = queueItems.value.find((x) => x.id === selectedReflectionReportId.value);
    const reflectionTexts = reflectionItems.value.map((x) => x.text).filter(Boolean);
    const baseTitle = `${target?.title || '会议内容'}｜反思`;
    const baseScript = reflectionTexts.map((x, idx) => `第${idx + 1}条建议：${x}`).join('。');
    const payload = await translateNonCarouselPayload(`reflection:${targetId}:${baseScript}`, {
      title: baseTitle,
      script: baseScript,
      highlights: reflectionTexts.slice(0, 2),
    });
    const audioPayload = await resolveNonCarouselAudio(`reflection:${targetId}:${payload.script}`, payload.script);

    report.id = String(selectedReflectionReportId.value);
    report.title = payload.title;
    report.speaker = target?.speaker || '复盘教练';
    report.scriptFinal = payload.script;
    report.renderMode = audioPayload.renderMode;
    report.audioPcmBase64 = audioPayload.audioPcmBase64;
    return true;
  } catch (e: any) {
    configInfo.value = `反思内容准备失败：${String(e.message || e)}`;
    return false;
  }
};

const applyCurrentModeReport = async (force = false): Promise<boolean> => {
  if (playbackMode.value === 'realtime_summary') {
    return applyRealtimeSummary();
  }
  if (playbackMode.value === 'reflection_qa') {
    return applyReflectionSummary();
  }
  return applyCarouselReport(force);
};

const playCurrentOnPlayer = () => {
  if (isPreparingScript.value) return;
  if (report.renderMode === 'audio') {
    if (!report.audioPcmBase64.trim()) return;
    (playerRef.value as any)?.speakAudio?.(report.audioPcmBase64);
    return;
  }
  if (!report.scriptFinal.trim()) return;
  (playerRef.value as any)?.speakText?.(report.scriptFinal);
};

const startBroadcast = () => {
  if (playbackMode.value === 'realtime_summary') {
    configInfo.value = '实时总结模式下数字人保持静默待机，不进行口播。';
    return;
  }
  playCurrentOnPlayer();
};

const refreshQueue = async () => {
  const currentReportId = Number(report.id || '0');
  try {
    const data = await getPlaybackQueue();
    queueItems.value = data.items || [];
    if (!queueItems.value.length) {
      currentIndex.value = 0;
      await applyCurrentModeReport(true);
      return;
    }

    const preferredId = Number(route.query.id || '0');
    const currentIndexFromQueue = currentReportId ? queueItems.value.findIndex((x) => x.id === currentReportId) : -1;
    const preferredIndex = preferredId ? queueItems.value.findIndex((x) => x.id === preferredId) : -1;
    currentIndex.value = currentIndexFromQueue >= 0 ? currentIndexFromQueue : preferredIndex >= 0 ? preferredIndex : 0;

    if (!selectedReflectionReportId.value) {
      selectedReflectionReportId.value = queueItems.value[0]?.id || null;
    }

    if (currentLanguageIndex.value >= selectedLanguageKeys.value.length) currentLanguageIndex.value = 0;
    await applyCurrentModeReport();
  } catch {
    queueItems.value = [];
    currentIndex.value = 0;
    report.id = '';
    report.title = '自动播报队列加载失败';
    report.speaker = '';
    report.scriptFinal = '';
    report.audioPcmBase64 = '';
    isPreparingScript.value = false;
  }
};

const loadRealtimeSummary = async () => {
  try {
    const data = await getFeishuLiveRecords(20, selectedRealtimeReportId.value);
    liveRecords.value = data.records || [];
    liveSourceLabel.value = data.source || 'unknown';
    await applyRealtimeSummary();
  } catch (e: any) {
    configInfo.value = `读取实时总结失败：${String(e.message || e)}`;
  }
};

const openFeishuPanel = () => {
  feishuBindResult.value = '';
  feishuLinkInput.value = window.localStorage.getItem(FEISHU_MEETING_LINK_KEY) || feishuLinkInput.value;
  showFeishuPanel.value = true;
};

const closeFeishuPanel = () => {
  if (feishuWorking.value) return;
  showFeishuPanel.value = false;
};

const runFeishuDiagnose = async () => {
  const meetingUrl = feishuLinkInput.value.trim();
  if (!meetingUrl) {
    feishuBindResult.value = '请先输入飞书会议链接';
    return;
  }
  feishuWorking.value = true;
  try {
    const lookbackDays = Math.max(1, Math.min(180, Number(feishuLookbackDays.value) || 30));
    const diagnose = await diagnoseFeishuMeeting({
      meeting_url: meetingUrl,
      lookback_days: lookbackDays,
    });
    const passed = diagnose.steps.filter((x) => x.ok).length;
    feishuBindResult.value = diagnose.ok
      ? `诊断通过（${passed}/${diagnose.steps.length}），可导入。`
      : `诊断未通过（${passed}/${diagnose.steps.length}）：${diagnose.suggestion}`;
    window.localStorage.setItem(FEISHU_MEETING_LINK_KEY, meetingUrl);
  } catch (e: any) {
    feishuBindResult.value = `诊断失败：${String(e.message || e)}`;
  } finally {
    feishuWorking.value = false;
  }
};

const bindAndImportFeishu = async () => {
  const meetingUrl = feishuLinkInput.value.trim();
  if (!meetingUrl) {
    feishuBindResult.value = '请先输入飞书会议链接';
    return;
  }
  feishuWorking.value = true;
  try {
    const lookbackDays = Math.max(1, Math.min(180, Number(feishuLookbackDays.value) || 30));
    const inspect = await inspectFeishuMeeting({
      meeting_url: meetingUrl,
      lookback_days: lookbackDays,
    });
    if (!inspect.total) {
      feishuBindResult.value = '未查询到会议记录，请检查链接或回溯天数。';
      return;
    }
    const imported = await importFeishuMeeting({
      meeting_url: meetingUrl,
      lookback_days: lookbackDays,
      auto_generate: true,
      auto_enable_playback: false,
    });
    const importedReportId = Number(imported.items?.find((x) => (x.report_id || 0) > 0)?.report_id || 0);
    if (importedReportId > 0) {
      selectedRealtimeReportId.value = importedReportId;
    }
    feishuBindResult.value = imported.message;
    window.localStorage.setItem(FEISHU_MEETING_LINK_KEY, meetingUrl);
    await loadRealtimeSummary();
    await refreshQueue();
    configInfo.value = `飞书会议已绑定并导入：${imported.message}`;
  } catch (e: any) {
    feishuBindResult.value = `导入失败：${String(e.message || e)}`;
  } finally {
    feishuWorking.value = false;
  }
};

const loadReflectionReportOptions = async () => {
  const merged: ReportListItem[] = [];
  const pageSize = 100;
  let page = 1;
  while (page <= 20) {
    const data = await listReports(page, pageSize);
    const rows = data.items || [];
    merged.push(...rows);
    if (rows.length < pageSize) break;
    page += 1;
  }
  reflectionReportOptions.value = merged;
  const exists = merged.some((x) => x.id === selectedReflectionReportId.value);
  if ((!selectedReflectionReportId.value || !exists) && merged.length) {
    selectedReflectionReportId.value = merged[0].id;
  }
};

const loadReflection = async () => {
  if (!selectedReflectionReportId.value) {
    configInfo.value = '请先选择一条新闻再调取反思内容';
    return;
  }
  isLoadingReflection.value = true;
  configInfo.value = '正在调取反思内容，请稍候...';
  try {
    const data = await getReportReflection(selectedReflectionReportId.value);
    reflectionItems.value = data.reflections || [];
    reflectionLoadedReportId.value = selectedReflectionReportId.value;
    await applyReflectionSummary();
    configInfo.value = `反思内容已调取（${reflectionItems.value.length} 条）`;
  } catch (e: any) {
    reflectionLoadedReportId.value = null;
    configInfo.value = `反思内容调取失败：${String(e.message || e)}`;
  } finally {
    isLoadingReflection.value = false;
  }
};

const onReflectionReportChanged = async (event: Event) => {
  const value = Number((event.target as HTMLSelectElement).value || '0');
  selectedReflectionReportId.value = value || null;
  reflectionItems.value = [];
  reflectionLoadedReportId.value = null;
  await applyReflectionSummary();
};

const saveMode = async (): Promise<boolean> => {
  try {
    const selectedReportId =
      playbackMode.value === 'realtime_summary' ? selectedRealtimeReportId.value : selectedReflectionReportId.value;
    const result = await updatePlaybackMode({
      mode: playbackMode.value,
      carousel_scope: carouselScope.value,
      selected_report_id: selectedReportId,
    });
    playbackMode.value = result.mode;
    carouselScope.value = result.carousel_scope;
    if (result.mode === 'realtime_summary') {
      selectedRealtimeReportId.value = result.selected_report_id;
    } else if (result.mode === 'reflection_qa') {
      selectedReflectionReportId.value = result.selected_report_id;
    }
    return true;
  } catch (e: any) {
    configInfo.value = `播放模式保存失败：${String(e.message || e)}`;
    return false;
  }
};

const switchMode = async (mode: PlaybackMode) => {
  playbackMode.value = mode;
  if (mode === 'realtime_summary') {
    await loadRealtimeSummary();
    return;
  }
  if (mode === 'reflection_qa') {
    await loadReflectionReportOptions();
    reflectionItems.value = [];
    await applyReflectionSummary();
    return;
  }
  await refreshQueue();
};

const setCarouselScope = async (scope: CarouselScope) => {
  carouselScope.value = scope;
  await applyCurrentModeReport(true);
};

const playNext = async () => {
  if (!queueItems.value.length) return;
  currentIndex.value = (currentIndex.value + 1) % queueItems.value.length;
  currentLanguageIndex.value = 0;
  await applyCarouselReport(true);
};

const playPrev = async () => {
  if (!queueItems.value.length) return;
  currentIndex.value = (currentIndex.value - 1 + queueItems.value.length) % queueItems.value.length;
  currentLanguageIndex.value = 0;
  await applyCarouselReport(true);
};

const getPlaySignature = () => {
  const audioSign = `${report.audioPcmBase64.length}:${report.audioPcmBase64.slice(0, 36)}`;
  return `${report.id}|${report.renderMode}|${report.scriptFinal}|${audioSign}|${playbackMode.value}`;
};

const handleBroadcastFinished = async () => {
  if (playbackMode.value !== 'carousel_summary') {
    return;
  }
  if (!queueItems.value.length || isPreparingScript.value) return;
  const previousSignature = getPlaySignature();

  if (selectedLanguageKeys.value.length > 1) {
    if (currentLanguageIndex.value < selectedLanguageKeys.value.length - 1) {
      currentLanguageIndex.value += 1;
      const ok = await applyCarouselReport();
      if (!ok) return;
      if (getPlaySignature() === previousSignature) {
        window.setTimeout(() => playCurrentOnPlayer(), 420);
      }
      return;
    }
    currentLanguageIndex.value = 0;
  }

  if (carouselScope.value === 'single') {
    const ok = await applyCarouselReport();
    if (!ok) return;
    window.setTimeout(() => playCurrentOnPlayer(), 450);
    return;
  }

  if (queueItems.value.length === 1) {
    const ok = await applyCarouselReport();
    if (!ok) return;
    window.setTimeout(() => playCurrentOnPlayer(), 450);
    return;
  }

  currentIndex.value = (currentIndex.value + 1) % queueItems.value.length;
  const ok = await applyCarouselReport();
  if (!ok) return;
  if (getPlaySignature() === previousSignature) {
    window.setTimeout(() => playCurrentOnPlayer(), 420);
  }
};

const loadAvatarToken = async () => {
  try {
    const data = await getAvatarToken();
    baseAvatarConfig.value = {
      token: data.token,
      figureId: data.figure_id,
      cameraId: data.camera_id,
      resolutionWidth: data.resolution_width ?? 1920,
      resolutionHeight: data.resolution_height ?? 1080,
      ttsLan: 'auto',
      positionV2: AVATAR_POSITION_V2,
      autoChromaKey: true,
      videoBg: '#F3F4FB',
      ttsPer: 'LITE_presenter_female',
      ttsSample: '16000',
      preAlertSec: 120,
    };
    avatarForm.token = data.token ?? '';
    avatarForm.figureId = String(data.figure_id ?? '');
    avatarForm.cameraId = data.camera_id ?? '';
    avatarForm.resolutionWidth = data.resolution_width ?? 1920;
    avatarForm.resolutionHeight = data.resolution_height ?? 1080;
    configInfo.value = '已使用后端配置';
    window.localStorage.setItem(activeConfigKey, JSON.stringify(baseAvatarConfig.value));
  } catch {
    const raw = window.localStorage.getItem(localConfigKey);
    if (raw) {
      try {
        const local = JSON.parse(raw);
        baseAvatarConfig.value = {
          token: String(local.token || ''),
          figureId: String(local.figureId || ''),
          cameraId: local.cameraId ? String(local.cameraId) : undefined,
          resolutionWidth: Number(local.resolutionWidth || 1920),
          resolutionHeight: Number(local.resolutionHeight || 1080),
          ttsLan: 'auto',
          positionV2: AVATAR_POSITION_V2,
          autoChromaKey: true,
          videoBg: '#F3F4FB',
          ttsPer: 'LITE_presenter_female',
          ttsSample: '16000',
          preAlertSec: 120,
        };
        avatarForm.token = baseAvatarConfig.value.token;
        avatarForm.figureId = String(baseAvatarConfig.value.figureId);
        avatarForm.cameraId = baseAvatarConfig.value.cameraId ?? '';
        avatarForm.resolutionWidth = baseAvatarConfig.value.resolutionWidth ?? 1920;
        avatarForm.resolutionHeight = baseAvatarConfig.value.resolutionHeight ?? 1080;
        configInfo.value = '后端未配置，已使用本地配置';
        window.localStorage.setItem(activeConfigKey, JSON.stringify(baseAvatarConfig.value));
        return;
      } catch {
        // 忽略损坏的本地配置。
      }
    }
    baseAvatarConfig.value = null;
    configInfo.value = '请填写 token 和 figureId 后保存';
  }
};

const saveManualConfig = (): boolean => {
  const token = avatarForm.token.trim();
  const figureId = avatarForm.figureId.trim();
  if (!token || !figureId) {
    configInfo.value = 'token 和 figureId 为必填';
    return false;
  }

  const conf: AvatarConfig = {
    token,
    figureId,
    cameraId: avatarForm.cameraId.trim() || undefined,
    resolutionWidth: Number(avatarForm.resolutionWidth) || 1920,
    resolutionHeight: Number(avatarForm.resolutionHeight) || 1080,
    ttsLan: 'auto',
    positionV2: AVATAR_POSITION_V2,
    autoChromaKey: true,
    videoBg: '#F3F4FB',
    ttsPer: 'LITE_presenter_female',
    ttsSample: '16000',
    preAlertSec: 120,
  };
  baseAvatarConfig.value = conf;
  window.localStorage.setItem(localConfigKey, JSON.stringify(conf));
  window.localStorage.setItem(activeConfigKey, JSON.stringify(conf));
  configInfo.value = '配置已保存';
  return true;
};

const persistAllConfig = async (applyRuntime: boolean): Promise<boolean> => {
  const savedAvatar = saveManualConfig();
  if (!savedAvatar) return false;

  if (!selectedLanguageKeys.value.length) {
    selectedLanguageKeys.value = ['zh'];
  }
  window.localStorage.setItem(localLanguageKey, JSON.stringify(selectedLanguageKeys.value));
  if (currentLanguageIndex.value >= selectedLanguageKeys.value.length) {
    currentLanguageIndex.value = 0;
  }

  const modeSaved = await saveMode();
  if (!modeSaved) return false;

  await refreshQueue();
  await loadReflectionReportOptions();
  if (playbackMode.value === 'realtime_summary') {
    await loadRealtimeSummary();
  } else if (playbackMode.value === 'reflection_qa') {
    await applyReflectionSummary();
  }

  const applied = await applyCurrentModeReport(true);
  if (!applied) return false;
  if (applyRuntime) {
    publishRuntimeSnapshot();
    // 立刻执行时主动打断并播放新内容；实时总结模式保持静默待机。
    if (playbackMode.value !== 'realtime_summary') {
      window.setTimeout(() => playCurrentOnPlayer(), 80);
    }
    configInfo.value = '已保存并执行全页面配置（数字人参数/语言/模式/内容），沉浸式页已同步';
  } else {
    configInfo.value = '已保存全页面配置（数字人参数/语言/模式/内容）';
  }
  return true;
};

const saveAllConfig = async () => {
  await persistAllConfig(false);
};

const saveConfigAndApply = async () => {
  await persistAllConfig(true);
};

const loadAvatarInDebug = async () => {
  if (!baseAvatarConfig.value?.token || !baseAvatarConfig.value?.figureId) {
    configInfo.value = '请先保存有效的 token 和 figureId，再加载数字人。';
    return;
  }
  window.localStorage.setItem(activeConfigKey, JSON.stringify(baseAvatarConfig.value));
  if (!debugAvatarEnabled.value) {
    debugAvatarEnabled.value = true;
    await nextTick();
  }
  (playerRef.value as any)?.loadAvatar?.();
  configInfo.value = '已在调试页加载数字人';
};

const toggleDebugAvatar = async () => {
  if (debugAvatarEnabled.value) {
    (playerRef.value as any)?.unloadAvatar?.();
    debugAvatarEnabled.value = false;
    return;
  }
  debugAvatarEnabled.value = true;
  await nextTick();
  (playerRef.value as any)?.loadAvatar?.();
};

const toggleFixedConfigSection = () => {
  showFixedConfigSection.value = !showFixedConfigSection.value;
  window.localStorage.setItem(fixedConfigCollapsedKey, showFixedConfigSection.value ? '0' : '1');
};

const clearManualConfig = () => {
  window.localStorage.removeItem(localConfigKey);
  window.localStorage.removeItem(activeConfigKey);
  avatarForm.token = '';
  avatarForm.figureId = '';
  avatarForm.cameraId = '';
  avatarForm.resolutionWidth = 1920;
  avatarForm.resolutionHeight = 1080;
  baseAvatarConfig.value = null;
  configInfo.value = '手动配置已清空';
};

const toggleLanguage = async (languageKey: string, event: Event) => {
  const target = event.target as HTMLInputElement | null;
  const checked = Boolean(target?.checked);
  const exists = selectedLanguageKeys.value.includes(languageKey);

  if (checked && !exists) {
    selectedLanguageKeys.value.push(languageKey);
  }

  if (!checked && exists) {
    if (selectedLanguageKeys.value.length === 1) {
      if (target) target.checked = true;
      configInfo.value = '至少保留一种播报语言';
      return;
    }
    selectedLanguageKeys.value = selectedLanguageKeys.value.filter((x) => x !== languageKey);
  }

  if (currentLanguageIndex.value >= selectedLanguageKeys.value.length) {
    currentLanguageIndex.value = 0;
  }

  currentLanguageIndex.value = 0;
  await applyCurrentModeReport(true);
};

const openImmersivePage = async () => {
  if (!baseAvatarConfig.value?.token || !baseAvatarConfig.value?.figureId) {
    configInfo.value = '请先确保 token 和 figureId 已配置成功，再打开沉浸式页面。';
    return;
  }

  const id =
    playbackMode.value === 'reflection_qa'
      ? selectedReflectionReportId.value || Number(report.id || '0') || 0
      : Number(report.id || '0') || 0;

  const params = new URLSearchParams();
  params.set('t', String(Date.now()));
  params.set('langs', selectedLanguageKeys.value.join(','));
  params.set('mode', playbackMode.value);
  const immersiveUrl = `/immersive/${id}?${params.toString()}`;

  // 先同步打开目标页面，确保用户手势生效并避免被拦截。
  const immersiveWindow = window.open(immersiveUrl, 'immersive-player');
  if (!immersiveWindow) {
    configInfo.value = '浏览器拦截了新窗口，请允许弹窗后重试。';
    return;
  }

  // 配置保存失败也不关闭沉浸式页，避免“点了没反应”。
  const savedAll = await persistAllConfig(false);
  if (!savedAll) {
    configInfo.value = '沉浸式页面已打开，但本次配置保存失败，请检查后端连接后重试保存。';
    return;
  }
  if (debugAvatarEnabled.value) {
    (playerRef.value as any)?.unloadAvatar?.();
    debugAvatarEnabled.value = false;
  }
};

const loadLanguageSelection = () => {
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

const loadMode = async () => {
  try {
    const modeState = await getPlaybackMode();
    playbackMode.value = modeState.mode;
    carouselScope.value = modeState.carousel_scope;
    if (modeState.mode === 'realtime_summary') {
      selectedRealtimeReportId.value = modeState.selected_report_id;
    } else if (modeState.mode === 'reflection_qa') {
      selectedReflectionReportId.value = modeState.selected_report_id;
    }
  } catch {
    playbackMode.value = 'carousel_summary';
    carouselScope.value = 'loop';
    selectedReflectionReportId.value = null;
    selectedRealtimeReportId.value = null;
  }
};

let queuePollTimer: number | null = null;
const onStorageChanged = (event: StorageEvent) => {
  if (event.key === queueVersionKey) {
    refreshQueue();
    loadReflectionReportOptions();
  }
};

onMounted(async () => {
  const collapsed = window.localStorage.getItem(fixedConfigCollapsedKey) === '1';
  showFixedConfigSection.value = !collapsed;
  loadLanguageSelection();
  feishuLinkInput.value = window.localStorage.getItem(FEISHU_MEETING_LINK_KEY) || '';
  await Promise.all([loadMode(), refreshQueue(), loadAvatarToken(), loadReflectionReportOptions()]);
  if (playbackMode.value === 'realtime_summary') {
    await loadRealtimeSummary();
  } else if (playbackMode.value === 'reflection_qa') {
    await applyReflectionSummary();
  }

  window.addEventListener('storage', onStorageChanged);
  queuePollTimer = window.setInterval(() => {
    if (playbackMode.value === 'carousel_summary') {
      refreshQueue();
    }
  }, 6000);
});

onUnmounted(() => {
  window.removeEventListener('storage', onStorageChanged);
  if (queuePollTimer) {
    window.clearInterval(queuePollTimer);
    queuePollTimer = null;
  }
});
</script>

<style scoped>
.panel-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 8, 18, 0.62);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}

.panel-card {
  width: min(720px, 92vw);
  border-radius: 16px;
  border: 1px solid rgba(90, 132, 255, 0.35);
  background: #071746;
  padding: 20px;
  color: #deebff;
}

.panel-desc {
  margin: 6px 0 14px;
  color: #92abd9;
  font-size: 14px;
}

.panel-hint {
  margin-top: 10px;
  color: #8fc7ff;
  font-size: 13px;
  word-break: break-all;
}

.panel-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.realtime-preview {
  margin-top: 10px;
  border: 1px solid rgba(70, 123, 233, 0.24);
  border-radius: 10px;
  background: rgba(7, 23, 70, 0.36);
  padding: 10px 12px;
}

.realtime-preview-title {
  margin: 0 0 8px;
  font-size: 13px;
  color: #a8c3ef;
}

.realtime-preview-empty {
  margin: 0;
  font-size: 13px;
  color: #89a8df;
}

.realtime-preview-list {
  margin: 0;
  padding-left: 16px;
  display: grid;
  gap: 6px;
  color: #dfebff;
  font-size: 13px;
  line-height: 1.55;
}
</style>
