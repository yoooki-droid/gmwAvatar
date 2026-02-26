<template>
  <main class="editor-layout">
    <section class="left-pane">
      <h2>内容输入</h2>
      <label>
        <span>新闻标题（必填）</span>
        <input v-model="form.title" class="field" placeholder="请输入新闻标题" />
      </label>
      <label>
        <span>时间（非必填）</span>
        <input v-model="form.meeting_time" type="datetime-local" class="field" />
      </label>
      <label>
        <span>发言人（非必填）</span>
        <input v-model="form.speaker" class="field" placeholder="请输入发言人姓名" />
      </label>
      <label>
        <span>内容（必填）</span>
        <textarea v-model="form.summary_raw" class="field textarea large" placeholder="请输入会议总结内容" />
      </label>
      <label>
        <span>原始语种（自动识别，可手动覆盖）</span>
        <select class="field" v-model="sourceLanguageKey">
          <option v-for="lang in languageOptions" :key="lang.key" :value="lang.key">{{ lang.label }}</option>
        </select>
      </label>
      <label>
        <span>提问人设（用于生成犀利提问）</span>
        <select class="field" v-model="form.question_persona">
          <option v-for="persona in questionPersonaOptions" :key="persona.key" :value="persona.key">{{ persona.label }}</option>
        </select>
      </label>
      <p class="hint">
        {{ sourceLanguageHint }}
      </p>
      <div class="page-actions">
        <button class="btn" :disabled="!prevId" @click="goPrev">上一条</button>
        <button class="btn" :disabled="!nextId" @click="goNext">下一条</button>
        <button class="btn primary" :disabled="!canGenerate || isGenerating" @click="handleGenerate">
          {{ isGenerating ? '生成中...' : 'AI 生成当前语言内容' }}
        </button>
        <button
          class="btn"
          :disabled="!canGenerate || isPreparingLanguages || isGenerating"
          @click="handleRetranslateAll"
        >
          {{ isPreparingLanguages ? '翻译中...' : 'AI 翻译全部语言' }}
        </button>
        <button class="btn dark" :disabled="!canSave" @click="handleSave">保存全部</button>
        <button class="btn dark" :disabled="!canSave" @click="handleSaveAndEnable">保存并播报</button>
      </div>
      <p class="hint">{{ info }}</p>
    </section>

    <section class="right-pane">
      <div class="right-head">
        <h2>AI 输出</h2>
      </div>

      <div class="language-box">
        <h3>多语言预翻译（提前准备）</h3>
        <div class="language-tab-row">
          <button
            class="language-tab"
            v-for="lang in languageOptions"
            :key="lang.key"
            :class="{
              active: currentEditLanguage === lang.key,
              ready: isLanguagePrepared(lang.key),
              translating: isLanguageTranslating(lang.key),
            }"
            :disabled="isLanguageTranslating(lang.key)"
            @click="onLanguageTabClick(lang.key)"
          >
            <span>{{ isSourceLanguage(lang.key) ? `原文（${lang.label}）` : lang.label }}</span>
            <span class="tab-state">{{ getLanguageTabStateText(lang.key) }}</span>
          </button>
        </div>
        <div class="actions">
          <button
            v-if="!isSourceLanguage(currentEditLanguage)"
            class="btn"
            :disabled="!currentLanguageReady || isSavingCurrentLanguage"
            @click="handleSaveCurrentLanguage"
          >
            {{ isSavingCurrentLanguage ? '保存中...' : '仅保存当前语言' }}
          </button>
          <button
            v-if="!isSourceLanguage(currentEditLanguage)"
            class="btn"
            :disabled="isLanguageTranslating(currentEditLanguage) || isGenerating || isPreparingLanguages || !canGenerate"
            @click="handleRetranslateCurrentLanguage"
          >
            {{ isLanguageTranslating(currentEditLanguage) ? '重译中...' : '重新翻译当前语言' }}
          </button>
          <span class="status-text">{{ currentLanguageStatusText }}</span>
        </div>
        <p class="hint">
          点击未准备语言会立即开始翻译，翻译完成后可进入编辑；左侧“翻译全部语言”会按当前主稿重译全部语种。
        </p>
      </div>

      <label v-if="!isSourceLanguage(currentEditLanguage)">
        <span>翻译标题（可修改）</span>
        <input :value="currentTitleValue" class="field" @input="onTitleInput" />
      </label>

      <label>
        <span>口播稿（可修改）</span>
        <textarea :value="currentScriptValue" class="field textarea" @input="onScriptInput" />
      </label>

      <div>
        <h3>Highlights（2条，可修改）</h3>
        <div class="highlight-list">
          <textarea
            :value="currentHighlight1"
            class="field textarea highlight"
            placeholder="亮点 1"
            @input="onHighlightInput(0, $event)"
          />
          <textarea
            :value="currentHighlight2"
            class="field textarea highlight"
            placeholder="亮点 2"
            @input="onHighlightInput(1, $event)"
          />
        </div>
      </div>

      <div>
        <h3>金融专家反思（3~5条，可修改）</h3>
        <div class="highlight-list">
          <textarea
            :value="currentReflection1"
            class="field textarea highlight"
            placeholder="反思建议 1"
            @input="onReflectionInput(0, $event)"
          />
          <textarea
            :value="currentReflection2"
            class="field textarea highlight"
            placeholder="反思建议 2"
            @input="onReflectionInput(1, $event)"
          />
          <textarea
            :value="currentReflection3"
            class="field textarea highlight"
            placeholder="反思建议 3"
            @input="onReflectionInput(2, $event)"
          />
          <textarea
            :value="currentReflection4"
            class="field textarea highlight"
            placeholder="反思建议 4（可选）"
            @input="onReflectionInput(3, $event)"
          />
          <textarea
            :value="currentReflection5"
            class="field textarea highlight"
            placeholder="反思建议 5（可选）"
            @input="onReflectionInput(4, $event)"
          />
        </div>
      </div>

      <div>
        <h3>会议提问（1~3条，可修改）</h3>
        <div class="highlight-list">
          <textarea
            :value="currentQuestion1"
            class="field textarea highlight"
            placeholder="犀利提问 1"
            @input="onQuestionInput(0, $event)"
          />
          <textarea
            :value="currentQuestion2"
            class="field textarea highlight"
            placeholder="犀利提问 2（可选）"
            @input="onQuestionInput(1, $event)"
          />
          <textarea
            :value="currentQuestion3"
            class="field textarea highlight"
            placeholder="犀利提问 3（可选）"
            @input="onQuestionInput(2, $event)"
          />
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  createReport,
  generateReport,
  getReport,
  getReportTranslations,
  listReports,
  retranslateAllLanguages,
  retranslateSingleLanguage,
  updatePlaybackMode,
  updateReport,
  updateReportTranslation,
} from '../services/api';

