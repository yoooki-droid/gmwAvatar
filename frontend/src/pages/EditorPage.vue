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
          :disabled="isPreparingLanguages || isGenerating || isSourceLanguage(currentEditLanguage)"
          @click="handleTranslateCurrentLanguage"
        >
          {{ isPreparingLanguages ? '翻译中...' : 'AI 翻译当前语言' }}
        </button>
        <button class="btn dark" :disabled="!canSave" @click="handleSave">保存</button>
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
            }"
            :disabled="isPreparingLanguages"
            @click="switchEditLanguage(lang.key)"
          >
            <span>{{ isSourceLanguage(lang.key) ? `原文（${lang.label}）` : lang.label }}</span>
            <span class="tab-state">{{ isSourceLanguage(lang.key) ? '主稿' : isLanguagePrepared(lang.key) ? '已准备' : '未准备' }}</span>
          </button>
        </div>
        <div class="actions">
          <button
            v-if="!isSourceLanguage(currentEditLanguage) && !currentLanguageReady"
            class="btn"
            :disabled="isPreparingLanguages"
            @click="prepareCurrentLanguage"
          >
            {{ isPreparingLanguages ? '准备中...' : '预翻译当前语言' }}
          </button>
          <span class="status-text">{{ currentLanguageStatusText }}</span>
        </div>
        <p class="hint">
          通过 Tab 切换查看不同语言内容；未准备语言会自动翻译标题、口播稿、Highlights 和反思。
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
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import {
  createReport,
  generateReport,
  getReport,
  getReportTranslations,
  listReports,
  prepareReportTranslation,
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
  reviewed: boolean;
  reviewed_at: string | null;
  status: 'missing' | 'ready';
  render_mode: 'text' | 'audio';
  audio_ready: boolean;
}

const languageOptions: LanguageOption[] = [
  { key: 'zh', label: '中文' },
  { key: 'en', label: '英文' },
  { key: 'yue', label: '粤语' },
  { key: 'ja', label: '日语' },
  { key: 'id', label: '印度尼西亚语' },
  { key: 'ms', label: '马来西亚语' },
  { key: 'hi', label: '印度语' },
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
const preparedLanguageKeys = ref<string[]>([]);
const currentEditLanguage = ref<string>('zh');
const sourceLanguageKey = ref<string>('zh');
const loadedSourceLanguage = ref<string>('zh');
const translationMap = reactive<Record<string, TranslationDraft>>({});

const form = reactive({
  title: '',
  meeting_time: '',
  speaker: '',
  summary_raw: '',
  script_final: '',
  highlights_final: ['', ''],
  reflections_final: ['', '', '', '', ''],
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
  const t = currentTranslation.value;
  if (!t) return '当前语言未准备';
  if (t.status !== 'ready') return '当前语言未准备';
  const reviewedText = t.reviewed ? '已校对' : '未校对';
  const audioText = t.render_mode === 'audio' ? (t.audio_ready ? '音频已就绪' : '音频未就绪') : '文本驱动';
  return `${reviewedText}｜${audioText}`;
});

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
  preparedLanguageKeys.value = [];
  currentEditLanguage.value = sourceLanguageKey.value;
};

const isLanguagePrepared = (languageKey: string): boolean => {
  if (isSourceLanguage(languageKey)) return true;
  const t = translationMap[languageKey];
  if (!t) return false;
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
    reviewed: boolean;
    reviewed_at: string | null;
    status: 'missing' | 'ready';
    render_mode: 'text' | 'audio';
    audio_ready: boolean;
  },
) => {
  const normalizedStatus =
    payload.status === 'ready' || (payload.script_final || '').trim() ? 'ready' : payload.status;
  translationMap[languageKey] = {
    title: payload.title || form.title,
    script_final: payload.script_final || '',
    highlights_final: ensurePairHighlights(payload.highlights_final || []),
    reflections_final: ensureReflections(payload.reflections_final || []),
    reviewed: Boolean(payload.reviewed),
    reviewed_at: payload.reviewed_at || null,
    status: normalizedStatus,
    render_mode: payload.render_mode,
    audio_ready: Boolean(payload.audio_ready),
  };
  if (normalizedStatus === 'ready' && !preparedLanguageKeys.value.includes(languageKey)) {
    preparedLanguageKeys.value.push(languageKey);
  }
};

const loadTranslations = async (id: number) => {
  clearTranslationState();
  try {
    const data = await getReportTranslations(id);
    for (const item of data.items || []) {
      if (isSourceLanguage(item.language_key)) continue;
      upsertTranslation(item.language_key, item);
    }
  } catch {
    preparedLanguageKeys.value = [];
  }
};

