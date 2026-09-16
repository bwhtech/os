<template>
	<div class="space-y-6">
		<LinkedInPreview
			v-for="target in linkedin"
			:key="target.result.channel"
			:channel="target.channel"
			:texts="texts"
			:limit="target.result.limit"
			:errors="target.result.errors"
		/>

		<!-- X gets its own card in phase 4. Until then its errors still have to show. -->
		<div
			v-for="target in others"
			:key="target.result.channel"
			class="rounded-6 border border-dashed border-outline-gray-2 p-4"
		>
			<div class="flex items-center gap-2">
				<PlatformIcon :provider="target.result.provider" class="size-4 text-ink-gray-6" />
				<p class="text-p-sm text-ink-gray-7">{{ target.result.provider }}</p>
			</div>
			<p class="mt-2 text-p-sm text-ink-gray-5">No preview yet.</p>
			<p v-for="error in target.result.errors" :key="error" class="mt-1 text-p-sm text-ink-red-3">
				{{ error }}
			</p>
		</div>

		<p v-if="!targets.length" class="text-p-sm text-ink-gray-5">Pick a channel to see the post.</p>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LinkedInPreview from '@/components/social/LinkedInPreview.vue'
import PlatformIcon from '@/components/social/PlatformIcon.vue'
import type { SocialChannel, TargetValidation } from '@/types'

/** The post as each picked platform would show it, with what that platform refuses. */
const props = defineProps<{
	targets: { result: TargetValidation; channel?: SocialChannel }[]
	texts: string[]
}>()

const linkedin = computed(() => props.targets.filter((target) => target.result.provider === 'LinkedIn'))
const others = computed(() => props.targets.filter((target) => target.result.provider !== 'LinkedIn'))
</script>