interface LanguageOption {
  key: string;
  label: string;
}

interface TranslationDraft {
  title: string;
  script_final: string;
  highlights_final: string[];
  reflections_final: string[];
  questions_final: string[];
  question_persona: string;
  reviewed: boolean;
  reviewed_at: string | null;
  status: 'missing' | 'translating' | 'ready' | 'failed';
  render_mode: 'text' | 'audio';
  audio_ready: boolean;
  error: string;
}

const languageOptions: LanguageOption[] = [
  { key: 'zh', label: '中文' },
  { key: 'en', label: '英文' },
  { key: 'yue', label: '粤语' },
  { key: 'ja', label: '日语' },
  { key: 'id', label: '印度尼西亚语' },
  { key: 'ms', label: '马来西亚语' },
  { key: 'hi', label: '印度语' },
  { key: 'th', label: '泰语' },
];

const questionPersonaOptions = [
  { key: 'board_director', label: '独立董事（问责）' },
  { key: 'cro', label: '首席风险官（风险）' },
  { key: 'coo', label: '首席运营官（执行）' },
  { key: 'cfo', label: '首席财务官（财务）' },
  { key: 'strategy', label: '战略顾问（取舍）' },
];

const route = useRoute();
const router = useRouter();

const queueVersionKey = 'playback_queue_version';
const localLanguageKey = 'playback_language_selection';
const focusReportIdKey = 'playback_focus_report_id';
const reportId = ref<number | null>(null);
const reportIds = ref<number[]>([]);
const info = ref('');

const isPreparingLanguages = ref(false);
const isGenerating = ref(false);
const isSavingCurrentLanguage = ref(false);
const isHydrating = ref(false);
const currentEditLanguage = ref<string>('zh');
const sourceLanguageKey = ref<string>('zh');
const loadedSourceLanguage = ref<string>('zh');
const translationMap = reactive<Record<string, TranslationDraft>>({});
let translationPollingTimer: number | null = null;

const form = reactive({
  title: '',
  meeting_time: '',
  speaker: '',
  summary_raw: '',
  script_final: '',
  highlights_final: ['', ''],
  reflections_final: ['', '', '', '', ''],
  questions_final: ['', '', ''],
  question_persona: 'board_director',
});

const isSourceLanguage = (languageKey: string) => languageKey === sourceLanguageKey.value;

