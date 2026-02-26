<template>
  <main class="meeting-immersive">
    <section class="meeting-stage" :class="{ 'detail-view': activeView === 'detail' }">
      <section class="copy-panel" :class="{ detail: activeView === 'detail' }">
        <p class="quote-mark quote-open" v-if="showQuotes">“</p>
        <p class="content-text" :class="textScaleClass">{{ displayText }}</p>
        <p class="quote-mark quote-close" v-if="showQuotes">”</p>
      </section>

      <div class="actions-row" v-if="activeView === 'summary'">
        <button class="action-btn" @click="showReflections">{{ labels.reflection }}</button>
        <button class="action-btn" @click="showQuestions">{{ labels.question }}</button>
      </div>
      <div class="back-row" v-else>
        <button class="action-btn back-btn" @click="backToSummary">{{ labels.back }}</button>
      </div>

      <div class="avatar-frame" :class="{ detail: activeView === 'detail' }">
        <BaiduAvatarPlayer
          ref="playerRef"
          :config="activeAvatarConfig"
          :script="currentSpeechScript"
          :render-mode="currentRenderMode"
          :audio-pcm-base64="currentAudioPcm"
          :auto-play-when-ready="false"
          :show-toolbar="false"
        />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import BaiduAvatarPlayer from '../components/BaiduAvatarPlayer.vue';
import {
  getAvatarToken,
  getPlaybackQueue,
  getReport,
  getReportQuestions,
  getReportReflection,
  synthesizeScriptAudio,
} from '../services/api';

type RenderMode = 'text' | 'audio';
type ViewMode = 'summary' | 'detail';
type DetailKind = 'questions' | 'reflections';

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

const route = useRoute();
const playerRef = ref<InstanceType<typeof BaiduAvatarPlayer> | null>(null);

const AVATAR_POSITION_V2 = '{"location":{"top":36,"left":710,"width":608,"height":1080}}';
const activeConfigKey = 'baidu_avatar_active_config';
const TEXT_RENDER_LANGUAGE_KEYS = new Set(['zh', 'en']);
const ORDINAL_ZH = ['第一', '第二', '第三', '第四', '第五'];
const ORDINAL_EN = ['First', 'Second', 'Third', 'Fourth', 'Fifth'];

const UI_LABELS: Record<string, { reflection: string; question: string; back: string }> = {
  zh: { reflection: '反思', question: '提问', back: '返回' },
  yue: { reflection: '反思', question: '提問', back: '返回' },
  en: { reflection: 'Reflection', question: 'Question', back: 'Back' },
  ja: { reflection: '振り返り', question: '質問', back: '戻る' },
  id: { reflection: 'Refleksi', question: 'Pertanyaan', back: 'Kembali' },
  ms: { reflection: 'Refleksi', question: 'Soalan', back: 'Kembali' },
  hi: { reflection: 'चिंतन', question: 'प्रश्न', back: 'वापस' },
  th: { reflection: 'สะท้อนคิด', question: 'คำถาม', back: 'กลับ' },
};

const reportId = Number(route.params.id || 0);
const activeView = ref<ViewMode>('summary');
const detailKind = ref<DetailKind>('questions');
const languageKey = ref('zh');

const summaryTitle = ref('会议总结');
const summaryText = ref('');
const summarySpeaker = ref('会议主持人');
const summaryRenderMode = ref<RenderMode>('text');
const summaryAudio = ref('');

const meetingPersona = ref('board_director');
const questions = ref<string[]>([]);
const reflections = ref<string[]>([]);

const detailRender = reactive<{ mode: RenderMode; audio: string }>({
  mode: 'text',
  audio: '',
});

const activeAvatarConfig = ref<AvatarConfig | null>(null);

