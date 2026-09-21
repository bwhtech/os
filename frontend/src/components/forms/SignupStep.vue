<template>
	<!-- One thing that happens on signup, numbered in the order it happens. A step that is off
	     keeps its place in the list, dimmed, so what is skipped is as plain as what is sent. -->
	<li class="relative flex gap-3 pb-8 last:pb-0">
		<div v-if="!last" class="absolute bottom-1 left-3 top-8 border-l border-outline-gray-2" aria-hidden="true" />
		<div
			class="relative flex size-6 shrink-0 items-center justify-center rounded-full text-sm-medium"
			:class="
				on
					? 'bg-surface-gray-7 text-ink-white'
					: 'border border-dashed border-outline-gray-3 text-ink-gray-4'
			"
		>
			{{ number }}
		</div>

		<div class="min-w-0 flex-1 space-y-4">
			<!-- Wraps so a wide action, like the lead magnet picker, drops under the text on a phone. -->
			<div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
				<div class="min-w-0 flex-1 basis-60 space-y-0.5 pt-0.5">
					<h3 class="text-base-medium" :class="on ? 'text-ink-gray-8' : 'text-ink-gray-5'">
						{{ title }}
					</h3>
					<p class="text-p-sm text-ink-gray-5">
						<slot name="summary">{{ summary }}</slot>
					</p>
				</div>
				<slot name="action" />
			</div>
			<div v-if="on && $slots.default" class="space-y-4">
				<slot />
			</div>
		</div>
	</li>
</template>

<script setup lang="ts">
withDefaults(
	defineProps<{
		number: number
		title: string
		summary?: string
		/** Off dims the step and hides its body. */
		on?: boolean
		last?: boolean
	}>(),
	{ summary: "", on: true, last: false },
);
</script>
