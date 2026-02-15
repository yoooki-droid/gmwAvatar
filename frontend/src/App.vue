<template>
  <div class="layout">
    <header class="topbar" v-if="!isImmersivePage">
      <div class="brand">News Anchor CMS</div>
      <nav class="nav">
        <RouterLink class="nav-link" to="/">列表</RouterLink>
        <RouterLink class="nav-link" to="/playback">播放</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const isImmersivePage = computed(() => route.path.startsWith('/immersive/'));
</script>