const detailText = computed(() => {
  const rows = detailKind.value === 'questions' ? questions.value : reflections.value;
  if (!rows.length) {
    return detailKind.value === 'questions' ? '当前会议暂无提问内容。' : '当前会议暂无反思内容。';
  }
  return rows.join('\n\n');
});
const displayText = computed(() => (activeView.value === 'summary' ? summaryText.value : detailText.value));
const contentLength = computed(() => displayText.value.length);
const labels = computed(() => UI_LABELS[languageKey.value] || UI_LABELS.zh);
const showQuotes = computed(() => Boolean(displayText.value.trim()));
const textScaleClass = computed(() => {
  const count = contentLength.value;
  if (count > 420) return 'scale-xs';
  if (count > 300) return 'scale-sm';
  if (count > 180) return 'scale-md';
  return 'scale-lg';
});

const currentSpeechScript = computed(() => {
  if (activeView.value === 'summary') return summaryText.value;
  const rows = detailKind.value === 'questions' ? questions.value : reflections.value;
  if (!rows.length) return detailText.value.replace(/\n/g, '。');

  const isEnglish = languageKey.value === 'en';
  const ordinal = isEnglish ? ORDINAL_EN : ORDINAL_ZH;
  if (detailKind.value === 'questions') {
    return rows
      .map((row, idx) => {
        const o = ordinal[idx] || `${idx + 1}`;
        return isEnglish ? `${o} question, ${row}.` : `${o}个问题，${row}。`;
      })
      .join(' ');
  }
  return rows
    .map((row, idx) => {
      const o = ordinal[idx] || `${idx + 1}`;
      return isEnglish ? `${o} reflection, ${row}.` : `${o}条反思，${row}。`;
    })
    .join(' ');
});
const currentRenderMode = computed<RenderMode>(() => {
  if (activeView.value === 'summary') return summaryRenderMode.value;
  return detailRender.mode;
});
const currentAudioPcm = computed(() => {
  if (activeView.value === 'summary') return summaryAudio.value;
  return detailRender.audio;
});

const parseLanguageKey = () => {
  const langsRaw = String(route.query.langs || '').trim();
  const first = langsRaw.split(',').map((x) => x.trim()).filter(Boolean)[0];
  if (first) {
    languageKey.value = first;
  }
};

const loadAvatarConfig = async () => {
  const localRaw = window.localStorage.getItem(activeConfigKey);
  if (localRaw) {
    try {
      const parsed = JSON.parse(localRaw);
      activeAvatarConfig.value = {
        token: String(parsed.token || ''),
        figureId: String(parsed.figureId || ''),
        cameraId: parsed.cameraId ? String(parsed.cameraId) : undefined,
        resolutionWidth: Number(parsed.resolutionWidth || 1920),
        resolutionHeight: Number(parsed.resolutionHeight || 1080),
        ttsLan: 'auto',
        positionV2: AVATAR_POSITION_V2,
        autoChromaKey: true,
        videoBg: '#F3F4FB',
        ttsPer: 'LITE_presenter_female',
        ttsSample: '16000',
        preAlertSec: 120,
      };
      return;
    } catch {
      // ignore broken local cache and fallback to backend token
    }
  }
  try {
    const tokenData = await getAvatarToken();
    activeAvatarConfig.value = {
      token: tokenData.token,
      figureId: tokenData.figure_id,
      cameraId: tokenData.camera_id,
      resolutionWidth: tokenData.resolution_width ?? 1920,
      resolutionHeight: tokenData.resolution_height ?? 1080,
      ttsLan: 'auto',
      positionV2: AVATAR_POSITION_V2,
      autoChromaKey: true,
      videoBg: '#F3F4FB',
      ttsPer: 'LITE_presenter_female',
      ttsSample: '16000',
      preAlertSec: 120,
    };
  } catch {
    activeAvatarConfig.value = null;
  }
};

const resolveRenderMode = (lang: string): RenderMode => (TEXT_RENDER_LANGUAGE_KEYS.has(lang) ? 'text' : 'audio');

const buildAudioForText = async (text: string, lang: string): Promise<string> => {
  if (!text.trim()) return '';
  const result = await synthesizeScriptAudio({
    script_text: text,
    language_key: lang,
  });
  return String(result.audio_pcm_base64 || '').trim();
};

