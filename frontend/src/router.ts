import { createRouter, createWebHistory } from 'vue-router';

import EditorPage from './pages/EditorPage.vue';
import ListPage from './pages/ListPage.vue';
import PlaybackPage from './pages/PlaybackPage.vue';
import ImmersivePage from './pages/ImmersivePage.vue';
import ImmersiveMeetingPage from './pages/ImmersiveMeetingPage.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'list', component: ListPage },
    { path: '/editor', name: 'editor-create', component: EditorPage },
    { path: '/editor/:id', name: 'editor-detail', component: EditorPage },
    { path: '/playback', name: 'playback', component: PlaybackPage },
    { path: '/immersive/:id', name: 'immersive', component: ImmersivePage },
    { path: '/immersive-meeting/:id', name: 'immersive-meeting', component: ImmersiveMeetingPage },
  ],
});
