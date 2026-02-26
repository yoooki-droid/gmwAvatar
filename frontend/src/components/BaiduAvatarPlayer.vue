<template>
  <div class="avatar-card">
    <div class="avatar-toolbar" v-if="props.showToolbar !== false">
      <button class="btn" @click="reloadAvatar">重载数字人</button>
      <button class="btn" @click="toggleMute">{{ isMuted ? '取消静音' : '静音' }}</button>
      <span class="status">状态：{{ statusText }}</span>
    </div>

    <div class="avatar-stage" v-if="visible">
      <iframe
        v-if="iframeUrl"
        id="digital-human-iframe"
        :src="iframeUrl"
        allow="autoplay; microphone; camera; encrypted-media;"
        frameborder="0"
      />
      <div v-else class="avatar-empty">
        缺少数字人配置，请先在播放页填写 token 和 figureId。
      </div>
    </div>

    <div v-else class="avatar-stage avatar-empty">
      数字人已卸载，点击“重载数字人”恢复
    </div>
  </div>
</template>

<script setup lang="ts">
import DHIframe from '@bddh/starling-dhiframe';
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

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

const props = defineProps<{
  config: AvatarConfig | null;
  script: string;
  renderMode?: 'text' | 'audio';
  audioPcmBase64?: string;
  autoPlayWhenReady?: boolean;
  loopPlay?: boolean;
  showToolbar?: boolean;
}>();

const emit = defineEmits<{
  (e: 'subtitle', value: string): void;
  (e: 'status', value: string): void;
  (e: 'finished'): void;
}>();

const visible = ref(true);
const isMuted = ref(false);
const connected = ref(false);
const rtcReady = ref(false);
const wsReady = ref(false);

let dh: any = null;
let connectTimer: number | null = null;
let recoverTimer: number | null = null;
const statusText = ref('初始化中');

const iframeUrl = computed(() => {
  if (!props.config?.token || !props.config?.figureId) return '';
  const rw = props.config.resolutionWidth ?? 1920;
  const rh = props.config.resolutionHeight ?? 1080;
  const params = new URLSearchParams();
  params.set('token', props.config.token);
  params.set('figureId', String(props.config.figureId));
  params.set('initMode', 'noAudio');
  params.set('resolutionWidth', String(rw));
  params.set('resolutionHeight', String(rh));
  params.set('cp-ttsSample', props.config.ttsSample ?? '16000');
  params.set('videoBg', props.config.videoBg ?? '#F3F4FB');
  params.set('autoChromaKey', String(props.config.autoChromaKey ?? true));
  params.set('cp-preAlertSec', String(props.config.preAlertSec ?? 120));
  params.set('ttsPer', props.config.ttsPer ?? 'LITE_presenter_female');
  if (props.config.ttsLan) params.set('cp-ttsLan', props.config.ttsLan);
  if (props.config.positionV2) {
    params.set('cp-positionV2', props.config.positionV2);
  } else if (rw === 1920 && rh === 1080) {
    // 与百度云渲染 demo 对齐，减少人物出画概率。
    params.set('cp-positionV2', '{"location":{"top":36,"left":710,"width":608,"height":1080}}');
  }
  if (props.config.cameraId) params.set('cameraId', String(props.config.cameraId));
  return `https://open.xiling.baidu.com/cloud/realtime?${params.toString()}`;
});

const onMessage = (msg: MessageEvent) => {
  if (msg.origin !== 'https://open.xiling.baidu.com') return;
  const data: any = msg.data || {};
  const type = data.type;
  const content = data.content || {};

  if (type === 'rtcState') {
    if (content.action === 'remoteVideoConnected') rtcReady.value = true;
    if (content.action === 'localVideoMuted') isMuted.value = Boolean(content.body);
  }

  if (type === 'wsState') {
    wsReady.value = content.readyState === 1;
  }

  if (type === 'msg') {
    const action = content.action;
    if (action === 'DOWN_SUBTITLE') emit('subtitle', content.body || '');
    if (action === 'RENDER_START') setStatus('播报中');
    if (action === 'FINISHED') {
      setStatus('播报完成');
      emit('finished');
      if (props.loopPlay && props.script.trim()) {
        window.setTimeout(() => speak(props.script), 400);
      }
    }
    if (action === 'RENDER_ERROR') setStatus('播报失败');
    if (action === 'RENDER_INTERRUPTED') setStatus('播报中断');
    if (action === 'DISCONNECT_ALERT') setStatus('长时间无交互，即将断开');
    if (action === 'TIMEOUT_EXIT') {
      setStatus('数字人已退出，正在自动重连');
      visible.value = false;
      scheduleAutoRecover();
    }
  }
};

const setStatus = (text: string) => {
  statusText.value = text;
  emit('status', text);
};

watch(
  () => iframeUrl.value,
  (url) => {
    if (!url) {
      setStatus('缺少数字人配置，请先填写 token 和 figureId');
    }
  },
  { immediate: true },
);