const loadMeetingData = async () => {
  if (!reportId) {
    return;
  }

  const preferredMode = resolveRenderMode(languageKey.value);
  try {
    const queue = await getPlaybackQueue({ includeAudio: true, langs: [languageKey.value], reportId });
    const item = (queue.items || [])[0];
    if (item) {
      const localized = item.localized?.[languageKey.value];
      summaryTitle.value = String(localized?.title || item.title || '会议总结');
      summarySpeaker.value = String(item.speaker || '会议主持人');
      summaryText.value = String(localized?.script_final || item.script_final || '').trim();
      summaryRenderMode.value = (localized?.render_mode as RenderMode) || preferredMode;
      summaryAudio.value = String(localized?.audio_pcm_base64 || '').trim();
      questions.value = (localized?.questions_final || item.questions_final || []).slice(0, 3).map((x) => String(x || '').trim()).filter(Boolean);
      reflections.value = (localized?.reflections_final || item.reflections_final || []).slice(0, 5).map((x) => String(x || '').trim()).filter(Boolean);
      meetingPersona.value = String(localized?.question_persona || item.question_persona || 'board_director');
      return;
    }
  } catch {
    // fallback to direct APIs when queue is unavailable or report not auto-enabled
  }

  const detail = await getReport(reportId);
  summaryTitle.value = detail.title || '会议总结';
  summarySpeaker.value = detail.speaker || '会议主持人';
  summaryText.value = String(detail.script_final || detail.script_draft || '').trim();
  summaryRenderMode.value = preferredMode;
  summaryAudio.value = '';

  const [questionRes, reflectionRes] = await Promise.all([
    getReportQuestions(reportId, { lang: languageKey.value, persona: detail.question_persona }),
    getReportReflection(reportId, languageKey.value),
  ]);
  questions.value = (questionRes.questions || []).map((x) => String(x.text || '').trim()).filter(Boolean).slice(0, 3);
  reflections.value = (reflectionRes.reflections || []).map((x) => String(x.text || '').trim()).filter(Boolean).slice(0, 5);
  meetingPersona.value = String(questionRes.persona || detail.question_persona || 'board_director');
};

const speakCurrent = async () => {
  const text = currentSpeechScript.value.trim();
  if (!text) return;
  if (currentRenderMode.value === 'audio') {
    if (!currentAudioPcm.value.trim()) {
      detailRender.audio = await buildAudioForText(text, languageKey.value);
    }
    if (currentAudioPcm.value.trim()) {
      (playerRef.value as any)?.speakAudio?.(currentAudioPcm.value);
    }
    return;
  }
  (playerRef.value as any)?.speakText?.(text);
};

const interruptPlayback = () => {
  (playerRef.value as any)?.interrupt?.();
};

const showQuestions = async () => {
  interruptPlayback();
  activeView.value = 'detail';
  detailKind.value = 'questions';
  detailRender.mode = resolveRenderMode(languageKey.value);
  detailRender.audio = '';
  await speakCurrent();
};

const showReflections = async () => {
  interruptPlayback();
  activeView.value = 'detail';
  detailKind.value = 'reflections';
  detailRender.mode = resolveRenderMode(languageKey.value);
  detailRender.audio = '';
  await speakCurrent();
};

const backToSummary = () => {
  interruptPlayback();
  activeView.value = 'summary';
};

onMounted(async () => {
  parseLanguageKey();
  await Promise.all([loadAvatarConfig(), loadMeetingData()]);
  await nextTick();
  (playerRef.value as any)?.loadAvatar?.();
});

onUnmounted(() => {
  interruptPlayback();
});
</script>