const selectableLanguages = computed(() => languageOptions.filter((x) => !isSourceLanguage(x.key)));

const currentTranslation = computed<TranslationDraft | null>(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return null;
  return translationMap[currentEditLanguage.value] || null;
});

const canGenerate = computed(() => !!form.title.trim() && !!form.summary_raw.trim());
const canSave = computed(() => !!form.title.trim() && !!form.summary_raw.trim());

const currentOrderIndex = computed(() => {
  if (!reportId.value) return -1;
  return reportIds.value.findIndex((id) => id === reportId.value);
});

const prevId = computed(() => {
  if (currentOrderIndex.value <= 0) return null;
  return reportIds.value[currentOrderIndex.value - 1] || null;
});

const nextId = computed(() => {
  if (currentOrderIndex.value < 0 || currentOrderIndex.value >= reportIds.value.length - 1) return null;
  return reportIds.value[currentOrderIndex.value + 1] || null;
});

const currentLanguageStatusText = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return '当前为原文主稿';
  if (isLanguageTranslating(currentEditLanguage.value)) return '当前语言翻译中，请稍候';
  const t = currentTranslation.value;
  if (!t) return '当前语言未准备';
  if (t.status === 'failed') return t.error ? `翻译失败：${t.error}` : '翻译失败，请重试';
  if (t.status !== 'ready') return '当前语言未准备';
  const reviewedText = t.reviewed ? '已校对' : '未校对';
  const audioText = t.render_mode === 'audio' ? (t.audio_ready ? '音频已就绪' : '音频未就绪') : '文本驱动';
  return `${reviewedText}｜${audioText}`;
});

const getLanguageTabStateText = (languageKey: string): string => {
  if (isSourceLanguage(languageKey)) return '主稿';
  if (isLanguageTranslating(languageKey)) return '翻译中';
  if (translationMap[languageKey]?.status === 'failed') return '失败';
  return isLanguagePrepared(languageKey) ? '已准备' : '未准备';
};

const currentLanguageReady = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return true;
  return isLanguagePrepared(currentEditLanguage.value);
});

const sourceLanguageHint = computed(() => {
  const langLabel = languageOptions.find((x) => x.key === sourceLanguageKey.value)?.label || sourceLanguageKey.value;
  if (sourceLanguageKey.value === loadedSourceLanguage.value) {
    return `自动识别主稿语种：${langLabel}。如识别不准确，可手动切换。`;
  }
  return `主稿语种已手动改为：${langLabel}。保存后将按该语种作为原文生成与翻译。`;
});

const ensurePairHighlights = (values: string[]) => {
  const out = values.map((x) => x.trim()).filter(Boolean).slice(0, 2);
  while (out.length < 2) out.push('');
  return out;
};

const ensureReflections = (values: string[]) => {
  const out = values.map((x) => x.trim()).filter(Boolean).slice(0, 5);
  while (out.length < 5) out.push('');
  return out;
};

const ensureQuestions = (values: string[]) => {
  const out = values.map((x) => x.trim()).filter(Boolean).slice(0, 3);
  while (out.length < 3) out.push('');
  return out;
};

const ensureReportOrder = async () => {
  try {
    const pageSize = 100;
    const merged: number[] = [];
    let page = 1;
    while (page <= 20) {
      const res = await listReports(page, pageSize);
      const ids = (res.items || []).map((x) => x.id);
      merged.push(...ids);
      if (ids.length < pageSize) break;
      page += 1;
    }
    reportIds.value = merged;
  } catch {
    reportIds.value = [];
  }
};

const clearTranslationState = () => {
  for (const key of Object.keys(translationMap)) {
    delete translationMap[key];
  }
  currentEditLanguage.value = sourceLanguageKey.value;
};

const resetTranslationsOnSourceChange = () => {
  const hasTranslations = Object.keys(translationMap).length > 0;
  if (!hasTranslations) return;
  stopTranslationPolling();
  clearTranslationState();
  info.value = '原文已变更，多语言内容已清空并重置为未准备，请重新翻译。';
};

const ensureTranslationDraft = (languageKey: string): TranslationDraft => {
  if (translationMap[languageKey]) {
    return translationMap[languageKey];
  }
  const draft: TranslationDraft = {
    title: '',
    script_final: '',
    highlights_final: ensurePairHighlights([]),
    reflections_final: ensureReflections([]),
    questions_final: ensureQuestions([]),
    question_persona: form.question_persona,
    reviewed: false,
    reviewed_at: null,
    status: 'missing',
    render_mode: 'text',
    audio_ready: false,
    error: '',
  };
  translationMap[languageKey] = draft;
  return draft;
};