const loadDetail = async (id: number) => {
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
  const highlights = (data.highlights_final.length ? data.highlights_final : data.highlights_draft).slice(0, 2);
  form.highlights_final = ensurePairHighlights(highlights);
  form.reflections_final = ensureReflections(data.reflections_final || []);
  await loadTranslations(data.id);
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

const prepareLanguage = async (languageKey: string) => {
  if (isSourceLanguage(languageKey)) return;
  if (!canGenerate.value) {
    throw new Error('请先填写标题和内容');
  }

  const saved = await persistZhReport(undefined);
  const translated = await prepareReportTranslation(saved.id, languageKey);
  upsertTranslation(languageKey, translated);
  if (!preparedLanguageKeys.value.includes(languageKey)) {
    preparedLanguageKeys.value.push(languageKey);
  }
};

const switchEditLanguage = async (languageKey: string) => {
  if (isSourceLanguage(languageKey)) {
    currentEditLanguage.value = sourceLanguageKey.value;
    return;
  }

  if (!preparedLanguageKeys.value.includes(languageKey)) {
    isPreparingLanguages.value = true;
    try {
      await prepareLanguage(languageKey);
    } catch (e: any) {
      info.value = `语言切换失败：${String(e.message || e)}`;
      isPreparingLanguages.value = false;
      return;
    }
    isPreparingLanguages.value = false;
  }

  currentEditLanguage.value = languageKey;
};

const prepareCurrentLanguage = async () => {
  if (isSourceLanguage(currentEditLanguage.value)) return;
  isPreparingLanguages.value = true;
  try {
    await prepareLanguage(currentEditLanguage.value);
    info.value = `${languageOptions.find((x) => x.key === currentEditLanguage.value)?.label || currentEditLanguage.value} 已准备完成`;
    await ensureReportOrder();
  } catch (e: any) {
    info.value = `多语言准备失败：${String(e.message || e)}`;
  } finally {
    isPreparingLanguages.value = false;
  }
};

const currentScriptValue = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.script_final;
  return currentTranslation.value?.script_final || '';
});

const currentHighlight1 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.highlights_final[0] || '';
  return currentTranslation.value?.highlights_final[0] || '';
});

const currentHighlight2 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.highlights_final[1] || '';
  return currentTranslation.value?.highlights_final[1] || '';
});

const currentTitleValue = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.title;
  return currentTranslation.value?.title || '';
});

const currentReflection1 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[0] || '';
  return currentTranslation.value?.reflections_final[0] || '';
});

const currentReflection2 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[1] || '';
  return currentTranslation.value?.reflections_final[1] || '';
});

const currentReflection3 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[2] || '';
  return currentTranslation.value?.reflections_final[2] || '';
});

const currentReflection4 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[3] || '';
  return currentTranslation.value?.reflections_final[3] || '';
});

const currentReflection5 = computed(() => {
  if (isSourceLanguage(currentEditLanguage.value)) return form.reflections_final[4] || '';
  return currentTranslation.value?.reflections_final[4] || '';
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
  const next = [...translationMap[lang].highlights_final];
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
    const next = [...translationMap[lang].reflections_final];
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
    currentEditLanguage.value = sourceLanguageKey.value;
    info.value = 'AI 生成完成（仅主稿）。如需其他语种，请切换语言后点击“AI 翻译当前语言”。';
  } catch (e: any) {
    info.value = `AI 生成失败：${String(e.message || e)}`;
  } finally {
    isGenerating.value = false;
  }
};

const handleTranslateCurrentLanguage = async () => {
  if (isSourceLanguage(currentEditLanguage.value)) {
    info.value = '当前是主稿语种，请先切换到目标语言后再翻译';
    return;
  }
  await prepareCurrentLanguage();
};

const saveCore = async (enableAutoPlay: boolean): Promise<number | null> => {
  if (!canSave.value) {
    info.value = '标题和内容为必填';
    return null;
  }

  try {
    form.highlights_final = ensurePairHighlights(form.highlights_final);
    form.reflections_final = ensureReflections(form.reflections_final);
    const saved = await persistZhReport(enableAutoPlay ? true : undefined);

    if (!isSourceLanguage(currentEditLanguage.value)) {
      const lang = currentEditLanguage.value;
      const translation = translationMap[lang];
      if (translation) {
        const updated = await updateReportTranslation(saved.id, lang, {
          title: translation.title,
          script_final: translation.script_final,
          highlights_final: translation.highlights_final,
          reflections_final: translation.reflections_final,
          reviewed: true,
        });
        upsertTranslation(lang, updated);
      }
    }

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
  if (currentEditLanguage.value === prevLang) {
    currentEditLanguage.value = nextLang;
  }
  info.value = `原始语种已切换为 ${languageOptions.find((x) => x.key === nextLang)?.label || nextLang}`;
});

const loadCurrentFromRoute = async () => {
  const id = Number(route.params.id);
  if (!id) {
    reportId.value = null;
    sourceLanguageKey.value = 'zh';
    clearTranslationState();
    return;
  }
  try {
    await loadDetail(id);
  } catch (e: any) {
    info.value = `详情加载失败：${String(e.message || e)}`;
  }
};

onMounted(async () => {
  await ensureReportOrder();
  await loadCurrentFromRoute();
});

watch(
  () => route.params.id,
  async () => {
    await ensureReportOrder();
    await loadCurrentFromRoute();
  },
);
</script>
