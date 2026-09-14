<template>
	<!-- Mobile and desktop are different navigation models, so the app picks one shell. -->
	<MobileShell v-if="isMobile">
		<router-view />
		<template #nav>
			<AppMobileNav @open-settings="settingsOpen = true" />
		</template>
	</MobileShell>

	<DesktopShell v-else>
		<template #sidebar>
			<AppSidebar @open-settings="settingsOpen = true" />
		</template>
		<router-view />
	</DesktopShell>

	<AppSettingsDialog v-model:open="settingsOpen" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DesktopShell, MobileShell, useColorScheme, usePageMeta } from 'frappe-ui'
import AppMobileNav from '@/components/shell/AppMobileNav.vue'
import AppSidebar from '@/components/shell/AppSidebar.vue'
import AppSettingsDialog from '@/components/settings/AppSettingsDialog.vue'
import { useIsMobile } from '@/composables/useIsMobile'

// Applies the stored `data-theme` before anything paints.
useColorScheme()
usePageMeta(() => ({ title: 'BWH OS' }))

const isMobile = useIsMobile()
const settingsOpen = ref(false)
</script>