const isLanguageTranslating = (languageKey: string): boolean => {
  if (isSourceLanguage(languageKey)) return false;
  return translationMap[languageKey]?.status === 'translating';
};

const setLanguageTranslating = (languageKey: string, translating: boolean) => {
  if (isSourceLanguage(languageKey)) return;
  const draft = ensureTranslationDraft(languageKey);
  draft.status = translating ? 'translating' : draft.status === 'translating' ? 'missing' : draft.status;
  if (translating) draft.error = '';
};

const isLanguagePrepared = (languageKey: string): boolean => {
  if (isSourceLanguage(languageKey)) return true;
  const t = translationMap[languageKey];
  if (!t) return false;
  if (t.status === 'failed') return false;
  if ((t.script_final || '').trim()) return true;
  if (t.status === 'ready') return true;
  return false;
};

const upsertTranslation = (
  languageKey: string,
  payload: {
    title: string;
    script_final: string;
    highlights_final: string[];
    reflections_final: string[];
    questions_final: string[];
    question_persona: string;
    reviewed: boolean;
    reviewed_at: string | null;
    status: 'missing' | 'translating' | 'ready' | 'failed';
    render_mode: 'text' | 'audio';
    audio_ready: boolean;
    error?: string;
  },
) => {
  const normalizedStatus =
    payload.status === 'failed'
      ? 'failed'
      : payload.status === 'translating'
        ? 'translating'
        : payload.status === 'ready' || (payload.script_final || '').trim()
          ? 'ready'
          : 'missing';
  
  const newHighlights = ensurePairHighlights(payload.highlights_final || []);
  const newReflections = ensureReflections(payload.reflections_final || []);
  const newQuestions = ensureQuestions(payload.questions_final || []);
  
  // 如果已存在，检查是否真的需要更新（避免触发不必要的响应式更新）
  const existing = translationMap[languageKey];
  if (existing) {
    let changed = false;
    if (existing.title !== (payload.title || form.title)) { existing.title = payload.title || form.title; changed = true; }
    if (existing.script_final !== (payload.script_final || '')) { existing.script_final = payload.script_final || ''; changed = true; }
    if (existing.reviewed !== Boolean(payload.reviewed)) { existing.reviewed = Boolean(payload.reviewed); changed = true; }
    if (existing.reviewed_at !== (payload.reviewed_at || null)) { existing.reviewed_at = payload.reviewed_at || null; changed = true; }
    if (existing.status !== normalizedStatus) { existing.status = normalizedStatus; changed = true; }
    if (existing.render_mode !== payload.render_mode) { existing.render_mode = payload.render_mode; changed = true; }
    if (existing.audio_ready !== Boolean(payload.audio_ready)) { existing.audio_ready = Boolean(payload.audio_ready); changed = true; }
    if (existing.error !== (payload.error || '')) { existing.error = payload.error || ''; changed = true; }
    if (existing.question_persona !== (payload.question_persona || form.question_persona)) {
      existing.question_persona = payload.question_persona || form.question_persona;
      changed = true;
    }
    
    // 检查数组是否变化
    if (JSON.stringify(existing.highlights_final) !== JSON.stringify(newHighlights)) {
      existing.highlights_final = newHighlights;
      changed = true;
    }
    if (JSON.stringify(existing.reflections_final) !== JSON.stringify(newReflections)) {
      existing.reflections_final = newReflections;
      changed = true;
    }
    if (JSON.stringify(existing.questions_final) !== JSON.stringify(newQuestions)) {
      existing.questions_final = newQuestions;
      changed = true;
    }
    // 如果没有任何变化，直接返回，避免触发响应式更新
    if (!changed) return;
  } else {
    // 不存在则创建新对象
    translationMap[languageKey] = {
      title: payload.title || form.title,
      script_final: payload.script_final || '',
      highlights_final: newHighlights,
      reflections_final: newReflections,
      questions_final: newQuestions,
      question_persona: payload.question_persona || form.question_persona,
      reviewed: Boolean(payload.reviewed),
      reviewed_at: payload.reviewed_at || null,
      status: normalizedStatus,
      render_mode: payload.render_mode,
      audio_ready: Boolean(payload.audio_ready),
      error: payload.error || '',
    };
  }
};

