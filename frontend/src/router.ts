import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { resolveLoggedUser } from '@/composables/useSession'

const routes: RouteRecordRaw[] = [
	{ path: '/', redirect: '/subscribers' },
	{
		path: '/subscribers',
		name: 'Subscribers',
		component: () => import('@/pages/SubscribersPage.vue'),
	},
	{ path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
	// `website_route_rules` mounts the app at /os.
	history: createWebHistory('/os'),
	routes,
})

router.beforeEach(async (to) => {
	if (await resolveLoggedUser()) return true
	window.location.href = `/login?redirect-to=${encodeURIComponent(`/os${to.fullPath}`)}`
	return false
})

export default router
