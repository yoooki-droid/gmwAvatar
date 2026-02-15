<template>
   <div className="realtime-dh-text-render-content">
        <el-input
            v-model="inputValue"
            type="textarea"
            placeholder="Please input"
            class="realtime-dh-text-render-input"
            :autosize="false"
        />
        <el-button
            type="primary"
            class="realtime-dh-text-render-btn"
            @click="handleClick"
        >开始播报</el-button>
    </div>
</template>

<script setup>
import {ref} from 'vue';
import {ElMessage} from 'element-plus';

const emit = defineEmits(['render']);
const inputValue = ref('');

const handleClick = () => {
    const txt = inputValue.value.trim();
    if (!txt) {
        ElMessage({
            message: '请输入内容',
            type: 'warning',
        });
        return;
    }
    emit('render', 'text', {text: txt});
};
</script>

<style lang="css" scoped>
.realtime-dh-text-render-content {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.realtime-dh-text-render-input {
    border-radius: 12px;
    margin-bottom: 24px;
    flex: 1;
    width: 100%;
}
.realtime-dh-text-render-input >>> .el-textarea__inner {
  width: 100%;
  height: 100%;
  resize: none; /* 可选：禁用右下角拉伸 */
  box-sizing: border-box;
}
.realtime-dh-text-render-btn {
    width: 240px;
    margin: 0 auto;
}

.realtime-dh-text-render-btn:hover {
    background: #2468F2;
}
</style>