<template>
    <iframe
       id="digital-human-iframe"
       :src="iframeUrl"
       :style="aspectRatio"
       allow="autoplay"
   ></iframe>
</template>

<script>
import { computed } from 'vue';
export default {
  setup() {
    const CUSTOME_PARAMS = {
      token: "i-rktjwdgmvuvcu/8220478b19a60aa6b48df1e07cf5ceac5049d8e7065044a0f8c727d10c46fab4/6954-05-06T09:07:29.017Z",
      figureId: 211868,
      ttsPerson: null,
      "cp-ttsSample": "16000",
      initMode: "noAudio",
      videoBg: "#F3F4FB",
      resolutionWidth: 1920,
      resolutionHeight: 1080,
      showDebugger: true,
      ttsPer: "LITE_presenter_female",
      backgroundImageUrl: "https://meta-human-editor-test.cdn.bcebos.com/17f8e526-1530-48ab-b02a-1c6138e1da1e/ffda0bfd-a0f5-49cc-bff4-1501ac1aa155/defaultBg.png",
      autoChromaKey: true,
      "cp-preAlertSec": 120,
      "cp-positionV2": "{\"location\":{\"top\":36,\"left\":239,\"width\":608,\"height\":1080}}"
    };
    const aspectRatio = computed(() => {
      const search = window.location.search;
      const params = new URLSearchParams(search);
      const resolutionWidth = params.get('resolutionWidth') || CUSTOME_PARAMS.resolutionWidth;
      const resolutionHeight = params.get('resolutionHeight') || CUSTOME_PARAMS.resolutionHeight;
      return {
        aspectRatio: +resolutionWidth / +resolutionHeight
      };
    });
    const iframeUrl = computed(() => {
      const search = window.location.search;
      const url = 'https://open.xiling.baidu.com/cloud/realtime';
      if (search.length > 0) {
        return `${url}${search}`;
      }
      const params = new URLSearchParams();
      Object.entries(CUSTOME_PARAMS || {}).forEach(([key, value]) => {
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          params.append(key, String(value));
        }
      });
      return `${url}?${params.toString()}`;
    });
    return {
      iframeUrl,
      aspectRatio
    };
  }
};
</script>