const loadTranslations = async (id: number) => {
  try {
    const data = await getReportTranslations(id);
    const incomingKeys = new Set<string>();
    for (const item of data.items || []) {
      if (isSourceLanguage(item.language_key)) continue;
      incomingKeys.add(item.language_key);
      upsertTranslation(item.language_key, item);
    }
    // 移除后端已不存在的翻译记录
    for (const key of Object.keys(translationMap)) {
      if (!isSourceLanguage(key) && !incomingKeys.has(key)) {
        delete translationMap[key];
      }
    }
    const hasTranslating = Object.values(translationMap).some((x) => x.status === 'translating');
    if (hasTranslating) {
      startTranslationPolling();
    }
    if (!hasTranslating) {
      stopTranslationPolling();
    }
  } catch {
    // ignore polling failures; keep latest local state
  }
};

let translationPollingErrorCount = 0;
const MAX_POLLING_ERRORS = 5;

const startTranslationPolling = () => {
  if (translationPollingTimer !== null || !reportId.value) return;
  translationPollingErrorCount = 0;
  translationPollingTimer = window.setInterval(async () => {
    if (!reportId.value) return;
    if (translationPollingErrorCount >= MAX_POLLING_ERRORS) {
      stopTranslationPolling();
      return;
    }
    try {
      await loadTranslations(reportId.value);
      translationPollingErrorCount = 0; // 成功则重置错误计数
    } catch {
      translationPollingErrorCount += 1;
    }
  }, 5000); // 从3秒改为5秒，降低轮询频率
};

const stopTranslationPolling = () => {
  if (translationPollingTimer === null) return;
  window.clearInterval(translationPollingTimer);
  translationPollingTimer = null;
};

const loadDetail = async (id: number) => {
  isHydrating.value = true;
  try {
    const data = await getReport(id);
    reportId.value = data.id;
    sourceLanguageKey.value = data.source_language || 'zh';
    loadedSourceLanguage.value = data.source_language || 'zh';
    currentEditLanguage.value = sourceLanguageKey.value;
    form.title = data.title || '';
    form.meeting_time = data.meeting_time ? data.meeting_time.slice(0, 16) : '';
    form.speaker = data.speaker || '';
    form.summary_raw = data.summary_raw || '';
    form.script_final = data.script_final || data.script_draft || '';
    const highlightsFinal = Array.isArray(data.highlights_final) ? data.highlights_final : [];
    const highlightsDraft = Array.isArray(data.highlights_draft) ? data.highlights_draft : [];
    const highlights = (highlightsFinal.length ? highlightsFinal : highlightsDraft).slice(0, 2);
    form.highlights_final = ensurePairHighlights(highlights);
    form.reflections_final = ensureReflections(data.reflections_final || []);
    form.questions_final = ensureQuestions(data.questions_final || []);
    form.question_persona = data.question_persona || 'board_director';
    await loadTranslations(data.id);
  } catch (error: any) {
    console.error('[EditorPage] loadDetail failed:', error);
    info.value = `加载失败：${error?.message || '未知错误'}`;
    // 确保即使失败也能显示基本界面，不要白屏
    reportId.value = id;
    sourceLanguageKey.value = 'zh';
    loadedSourceLanguage.value = 'zh';
    currentEditLanguage.value = 'zh';
  } finally {
    isHydrating.value = false;
  }
};

const persistZhReport = async (enableAutoPlay?: boolean): Promise<{ id: number; created: boolean }> => {
  const payload = {
    title: form.title.trim(),
    meeting_time: form.meeting_time || undefined,
    speaker: form.speaker.trim(),
    summary_raw: form.summary_raw.trim(),
    source_language: sourceLanguageKey.value,
    script_final: form.script_final.trim(),
    highlights_final: form.highlights_final.map((x) => x.trim()).filter(Boolean),
    reflections_final: form.reflections_final.map((x) => x.trim()).filter(Boolean),
    questions_final: form.questions_final.map((x) => x.trim()).filter(Boolean),
    question_persona: form.question_persona,
    auto_play_enabled: enableAutoPlay,
  };

  if (!reportId.value) {
    const created = await createReport(payload);
    reportId.value = created.id;
    loadedSourceLanguage.value = created.source_language || sourceLanguageKey.value;
    await router.replace(`/editor/${created.id}`);
    return { id: created.id, created: true };
  }

  const updated = await updateReport(reportId.value, payload);
  loadedSourceLanguage.value = updated.source_language || sourceLanguageKey.value;
  return { id: reportId.value, created: false };
};

const queueRetranslateLanguage = async (languageKey: string, persistedReportId?: number) => {
  if (isSourceLanguage(languageKey)) return;
  if (!canGenerate.value) {
    throw new Error('请先填写标题和内容');
  }

  const saved = persistedReportId ? { id: persistedReportId, created: false } : await persistZhReport(undefined);
  await retranslateSingleLanguage(saved.id, languageKey);
  setLanguageTranslating(languageKey, true);
  startTranslationPolling();
};