const initDHIframe = () => {
  if (!visible.value || !props.config || !iframeUrl.value) return;
  dh = new DHIframe('digital-human-iframe');
  dh.registerMessageReceived(onMessage);
  connected.value = true;
  setStatus('连接中');
  if (connectTimer) window.clearTimeout(connectTimer);
  connectTimer = window.setTimeout(() => {
    if (!rtcReady.value || !wsReady.value) {
      setStatus('连接超时：请检查 token、figureId、分辨率参数或网络');
    }
  }, 10000);
};

const disposeDHIframe = () => {
  if (!dh) return;
  dh.removeMessageReceived(onMessage);
  dh = null;
  connected.value = false;
  rtcReady.value = false;
  wsReady.value = false;
  if (connectTimer) {
    window.clearTimeout(connectTimer);
    connectTimer = null;
  }
  if (recoverTimer) {
    window.clearTimeout(recoverTimer);
    recoverTimer = null;
  }
};

const canSpeak = computed(() => connected.value && rtcReady.value && wsReady.value);

const sendInterrupt = () => {
  if (!dh) return;
  dh.sendMessage({
    action: 'TEXT_RENDER',
    body: '<interrupt></interrupt>',
    requestId: crypto.randomUUID(),
  });
};

const interrupt = () => {
  sendInterrupt();
  setStatus('播报中断');
};

const speakText = (text: string) => {
  if (!dh || !text.trim()) return;
  sendInterrupt();
  dh.sendMessage({
    action: 'TEXT_RENDER',
    body: text,
    requestId: crypto.randomUUID(),
  });
};

const base64ToUint8Array = (base64: string) => {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
};

const uint8ArrayToBase64 = (bytes: Uint8Array) => {
  let binary = '';
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
};

const wait = async (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

const speakAudio = async (pcmBase64: string) => {
  if (!dh || !pcmBase64.trim()) return;
  if (typeof (dh as any).sendAudioData !== 'function') {
    setStatus('当前数字人 SDK 不支持音频流播报');
    return;
  }
  const bytes = base64ToUint8Array(pcmBase64.trim());
  if (!bytes.length) {
    setStatus('音频数据为空，无法播报');
    return;
  }
  sendInterrupt();
  const requestId = crypto.randomUUID();
  const unitLen = 2048;
  const total = Math.ceil(bytes.length / unitLen);
  for (let i = 0; i < total; i += 1) {
    const chunk = bytes.slice(i * unitLen, (i + 1) * unitLen);
    const base64Chunk = uint8ArrayToBase64(chunk);
    (dh as any).sendAudioData({
      action: 'AUDIO_STREAM_RENDER',
      requestId,
      body: JSON.stringify({
        audio: base64Chunk,
        first: i === 0,
        last: i === total - 1,
      }),
    });
    if (i % 12 === 0) {
      await wait(10);
    }
  }
};

const speak = (text: string) => {
  speakText(text);
};

const toggleMute = () => {
  if (!dh) return;
  const nextMuted = !isMuted.value;
  dh.sendCommand({
    subType: 'muteAudio',
    subContent: nextMuted,
  });
  // 使用短延时同步 UI，避免命令异步导致闪烁。
  window.setTimeout(() => {
    isMuted.value = nextMuted;
  }, 150);
};

const reloadAvatar = async () => {
  disposeDHIframe();
  visible.value = false;
  await new Promise((r) => window.setTimeout(r, 300));
  visible.value = true;
  await nextTick();
  initDHIframe();
};

const unloadAvatar = () => {
  disposeDHIframe();
  visible.value = false;
  setStatus('数字人已卸载');
};

const loadAvatar = async () => {
  if (visible.value) return;
  visible.value = true;
  await nextTick();
  initDHIframe();
};

const scheduleAutoRecover = () => {
  if (props.showToolbar !== false) return;
  if (recoverTimer) window.clearTimeout(recoverTimer);
  recoverTimer = window.setTimeout(() => {
    reloadAvatar();
  }, 600);
};

watch(
  () => props.config,
  async (next) => {
    if (!next) return;
    await nextTick();
    disposeDHIframe();
    initDHIframe();
  },
  { immediate: true },
);

watch(
  [canSpeak, () => props.script, () => props.audioPcmBase64, () => props.renderMode, () => props.autoPlayWhenReady],
  async ([ready, script, audioPcmBase64, renderMode, autoPlay]) => {
    if (!ready || !autoPlay) return;
    if (renderMode === 'audio') {
      if (!audioPcmBase64?.trim()) return;
      await speakAudio(audioPcmBase64);
      return;
    }
    if (!script.trim()) return;
    speakText(script);
  },
);

onMounted(() => {
  window.addEventListener('message', onMessage as any);
});

onUnmounted(() => {
  window.removeEventListener('message', onMessage as any);
  disposeDHIframe();
});

defineExpose({ speak, speakText, speakAudio, interrupt, reloadAvatar, unloadAvatar, loadAvatar });
</script>
