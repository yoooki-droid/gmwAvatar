<template class="dh-realtime-card-list">
    <div
        v-for="item in cardList"
        :key="item.key"
        class="dh-realtime-card"
    >
        <img :src="item.iconSrc" class="dh-realtime-card-icon" />
        <p class="dh-realtime-card-title">{{ item.name }}</p>
        <el-button
            v-show="renderStatus === item.key"
            @click="handleClick('interrupt')"
            class="dh-realtime-card-pause-btn"
        >
            <img :src="PauseSvg" class="dh-realtime-card-pause-icon"/>停止播报
        </el-button>
        <el-button
            v-show="renderStatus !== item.key"
            type="primary"
            @Click="handleClick(item.key)"
            class="dh-realtime-card-btn"
        >开始播报</el-button>
    </div>
</template>

<script setup>
import {reactive, ref} from 'vue';
import StreamPng from '@/assets/stream.png';
import AudioPng from '@/assets/audio.png';
import StreamAudioPng from '@/assets/stream-audio.png';
import PauseSvg from '@/assets/pause.svg';
import {RENDER_KEY} from './constants';

const emit = defineEmits(['render']);
const renderStatus = ref('');

const cardList = reactive([
    {
        name: '流式文本播报示例',
        key: RENDER_KEY.STREAM,
        iconSrc: StreamPng
    },
    {
        name: '流式音频播报示例',
        key: RENDER_KEY.STREAM_AUDIO,
        iconSrc: StreamAudioPng
    }
]);

const handleClick = (key) => {
    renderStatus.value = key === RENDER_KEY.EMPTY ? RENDER_KEY.EMPTY : key;
    emit('render', key);
};

</script>
<style>
.dh-realtime-card-list {
    max-width: 100%;
}

.dh-realtime-card {
    display: flex;
    max-width: 100%;
    padding: 16px 24px;
    justify-content: space-between;
    align-items: center;
    border-radius: 12px;
    border: 1px solid #dde3f0;
    margin-bottom: 16px;

    .dh-realtime-card-icon {
        width: 39px;
        height: 39px;
    }

    .dh-realtime-card-pause-icon {
        width: 16px;
        height: 16px;
    }

    .dh-realtime-card-btn {
        width: 140px;

        &:hover {
            background-color: #2468f2;
            color: #fff;
        }
    }

    .dh-realtime-card-pause-btn  {
        width: 140px;

        &:hover {
            background-color: #fff;
            border-color: #2468f2;
            color: #2468f2;
        }
    }
    .dh-realtime-card-title {
        flex: 1;
        color: #091221;
        text-align: left;
        font-family: "PingFang SC";
        font-size: 16px;
        font-style: normal;
        font-weight: 500;
        line-height: 26px;
        margin: 0;
    }
}
</style>