import { createRouter, createWebHistory } from 'vue-router'
import GeneratorView from '@/views/GeneratorView.vue'
import SaverView from '@/views/SaverView.vue'
import LibraryView from '@/views/LibraryView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/generate' },
    { path: '/generate', name: 'generate', component: GeneratorView },
    { path: '/saver', name: 'saver', component: SaverView },
    { path: '/library', name: 'library', component: LibraryView },
  ],
})

export default router