<template>
	<div class="flex flex-wrap items-center gap-x-2 gap-y-3">
		<div class="flex flex-wrap items-center gap-1">
			<button
				v-for="tab in tabs"
				:key="tab.value"
				type="button"
				role="tab"
				:aria-selected="tab.value === active"
				:class="[
					'flex items-center gap-1.5 rounded-full px-2.5 py-1 text-p-sm transition-colors',
					tab.value === active
						? 'bg-surface-gray-3 text-ink-gray-8'
						: 'text-ink-gray-6 hover:bg-surface-gray-2',
				]"
				@click="active = tab.value"
			>
				<Avatar
					v-if="tab.channel"
					:image="tab.channel.avatar_url ?? undefined"
					:label="tab.label"
					size="xs"
				/>
				{{ tab.label }}
				<!-- A channel writing its own text is worth seeing from the other tabs. -->
				<span
					v-if="tab.value && customized.includes(tab.value)"
					class="size-1.5 rounded-full bg-surface-gray-6"
					:title="`${tab.label} has its own content`"
				/>
			</button>
		</div>

		<Switch
			v-if="active"
			class="ml-auto"
			size="sm"
			label="Customize"
			:model-value="customized.includes(active)"
			:disabled="disabled"
			@update:model-value="emit('customize', active, $event)"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Avatar, Switch } from 'frappe-ui'
import type { SocialChannel, TargetValidation } from '@/types'

/**
 * Which content is being written: the one every channel gets, or one channel's own.
 * A channel writes its own only while Customize is on; turning it off drops that text.
 */
const props = defineProps<{
	targets: { result: TargetValidation; channel?: SocialChannel }[]
	/** The channels that write their own content */
	customized: string[]
	disabled?: boolean
}>()

const emit = defineEmits<{ customize: [channel: string, on: boolean] }>()

/** The empty value is the content every channel gets. */
const active = defineModel<string>({ required: true })

const tabs = computed(() => [
	{ value: '', label: 'All channels', channel: undefined },
	...props.targets.map((target) => ({
		value: target.result.channel,
		label: target.channel?.display_name ?? target.result.provider,
		channel: target.channel,
	})),
])
</script>