const onLanguageTabClick = async (languageKey: string) => {
  try {
    if (isSourceLanguage(languageKey)) {
      currentEditLanguage.value = sourceLanguageKey.value;
      return;
    }

    if (isLanguagePrepared(languageKey)) {
      currentEditLanguage.value = languageKey;
      return;
    }

    if (isLanguageTranslating(languageKey)) {
      info.value = `${languageOptions.find((x) => x.key === languageKey)?.label || languageKey} 翻译中，请稍候`;
      return;
    }

    info.value = `${languageOptions.find((x) => x.key === languageKey)?.label || languageKey} 翻译中...`;
    await queueRetranslateLanguage(languageKey);
    info.value = `${languageOptions.find((x) => x.key === languageKey)?.label || languageKey} 已加入翻译队列`;
    if (reportId.value) {
      await loadTranslations(reportId.value);
    }
  } catch (e: any) {
    info.value = `语言处理失败：${String(e?.message || e)}`;
  }
};

const currentScriptValue = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.script_final;
  return currentTranslation.value?.script_final || '';
});

const currentHighlight1 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.highlights_final[0] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.highlights_final)) ? (trans.highlights_final[0] || '') : '';
});

const currentHighlight2 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.highlights_final[1] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.highlights_final)) ? (trans.highlights_final[1] || '') : '';
});

const currentTitleValue = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.title;
  return currentTranslation.value?.title || '';
});

const currentReflection1 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[0] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.reflections_final)) ? (trans.reflections_final[0] || '') : '';
});

const currentReflection2 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[1] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.reflections_final)) ? (trans.reflections_final[1] || '') : '';
});

const currentReflection3 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[2] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.reflections_final)) ? (trans.reflections_final[2] || '') : '';
});

const currentReflection4 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[3] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.reflections_final)) ? (trans.reflections_final[3] || '') : '';
});

const currentReflection5 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[4] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.reflections_final)) ? (trans.reflections_final[4] || '') : '';
});

const currentQuestion1 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.questions_final[0] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.questions_final)) ? (trans.questions_final[0] || '') : '';
});

const currentQuestion2 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.questions_final[1] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.questions_final)) ? (trans.questions_final[1] || '') : '';
});

const currentQuestion3 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.questions_final[2] || '';
  const trans = currentTranslation.value;
  return (trans && Array.isArray(trans.questions_final)) ? (trans.questions_final[2] || '') : '';
});

const onTitleInput = (event: Event) => {
  if (isSourceLanguage(currentEditLanguage.value)) return;
  const value = (event.target as HTMLInputElement).value;
  const lang = currentEditLanguage.value;
  if (!translationMap[lang]) return;
  translationMap[lang].title = value;
  translationMap[lang].reviewed = false;
};

const onScriptInput = (event: Event) => {
  const value = (event.target as HTMLTextAreaElement).value;
  if (isSourceLanguage(currentEditLanguage.value)) {
    form.script_final = value;
    return;
  }
  const lang = currentEditLanguage.value;
  if (!translationMap[lang]) return;
  translationMap[lang].script_final = value;
  translationMap[lang].reviewed = false;
};

const onHighlightInput = (index: number, event: Event) => {
  const value = (event.target as HTMLTextAreaElement).value;
  if (isSourceLanguage(currentEditLanguage.value)) {
    const next = [...form.highlights_final];
    while (next.length < 2) next.push('');
    next[index] = value;
    form.highlights_final = next;
    return;
  }

  const lang = currentEditLanguage.value;
  if (!translationMap[lang]) return;
  const current = Array.isArray(translationMap[lang].highlights_final) ? translationMap[lang].highlights_final : [];
  const next = [...current];
  while (next.length < 2) next.push('');
  next[index] = value;
  translationMap[lang].highlights_final = next;
  translationMap[lang].reviewed = false;
};

const onReflectionInput = (index: number, event: Event) => {
  const value = (event.target as HTMLTextAreaElement).value;
  if (!isSourceLanguage(currentEditLanguage.value)) {
    const lang = currentEditLanguage.value;
    if (!translationMap[lang]) return;
    const current = Array.isArray(translationMap[lang].reflections_final) ? translationMap[lang].reflections_final : [];
    const next = [...current];
    while (next.length < 5) next.push('');
    next[index] = value;
    translationMap[lang].reflections_final = next;
    translationMap[lang].reviewed = false;
    return;
  }
  const next = [...form.reflections_final];
  while (next.length < 5) next.push('');
  next[index] = value;
  form.reflections_final = next;
};

