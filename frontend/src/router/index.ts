import { createRouter, createWebHistory } from 'vue-router'
import GeneratorView from '@/views/GeneratorView.vue'
import ParserView from '@/views/ParserView.vue'
import SaverView from '@/views/SaverView.vue'
import LibraryView from '@/views/LibraryView.vue'
import TagsView from '@/views/TagsView.vue'
import RecordsView from '@/views/RecordsView.vue'
import LorasView from '@/views/LorasView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/generate' },
    { path: '/generate', name: 'generate', component: GeneratorView },
    { path: '/parser', name: 'parser', component: ParserView },
    { path: '/saver', name: 'saver', component: SaverView },
    { path: '/library', name: 'library', component: LibraryView },
    { path: '/records', name: 'records', component: RecordsView },
    { path: '/loras', name: 'loras', component: LorasView },
    { path: '/tags', name: 'tags', component: TagsView },
  ],
})

export default router