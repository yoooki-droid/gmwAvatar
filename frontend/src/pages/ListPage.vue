<template>
  <main class="cms-page">
    <div class="page-head compact">
      <div class="page-actions">
        <button class="btn ghost" @click="openFeishuPanel">绑定飞书会议</button>
        <RouterLink class="btn ghost" to="/playback">播放</RouterLink>
        <RouterLink class="btn dark" to="/editor">+ New Item</RouterLink>
      </div>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>自动播报</th>
            <th>Title</th>
            <th>Speaker</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>
              <label class="switch-wrap">
                <input
                  class="switch-input"
                  type="checkbox"
                  :checked="item.auto_play_enabled"
                  @change="toggleAutoPlay(item, $event)"
                />
                <span class="switch-label">{{ item.auto_play_enabled ? '开启' : '关闭' }}</span>
              </label>
            </td>
            <td>{{ item.title }}</td>
            <td>{{ item.speaker }}</td>
            <td>{{ formatDate(item.meeting_time) }}</td>
            <td>
              <div class="row-actions">
                <RouterLink class="btn ghost" :to="`/editor/${item.id}`">编辑</RouterLink>
                <button class="btn ghost danger" @click="removeItem(item.id)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="foot-note">Showing {{ total }} items</div>

    <div class="panel-mask" v-if="showFeishuPanel" @click.self="closeFeishuPanel">
      <section class="panel-card">
        <h3>绑定飞书会议并导入</h3>
        <p class="panel-desc">输入飞书会议链接后，系统会自动拉取妙记内容并导入到新闻列表。</p>
        <label>
          <span>飞书会议链接</span>
          <input
            v-model.trim="feishuLinkInput"
            class="field"
            placeholder="https://vc.feishu.cn/j/151322082 或 https://tpc.feishu.cn/minutes/xxxx"
          />
        </label>
        <div class="panel-grid">
          <label>
            <span>回溯天数</span>
            <input v-model.number="lookbackDaysInput" class="field" type="number" min="1" max="180" />
          </label>
          <label class="panel-check">
            <input v-model="autoGenerateInput" type="checkbox" />
            <span>导入后自动生成口播稿与亮点</span>
          </label>
          <label class="panel-check">
            <input v-model="autoEnablePlaybackInput" type="checkbox" />
            <span>导入后自动开启播报</span>
          </label>
        </div>
        <p class="panel-hint" v-if="feishuBindingLink">最近一次绑定：{{ feishuBindingLink }}</p>
        <p class="panel-hint" v-if="importResultText">{{ importResultText }}</p>
        <div class="panel-actions">
          <button class="btn ghost" :disabled="importing" @click="closeFeishuPanel">取消</button>
          <button class="btn primary" :disabled="importing" @click="bindAndImportFeishuMeeting">
            {{ importing ? '导入中...' : '绑定并导入' }}
          </button>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

import { deleteReport, importFeishuMeeting, listReports, type ReportListItem, updateReport } from '../services/api';

const FEISHU_BINDING_KEY = 'feishu_form_binding_link';
const queueVersionKey = 'playback_queue_version';

const items = ref<ReportListItem[]>([]);
const total = ref(0);

const showFeishuPanel = ref(false);
const feishuLinkInput = ref('');
const feishuBindingLink = ref('');
const importing = ref(false);
const lookbackDaysInput = ref(30);
const autoGenerateInput = ref(true);
const autoEnablePlaybackInput = ref(false);
const importResultText = ref('');

const formatDate = (raw: string) => {
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' });
};

const loadList = async () => {
  const res = await listReports(1, 50);
  items.value = res.items;
  total.value = res.total;
};

const toggleAutoPlay = async (item: ReportListItem, event: Event) => {
  const target = event.target as HTMLInputElement | null;
  const enabled = Boolean(target?.checked);
  const previous = item.auto_play_enabled;
  item.auto_play_enabled = enabled;
  try {
    await updateReport(item.id, { auto_play_enabled: enabled });
    window.localStorage.setItem(queueVersionKey, String(Date.now()));
  } catch {
    item.auto_play_enabled = previous;
    window.alert('自动播报开关保存失败，请重试');
  }
};

const removeItem = async (id: number) => {
  const ok = window.confirm('确认删除这条记录吗？删除后不可恢复。');
  if (!ok) return;
  await deleteReport(id);
  await loadList();
};

const openFeishuPanel = () => {
  feishuLinkInput.value = feishuBindingLink.value;
  importResultText.value = '';
  showFeishuPanel.value = true;
};

const closeFeishuPanel = () => {
  if (importing.value) return;
  showFeishuPanel.value = false;
};

const bindAndImportFeishuMeeting = async () => {
  const link = feishuLinkInput.value.trim();
  if (!link) {
    window.alert('请先输入飞书会议链接');
    return;
  }
  importing.value = true;
  importResultText.value = '';
  const lookbackDays = Number.isFinite(lookbackDaysInput.value) ? Math.max(1, Math.min(180, lookbackDaysInput.value)) : 30;
  try {
    const result = await importFeishuMeeting({
      meeting_url: link,
      lookback_days: lookbackDays,
      auto_generate: autoGenerateInput.value,
      auto_enable_playback: autoEnablePlaybackInput.value,
    });
    importResultText.value = `${result.message}。`;
    await loadList();
  } catch (error: any) {
    importResultText.value = `导入失败：${String(error?.message || error)}`;
  } finally {
    importing.value = false;
  }

  feishuBindingLink.value = link;
  window.localStorage.setItem(FEISHU_BINDING_KEY, link);
};

onMounted(async () => {
  feishuBindingLink.value = window.localStorage.getItem(FEISHU_BINDING_KEY) || '';
  await loadList();
});
</script>

<style scoped>
.page-head.compact {
  margin-bottom: 10px;
  align-items: center;
}

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

.panel-grid {
  display: grid;
  gap: 10px;
}

.panel-check {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.panel-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
