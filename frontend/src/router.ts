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
	{ path: '/blog', redirect: '/blog/overview' },
	{
		path: '/blog/overview',
		name: 'Blog Overview',
		component: () => import('@/pages/BlogOverviewPage.vue'),
	},
	{
		path: '/blog/comments',
		name: 'Blog Comments',
		component: () => import('@/pages/BlogCommentsPage.vue'),
	},
	{
		path: '/social',
		name: 'Social Posts',
		component: () => import('@/pages/SocialPostsPage.vue'),
	},
	{
		path: '/social/:postId',
		name: 'Social Post',
		component: () => import('@/pages/SocialPostPage.vue'),
		props: true,
	},
	{
		path: '/videos',
		name: 'Videos',
		component: () => import('@/pages/VideosPage.vue'),
	},
	{
		path: '/videos/:videoId',
		name: 'Video',
		component: () => import('@/pages/VideoPage.vue'),
		props: true,
	},
	{
		path: '/series',
		name: 'Series List',
		component: () => import('@/pages/SeriesListPage.vue'),
	},
	// Routes with a `seriesId` show the sidebar of that series. See AppShell.
	{
		path: '/series/:seriesId',
		name: 'Series',
		component: () => import('@/pages/SeriesPage.vue'),
		props: true,
	},
	{
		path: '/series/:seriesId/videos/:videoId',
		name: 'Series Video',
		component: () => import('@/pages/VideoPage.vue'),
		props: true,
	},
	{
		path: '/canvas',
		name: 'Canvases',
		component: () => import('@/pages/CanvasesPage.vue'),
	},
	{
		path: '/canvas/:canvasId',
		name: 'Canvas',
		component: () => import('@/pages/CanvasPage.vue'),
		props: true,
	},
	// A window of its own, without the sidebar or the header. See AppShell.
	{
		path: '/canvas/:canvasId/window',
		name: 'Canvas Window',
		component: () => import('@/pages/CanvasWindowPage.vue'),
		props: true,
		meta: { bare: true },
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
