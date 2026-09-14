<template>
	<SettingsDialog v-model:open="open" v-model:tab="tab" size="3xl">
		<template #title>Settings</template>
		<SettingsSidebar>
			<SettingsNavGroup v-for="group in GROUPS" :key="group.label" :label="group.label">
				<SettingsNavItem v-for="item in group.items" :key="item.value" :value="item.value">
					<template #prefix>
						<span :class="[item.icon, 'size-4 shrink-0 text-ink-gray-6']" aria-hidden="true" />
					</template>
					{{ item.label }}
				</SettingsNavItem>
			</SettingsNavGroup>
		</SettingsSidebar>

		<SettingsContent>
			<EmailSettings :open="open" />
			<BlogSettings :open="open" />
		</SettingsContent>
	</SettingsDialog>
</template>

<script setup lang="ts">
import {
	SettingsContent,
	SettingsDialog,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsSidebar,
} from 'frappe-ui'
import BlogSettings from '@/components/settings/BlogSettings.vue'
import EmailSettings from '@/components/settings/EmailSettings.vue'
import { useSettingsDialog } from '@/composables/useSettingsDialog'

/** All OS settings. Each module adds a group here and a component with its panels. */
const { open, tab } = useSettingsDialog()

const GROUPS = [
	{
		label: 'Email',
		items: [
			{ label: 'Sending', value: 'sending', icon: 'lucide-send' },
			{ label: 'Footer', value: 'footer', icon: 'lucide-building-2' },
		],
	},
	{
		label: 'Blog',
		items: [{ label: 'Comments', value: 'blog-comments', icon: 'lucide-message-square' }],
	},
]
</script>