<style scoped>
.meeting-immersive {
  width: 100vw;
  height: 100vh;
  margin: 0;
  display: grid;
  place-items: center;
  overflow: hidden;
  background:
    radial-gradient(circle at 72% 40%, rgba(20, 63, 166, 0.18), transparent 44%),
    linear-gradient(161deg, #01040d 0%, #04102a 58%, #06173d 100%);
}

.meeting-stage {
  position: relative;
  width: min(100vw, calc(100vh * 16 / 9));
  aspect-ratio: 16 / 9;
  overflow: hidden;
}

.copy-panel {
  position: absolute;
  left: 16.8%;
  top: 11.8%;
  width: 66.8%;
  height: 52.8%;
  overflow: hidden;
  z-index: 3;
}

.content-text {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.36;
  color: #f4f8ff;
  font-weight: 560;
  overflow: hidden;
}

.content-text.scale-lg {
  font-size: clamp(22px, 1.5vw, 28px);
}

.content-text.scale-md {
  font-size: clamp(20px, 1.35vw, 25px);
}

.content-text.scale-sm {
  font-size: clamp(18px, 1.22vw, 22px);
}

.content-text.scale-xs {
  font-size: clamp(16px, 1.1vw, 20px);
  line-height: 1.25;
}

.quote-mark {
  position: absolute;
  color: #5ea0ff;
  font-size: clamp(30px, 2vw, 38px);
  line-height: 1;
  font-weight: 700;
}

.quote-open {
  left: 0;
  top: -2.2%;
}

.quote-close {
  right: 1.8%;
  bottom: -2.4%;
}

.copy-panel.detail {
  left: 40%;
  top: 23.4%;
  width: 47.5%;
  height: 40.8%;
}

.copy-panel.detail .content-text {
  line-height: 1.36;
}

.actions-row {
  position: absolute;
  left: 50%;
  bottom: 12.8%;
  transform: translateX(-50%);
  display: flex;
  width: 66.8%;
  gap: 18px;
  z-index: 3;
}

.back-row {
  position: absolute;
  right: 15.8%;
  bottom: 12.8%;
  z-index: 4;
}

.action-btn {
  flex: 1;
  height: clamp(52px, 4.2vw, 62px);
  border-radius: 10px;
  border: 1px solid rgba(153, 191, 255, 0.45);
  background: linear-gradient(180deg, rgba(23, 62, 154, 0.38), rgba(15, 36, 90, 0.52));
  color: #f0f6ff;
  font-size: clamp(20px, 1.35vw, 28px);
  font-weight: 520;
  cursor: pointer;
  backdrop-filter: blur(4px);
}

.action-btn:hover {
  border-color: rgba(180, 210, 255, 0.82);
}

.avatar-frame {
  position: absolute;
  left: calc(2.2% - 50px);
  bottom: 0;
  width: 22.2%;
  height: 42%;
  overflow: hidden;
  z-index: 4;
}

.avatar-frame.detail {
  left: calc(-0.4% - 50px);
  width: 47.4%;
  height: 100%;
}

.back-btn {
  width: clamp(160px, 13vw, 210px);
  flex: none;
  font-size: clamp(20px, 1.28vw, 26px);
}

.avatar-frame :deep(.avatar-card) {
  width: 100%;
  height: 100%;
  min-height: 100%;
  gap: 0;
}

.avatar-frame :deep(.avatar-stage) {
  width: 100%;
  height: 100% !important;
  min-height: 100% !important;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.avatar-frame :deep(#digital-human-iframe) {
  width: 100%;
  height: 100%;
  min-height: 100%;
  background: transparent !important;
}

@media (max-width: 900px) {
  .copy-panel {
    left: 11%;
    width: 79%;
    height: 55%;
  }

  .copy-panel.detail {
    left: 40%;
    width: 53%;
    top: 21%;
    height: 47%;
  }

  .content-text.scale-lg {
    font-size: clamp(16px, 2.3vw, 22px);
  }

  .content-text.scale-md {
    font-size: clamp(15px, 2.1vw, 20px);
  }

  .content-text.scale-sm,
  .content-text.scale-xs {
    font-size: clamp(13px, 1.9vw, 18px);
  }

  .actions-row {
    bottom: 12%;
    width: 90%;
    gap: 12px;
  }

  .action-btn {
    font-size: clamp(15px, 2vw, 20px);
    height: 42px;
  }

  .back-row {
    right: 11%;
    bottom: 12%;
  }

  .back-btn {
    width: 138px;
  }

  .avatar-frame {
    width: 30%;
    height: 40.8%;
  }

  .avatar-frame.detail {
    width: 58.8%;
    height: 88.8%;
  }
}
</style>
