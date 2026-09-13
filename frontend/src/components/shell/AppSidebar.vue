<template>
	<Sidebar width="14rem">
		<SidebarHeader title="BWH OS" :logo="LOGO_URL" :menu-items="workspaceMenu" />

		<ScrollArea class="min-h-0 flex-1 px-1">
			<SidebarSection v-for="section in SECTIONS" :key="section.label" :label="section.label">
				<SidebarItem
					v-for="item in section.items"
					:key="item.to"
					:icon="item.icon"
					:label="item.label"
					:to="item.to"
					:active="route.path.startsWith(item.to)"
				/>
			</SidebarSection>
		</ScrollArea>

		<div class="shrink-0 p-1">
			<Dropdown :options="userMenu" side="top" align="start" match-trigger-width>
				<button
					class="flex w-full items-center gap-2 rounded-4 p-1.5 text-left hover:bg-surface-gray-3"
				>
					<Avatar size="sm" :image="user?.user_image ?? undefined" :label="user?.full_name ?? ''" />
					<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-8">
						{{ user?.full_name ?? '…' }}
					</span>
					<span class="lucide-chevrons-up-down size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
				</button>
			</Dropdown>
		</div>
	</Sidebar>
</template>

<script setup lang="ts">
import {
	Avatar,
	Dropdown,
	ScrollArea,
	Sidebar,
	SidebarHeader,
	SidebarItem,
	SidebarSection,
	type DropdownOptions,
} from 'frappe-ui'
import { useRoute } from 'vue-router'
import { useSession } from '@/composables/useSession'

const LOGO_URL = '/assets/bwh_os/images/os-logo.svg'

/** One sidebar section per OS module. */
const SECTIONS = [
	{
		label: 'Email List',
		items: [
			{ to: '/subscribers', label: 'Subscribers', icon: 'lucide-users' },
			{ to: '/forms', label: 'Forms', icon: 'lucide-clipboard-list' },
		],
	},
]

const route = useRoute()
const { user, logout } = useSession()

const workspaceMenu = [
	{
		label: 'Desk',
		icon: 'lucide-app-window',
		onClick: () => {
			window.location.href = '/desk'
		},
	},
]

const userMenu: DropdownOptions = [
	{ label: 'Log out', icon: 'lucide-log-out', theme: 'red', onClick: () => logout() },
]
</script>
