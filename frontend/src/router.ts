import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { resolveLoggedUser } from '@/composables/useSession'

const routes: RouteRecordRaw[] = [
	{ path: '/', redirect: '/dashboard' },
	{
		path: '/dashboard',
		name: 'Dashboard',
		component: () => import('@/pages/DashboardPage.vue'),
	},
	{
		path: '/subscribers',
		name: 'Subscribers',
		component: () => import('@/pages/SubscribersPage.vue'),
	},
	{
		path: '/forms',
		name: 'Forms',
		component: () => import('@/pages/FormsPage.vue'),
	},
	{
		path: '/forms/:formId',
		name: 'Form',
		component: () => import('@/pages/FormPage.vue'),
		props: true,
	},
	{
		path: '/lead-magnets',
		name: 'Lead Magnets',
		component: () => import('@/pages/LeadMagnetsPage.vue'),
	},
	{
		path: '/lead-magnets/:leadMagnetId',
		name: 'Lead Magnet',
		component: () => import('@/pages/LeadMagnetPage.vue'),
		props: true,
	},
	{
		path: '/newsletters',
		name: 'Newsletters',
		component: () => import('@/pages/NewslettersPage.vue'),
	},
	{
		path: '/newsletters/:issueId',
		name: 'Newsletter',
		component: () => import('@/pages/NewsletterPage.vue'),
		props: true,
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
