<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Audience</h2>
			<p class="text-p-base text-ink-gray-6">
				<template v-if="preview.data">
					Goes to
					<span class="tabular-nums text-ink-gray-8">{{ preview.data.recipients }}</span>
					Active {{ preview.data.recipients === 1 ? 'subscriber' : 'subscribers' }}
					<template v-if="preview.data.batches.length > 1">
						over {{ preview.data.batches.length }} hours
					</template>
				</template>
				<template v-else>Counting subscribers…</template>
			</p>
		</div>

		<div class="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_10rem]">
			<Select v-model="audience" label="Send to" :options="AUDIENCES" />
			<TextInput
				v-model.number="hourlyLimit"
				type="number"
				label="Hourly limit"
				:min="1"
				description="Emails per hour"
			/>
		</div>
		<TagPicker
			v-if="audience === 'Tags'"
			v-model="tags"
			description="Active subscribers with any of these tags get the newsletter."
		/>
	</section>
</template>

<script setup lang="ts">
import { Select, TextInput } from 'frappe-ui'
import TagPicker from '@/components/tags/TagPicker.vue'
import type { AudiencePreview, NewsletterAudience } from '@/types'

defineProps<{ preview: { data: AudiencePreview | null } }>()

const audience = defineModel<NewsletterAudience>('audience', { required: true })
const tags = defineModel<string[]>('tags', { required: true })
const hourlyLimit = defineModel<number>('hourlyLimit', { required: true })

const AUDIENCES = [
	{ label: 'All Active subscribers', value: 'All Active' },
	{ label: 'Subscribers with tags', value: 'Tags' },
]
</script>
