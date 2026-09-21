export interface NavItem {
	to: string
	label: string
	icon: string
}

export interface NavSection {
	label: string
	items: NavItem[]
}

/** One section per OS module. The desktop sidebar and the mobile "More" sheet both render it. */
export const SECTIONS: NavSection[] = [
	{
		label: 'Email List',
		items: [
			{ to: '/dashboard', label: 'Dashboard', icon: 'lucide-layout-dashboard' },
			{ to: '/subscribers', label: 'Subscribers', icon: 'lucide-users' },
			{ to: '/forms', label: 'Forms', icon: 'lucide-clipboard-list' },
			{ to: '/lead-magnets', label: 'Lead Magnets', icon: 'lucide-gift' },
			{ to: '/newsletters', label: 'Newsletters', icon: 'lucide-newspaper' },
		],
	},
	{
		label: 'Blog',
		items: [
			{ to: '/blog/overview', label: 'Overview', icon: 'lucide-chart-column' },
			{ to: '/blog/comments', label: 'Comments', icon: 'lucide-message-square' },
		],
	},
	{
		label: 'Social',
		items: [{ to: '/social', label: 'Posts', icon: 'lucide-megaphone' }],
	},
	{
		label: 'Videos',
		items: [
			{ to: '/videos', label: 'All Videos', icon: 'lucide-clapperboard' },
			{ to: '/series', label: 'Series', icon: 'lucide-library' },
		],
	},
	{
		label: 'Canvas',
		items: [{ to: '/canvas', label: 'All Canvases', icon: 'lucide-pen-tool' }],
	},
]

/** The pages that get a tab in the mobile nav. The rest live in the "More" sheet. */
export const MOBILE_TABS: NavItem[] = [
	{ to: '/dashboard', label: 'Dashboard', icon: 'lucide-layout-dashboard' },
	{ to: '/subscribers', label: 'Subscribers', icon: 'lucide-users' },
	{ to: '/newsletters', label: 'Newsletters', icon: 'lucide-newspaper' },
	{ to: '/blog/comments', label: 'Comments', icon: 'lucide-message-square' },
]

export const LOGO_URL = '/assets/bwh_os/images/os-logo.svg'
