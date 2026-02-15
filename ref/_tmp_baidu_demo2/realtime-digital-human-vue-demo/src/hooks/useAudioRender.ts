import {v4 as uuidV4} from 'uuid';

import {arrayBufferToBase64} from "../utils/audioUtils";

export async function fetchData(url: string): Promise<ArrayBuffer> {
    const response = await fetch(url, {
        method: 'GET'
    });

    if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
    }

    // 将响应体解析为 ArrayBuffer
    const arrayBuffer = await response.arrayBuffer();
    return arrayBuffer;
}

const waitStop = async (time: number) => {
    return new Promise<void>(resolve => {
        setTimeout(() => resolve(), time || 100);
    });
};

export default function useAudioRender(dhIframe: any) {

    const playStreamAudio = async () => {
        const buffer = await fetchData('https://meta-human-editor-prd.cdn.bcebos.com/open-api%2FaudioTest.pcm');
        const unitLen = 2048; // 模拟切段
        const len = Math.ceil(buffer.byteLength / unitLen);
        const requestId = uuidV4();
        for (let i = 0; i < len; ++i) {
            const arrayBuffer = buffer.slice(i * unitLen, (i + 1) * unitLen);
            const base64String = arrayBufferToBase64(arrayBuffer); // pcm转base64
            if (i % 10 === 0) {
                await waitStop(50);
            }
            dhIframe.sendAudioData({
                action: 'AUDIO_STREAM_RENDER',
                requestId,
                body: JSON.stringify({
                    audio: base64String,
                    first: i === 0,
                    last: i === len - 1,
                }),
            })
        }
    };

    return {
        playStreamAudio
    };
}
