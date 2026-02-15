<template>
    <div class="realtime-dh-wrapper">
        <div class="realtime-dh-inner">
            <div class="realtime-dh-left-wrapper">
                <InputRender
                    @sendMessage="sendMessage"
                    @playAudio="playAudio"
                    @playStreamAudio="playStreamAudio"
                />
            </div>
            <div class="realtime-dh-right-wrapper">
                <div class="realtime-dh-right-inner">
                    <Iframe v-if="showHuman"></Iframe>
                    <div
                        v-if="showTimeoutTip && showHuman"
                        class="realtime-dh-right-tip"
                        @click="playWelcome"
                    >长时间无交互，数字人马上消失了，点我一下，进行交互</div>
                    <div class="dh-realtime-right-top-box">
                        <div class="dh-realtime-svg-wrapper" @click="handleMute">
                            <img :src="videoIsMuted ? MutedSvg : VoiceSvg" class="mute-icon" />
                        </div>
                        <el-dropdown>
                            <div class="dh-realtime-svg-wrapper">
                                <img :src="HumanSvg" class="setting-icon" />
                            </div>
                            <template #dropdown>
                                <el-dropdown-menu>
                                    <el-dropdown-item key="reload" @click="handleMountHuman">重载数字人</el-dropdown-item>
                                    <el-dropdown-item key="remove" @click="handleUnmountHuman">卸载数字人</el-dropdown-item>
                                </el-dropdown-menu>
                            </template>
                        </el-dropdown>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue';
import DHIframe from '@bddh/starling-dhiframe';

import VoiceSvg from '@/assets/voice.svg';
import MutedSvg from '@/assets/muted.svg';
import HumanSvg from '@/assets/human.svg';

import InputRender from './components/Render/Index.vue';
import Iframe from './components/Iframe/Index.vue';
import useAudioRender from './hooks/useAudioRender';
import {checkPlayUnMute} from './utils/audioUtils';
import {v4 as uuidV4} from 'uuid';

const ReadyState = {
    UNINSTANTIATED: -1,
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3
};
const dhIframe = new DHIframe('digital-human-iframe');
const realTimeVideoReady = ref(false);
const wsConnected = ref(false);
const videoIsMuted = ref(false);
const commandId = ref(uuidV4());
const checkOver = ref(false);
const showTimeoutTip = ref(false);
const showLoadingPage = ref(false);
const showHuman = ref(true);

const { playAudio, playStreamAudio } = useAudioRender(dhIframe);
// 重新加载
const handleMountHuman = () => {
    if (showHuman.value) {
        // 如果是加载的，需要先卸载
        showHuman.value = false;
        setTimeout(() => showHuman.value = true, 500);
    } else {
        showHuman.value = true;
    }
};
// 卸载
const handleUnmountHuman = () => {
    showHuman.value = false;
};
// 发送消息
const sendMessage = (msg) => {
    dhIframe.sendMessage(msg);
};
// mute
const handleMute = () => {
    const value = !videoIsMuted.value;
    dhIframe.sendCommand({
        subType: 'muteAudio',
        subContent: value
    });

    // sendCommand是异步的，建议等待1-2s后再进行文本驱动。
    setTimeout(() => {
        videoIsMuted.value = value;
    }, 100);
};
// 消息监听
const onMessage = (msg) => {
    if (msg.origin === 'https://open.xiling.baidu.com') {
        const { type, content } = msg.data;
        switch (type) {
            case 'rtcState':
                if (content.action === 'remoteVideoConnected') {
                    realTimeVideoReady.value = true;
                }
                if (content.action === 'localVideoMuted' && content.body) {
                    videoIsMuted.value = true;
                }
                break;
            case 'wsState':
                if (content.readyState === ReadyState.OPEN) {
                    wsConnected.value = true;
                } else if (content.readyState === ReadyState.CLOSED || content.readyState === ReadyState.CLOSING) {
                    wsConnected.value = false;
                }
                break;
            case 'msg':
                const { action, requestId } = content;
                if (requestId === commandId.value && action === 'FINISHED') {
                    console.info(`数字人驱动完成, 驱动id为${requestId}`);
                    const newCommandId = uuidV4();
                    // 解开注释可以进行持续播报
                    // commandId.value = newCommandId;
                    dhIframe.sendMessage({
                        action: 'TEXT_RENDER',
                        body: '我已经完成一次驱动，这是我说的第n句话',
                        requestId: newCommandId
                    });
                    showTimeoutTip.value = false;
                } else if (action === 'DISCONNECT_ALERT') {
                    showTimeoutTip.value = true;
                } else if (action === 'TIMEOUT_EXIT') {
                    showHuman.value = false;
                }
                break;
            default:
                break;
        }
    }
};
watch(
    [realTimeVideoReady, wsConnected, checkOver, videoIsMuted],
    ([newRealTimeVideoReady, newWsConnected, newCheckOver, newVideoIsMuted]) => {
        console.log('checkOver', newCheckOver, 'videoIsMuted', newVideoIsMuted);
        if (newRealTimeVideoReady && newWsConnected && newCheckOver && !newVideoIsMuted) {
            dhIframe.sendMessage({
                action: 'TEXT_RENDER',
                body: '这是我的开场白自我介绍，我是数字人',
                requestId: commandId.value
            });
        }
    }
);
onMounted(async () => {
    // 检测是否静音
    const result = await checkPlayUnMute(); // 500ms左右
    console.log('result', result);
    videoIsMuted.value = !result;
    checkOver.value = true;

    dhIframe.registerMessageReceived(onMessage);
    return () => {
        dhIframe.removeMessageReceived(onMessage);
    };
});
</script>

<style scoped>
#digital-human-iframe {
    max-width: 100%;
    height: 100%;
    max-height: 100%;
    aspect-ratio: 9/16;
    border: none;
}

.realtime-dh-wrapper {
    width: 100%;
    height: 100%;
    background-color: #fff;
    display: flex;
    justify-content: center;
    align-items: center;

    .realtime-dh-inner {
        width: 100%;
        height: 100%;
        /* max-width: 1200px;
        max-height: 780px; */
        display: flex;
        padding: 12px 24px 24px 24px;
        gap: 24px;
        box-sizing: border-box;
    }

    .realtime-dh-left-wrapper {
        width: 392px;
        height: 100%;
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
    }

    .realtime-dh-right-wrapper {
        flex: 1;
        padding-top: 60px;

        .realtime-dh-right-inner {
            position: relative;
            width: 100%;
            height: 100%;
            border-radius: 12px;
            overflow: hidden;
            background: #dde3f0;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .dh-realtime-right-top-box {
            position: absolute;
            right: 16px;
            top: 16px;
            display: flex;
            gap: 8px;
        }

        .dh-realtime-svg-wrapper {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border-radius: 6px;
            border: 1px solid #dde3f0;
            background: #fff;
            cursor: pointer;

            &:hover {
                border: 1px solid #007aff;
            }

            .setting-icon,
            .mute-icon {
                width: 16px;
                height: 16px;
            }
        }

        .realtime-dh-right-tip {
            position: absolute;
            left: 50%;
            cursor: pointer;
            top: 25%;
            transform: translateX(-50%);
        }
    }
}
</style>