const onQuestionInput = (index: number, event: Event) => {
  const value = (event.target as HTMLTextAreaElement).value;
  if (!isSourceLanguage(currentEditLanguage.value)) {
    const lang = currentEditLanguage.value;
    if (!translationMap[lang]) return;
    const current = Array.isArray(translationMap[lang].questions_final) ? translationMap[lang].questions_final : [];
    const next = [...current];
    while (next.length < 3) next.push('');
    next[index] = value;
    translationMap[lang].questions_final = next;
    translationMap[lang].reviewed = false;
    return;
  }
  const next = [...form.questions_final];
  while (next.length < 3) next.push('');
  next[index] = value;
  form.questions_final = next;
};

const handleGenerate = async () => {
  if (!canGenerate.value) {
    info.value = '请先填写标题和内容';
    return;
  }
  isGenerating.value = true;
  try {
    const saved = await persistZhReport(undefined);
    const generated = await generateReport(saved.id);
    form.script_final = generated.script_draft || '';
    form.highlights_final = ensurePairHighlights(generated.highlights_draft || []);
    form.reflections_final = ensureReflections(generated.reflections_draft || []);
    form.questions_final = ensureQuestions(generated.questions_draft || []);
    currentEditLanguage.value = sourceLanguageKey.value;
    info.value = 'AI 生成完成（仅主稿）。如需其他语种，请点击“AI 翻译全部语言”或直接点击目标语言 Tab。';
  } catch (e: any) {
    info.value = `AI 生成失败：${String(e.message || e)}`;
  } finally {
    isGenerating.value = false;
  }
};

const handleRetranslateAll = async () => {
  if (!canGenerate.value) {
    info.value = '请先填写标题和内容';
    return;
  }

  isPreparingLanguages.value = true;
  try {
    const saved = await persistZhReport(undefined);
    const triggered = await retranslateAllLanguages(saved.id);
    for (const key of triggered.languages) {
      setLanguageTranslating(key, true);
    }
    startTranslationPolling();
    info.value = '全部语言已加入翻译队列，可离开页面继续处理';
    await loadTranslations(saved.id);
  } catch (e: any) {
    info.value = `重译失败：${String(e.message || e)}`;
  } finally {
    isPreparingLanguages.value = false;
  }
};

const handleRetranslateCurrentLanguage = async () => {
  if (isSourceLanguage(currentEditLanguage.value)) return;
  try {
    await queueRetranslateLanguage(currentEditLanguage.value);
    info.value = `${languageOptions.find((x) => x.key === currentEditLanguage.value)?.label || currentEditLanguage.value} 已加入重译队列`;
    if (reportId.value) {
      await loadTranslations(reportId.value);
    }
  } catch (e: any) {
    info.value = `当前语言重译失败：${String(e.message || e)}`;
  }
};

const persistAllTranslations = async (id: number) => {
  const entries = Object.entries(translationMap).filter(([lang]) => !isSourceLanguage(lang));
  for (const [lang, translation] of entries) {
    const hasContent =
      Boolean((translation.title || '').trim()) ||
      Boolean((translation.script_final || '').trim()) ||
      translation.highlights_final.some((x) => Boolean((x || '').trim())) ||
      translation.reflections_final.some((x) => Boolean((x || '').trim())) ||
      translation.questions_final.some((x) => Boolean((x || '').trim()));
    if (!hasContent && translation.status !== 'ready') {
      continue;
    }
    const updated = await updateReportTranslation(id, lang, {
      title: translation.title,
      script_final: translation.script_final,
      highlights_final: translation.highlights_final,
      reflections_final: translation.reflections_final,
      questions_final: translation.questions_final,
      question_persona: translation.question_persona,
      reviewed: Boolean(translation.reviewed),
    });
    upsertTranslation(lang, updated);
  }
};

const handleSaveCurrentLanguage = async () => {
  if (isSourceLanguage(currentEditLanguage.value)) {
    info.value = '当前为主稿语种，请使用“保存全部”';
    return;
  }
  if (!reportId.value) {
    info.value = '请先保存主稿后再保存当前语言';
    return;
  }
  const lang = currentEditLanguage.value;
  const translation = translationMap[lang];
  if (!translation || !isLanguagePrepared(lang)) {
    info.value = '当前语言未准备完成，暂不可保存';
    return;
  }

  isSavingCurrentLanguage.value = true;
  try {
    const updated = await updateReportTranslation(reportId.value, lang, {
      title: translation.title,
      script_final: translation.script_final,
      highlights_final: translation.highlights_final,
      reflections_final: translation.reflections_final,
      questions_final: translation.questions_final,
      question_persona: translation.question_persona,
      reviewed: true,
    });
    upsertTranslation(lang, updated);
    info.value = `${languageOptions.find((x) => x.key === lang)?.label || lang} 已单独保存`;
  } catch (e: any) {
    info.value = `当前语言保存失败：${String(e.message || e)}`;
  } finally {
    isSavingCurrentLanguage.value = false;
  }
};

