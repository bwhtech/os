<template>
	<DesktopShell>
		<template #sidebar>
			<AppSidebar />
		</template>
		<router-view />
	</DesktopShell>
</template>

<script setup lang="ts">
import { DesktopShell, useColorScheme, usePageMeta } from 'frappe-ui'
import AppSidebar from '@/components/shell/AppSidebar.vue'

// Applies the stored `data-theme` before anything paints.
useColorScheme()
usePageMeta(() => ({ title: 'BWH OS' }))
</script>
