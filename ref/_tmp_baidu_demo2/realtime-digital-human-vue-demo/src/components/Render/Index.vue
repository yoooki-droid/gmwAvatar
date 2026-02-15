<template>
    <el-tabs v-model="activeKey" style="height: 60px;">
        <el-tab-pane label="文本驱动播报" name="text" />
        <el-tab-pane label="更多驱动方式示例" name="more" />
    </el-tabs>
    <TextRender v-if="activeKey === RENDER_KEY.TEXT" @render="handleRender"/>
    <RenderList v-else="activeKey === RENDER_KEY.MORE" @render="handleRender"/>
</template>

<script setup>
import {ref} from 'vue';
import {v4 as uuidV4} from 'uuid';
import TextRender from './TextRender.vue';
import RenderList from './RenderList.vue';
import {RENDER_KEY, STREAM_TEXT} from './constants';

const emit = defineEmits(['sendMessage', 'playStreamAudio']);
const activeKey = ref(RENDER_KEY.TEXT);

const handleRender = (key, options = {}) => {
    const uuid = uuidV4();
    switch (key) {
        case RENDER_KEY.TEXT:
            emit('sendMessage', {
                action: 'TEXT_RENDER',
                body: '<interrupt></interrupt>',
                requestId: uuid
            });
            emit('sendMessage', {
                action: 'TEXT_RENDER',
                body: options?.text,
                requestId: uuidV4()
            });
            break;
        case RENDER_KEY.AUDIO:
            emit('sendMessage', {
                action: 'TEXT_RENDER',
                body: '<interrupt></interrupt>',
                requestId: uuid
            });
            break;
        case RENDER_KEY.STREAM:
            emit('sendMessage', {
                action: 'TEXT_RENDER',
                body: '<interrupt></interrupt>',
                requestId: uuid
            });
            // 一轮流式驱动requestId必须使用同一个requestId
            STREAM_TEXT.forEach((text, index) => {
                emit('sendMessage', {
                    action: 'TEXT_STREAM_RENDER',
                    body: JSON.stringify({
                        first: index === 0,
                        last: index === STREAM_TEXT.length - 1,
                        text: text,
                    }),
                    requestId: uuid
                });
            });
            break;
        case RENDER_KEY.STREAM_AUDIO:
            emit('playStreamAudio');
            break;
        case RENDER_KEY.INTERRPUT:
            // 打断数字人
            emit('sendMessage', {
                action: 'TEXT_RENDER',
                body: '<interrupt></interrupt>',
                requestId: uuid
            });
            break;
        default:
            break;
    }
};
</script>
<style>
.realtime-dh-input-render-container {
    min-height: 100%;
    display: flex;
    flex-direction: column;
}
</style>