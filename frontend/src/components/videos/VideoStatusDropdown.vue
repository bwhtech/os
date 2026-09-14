<template>
	<Dropdown :options="options">
		<Button variant="subtle" size="sm" icon-right="lucide-chevron-down">
			<template #prefix>
				<span :class="['size-1.5 rounded-full', statusDot(status)]" aria-hidden="true" />
			</template>
			{{ status }}
		</Button>
	</Dropdown>
</template>

<script setup lang="ts">
import { Button, Dropdown, type DropdownOptions } from 'frappe-ui'
import { STATUSES, statusDot } from '@/lib/videos'
import type { VideoStatus } from '@/types'

const status = defineModel<VideoStatus>({ required: true })

const options: DropdownOptions = STATUSES.map((value) => ({
	label: value,
	onClick: () => {
		status.value = value
	},
}))
</script>