const saveCore = async (enableAutoPlay: boolean): Promise<number | null> => {
  if (!canSave.value) {
    info.value = '标题和内容为必填';
    return null;
  }

  try {
    form.highlights_final = ensurePairHighlights(form.highlights_final);
    form.reflections_final = ensureReflections(form.reflections_final);
    form.questions_final = ensureQuestions(form.questions_final);
    const saved = await persistZhReport(enableAutoPlay ? true : undefined);
    await persistAllTranslations(saved.id);

    info.value = enableAutoPlay ? '保存成功，已开启播报' : '保存成功';
    window.localStorage.setItem(queueVersionKey, String(Date.now()));
    await ensureReportOrder();
    if (saved.created) {
      await loadTranslations(saved.id);
    }
    return saved.id;
  } catch (e: any) {
    info.value = `保存失败：${String(e.message || e)}`;
    return null;
  }
};

const handleSave = async () => {
  await saveCore(false);
};

const resolveSelectedLanguages = (): string[] => {
  const fallback = ['zh'];
  const raw = window.localStorage.getItem(localLanguageKey);
  if (!raw) return fallback;
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return fallback;
    const valid = parsed
      .map((x: unknown) => String(x || '').trim())
      .filter(Boolean)
      .filter((x) => languageOptions.some((opt) => opt.key === x));
    return valid.length ? valid : fallback;
  } catch {
    return fallback;
  }
};

const handleSaveAndEnable = async () => {
  const savedId = await saveCore(true);
  if (!savedId) return;

  try {
    await updatePlaybackMode({
      mode: 'carousel_summary',
      carousel_scope: 'single',
      selected_report_id: savedId,
    });
  } catch {
    // 模式保存失败时继续跳转，沉浸页会按参数和本地状态兜底。
  }

  window.localStorage.setItem(focusReportIdKey, String(savedId));
  window.localStorage.setItem(queueVersionKey, String(Date.now()));
  const langs = resolveSelectedLanguages();
  const params = new URLSearchParams();
  params.set('t', String(Date.now()));
  params.set('langs', langs.join(','));
  params.set('mode', 'carousel_summary');
  window.location.assign(`/immersive/${savedId}?${params.toString()}`);
};

const goPrev = async () => {
  if (!prevId.value) return;
  await router.push(`/editor/${prevId.value}`);
};

const goNext = async () => {
  if (!nextId.value) return;
  await router.push(`/editor/${nextId.value}`);
};

watch(sourceLanguageKey, (nextLang, prevLang) => {
  if (!nextLang || nextLang === prevLang) return;
  if (isHydrating.value) return;
  if (currentEditLanguage.value === prevLang) {
    currentEditLanguage.value = nextLang;
  }
  resetTranslationsOnSourceChange();
  info.value = `原始语种已切换为 ${languageOptions.find((x) => x.key === nextLang)?.label || nextLang}`;
});

watch(
  () => [form.title, form.meeting_time, form.speaker, form.summary_raw],
  () => {
    if (isHydrating.value) return;
    resetTranslationsOnSourceChange();
  },
);

const loadCurrentFromRoute = async () => {
  const id = Number(route.params.id);
  if (!id) {
    stopTranslationPolling();
    isHydrating.value = true;
    reportId.value = null;
    sourceLanguageKey.value = 'zh';
    clearTranslationState();
    isHydrating.value = false;
    return;
  }
  try {
    await loadDetail(id);
  } catch (e: any) {
    const raw = String(e?.message || e || '');
    if (raw.includes('记录不存在') || raw.includes('404')) {
      window.alert('该记录不存在，已返回列表页。');
      await router.replace('/');
      return;
    }
    info.value = `详情加载失败：${raw}`;
  }
};

onMounted(async () => {
  await ensureReportOrder();
  await loadCurrentFromRoute();
});

onUnmounted(() => {
  stopTranslationPolling();
});

watch(
  () => route.params.id,
  async () => {
    await ensureReportOrder();
    await loadCurrentFromRoute();
  },
);
</script>
