<template>
	<div class="space-y-5">
		<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
			<div
				v-for="stat in stats"
				:key="stat.action"
				class="rounded-6 border border-outline-gray-1 px-3 py-2.5"
			>
				<p class="text-xl font-semibold text-ink-gray-9">{{ preview.counts[stat.action] }}</p>
				<p class="text-p-sm text-ink-gray-5">{{ stat.label }}</p>
			</div>
		</div>

		<TagPicker
			v-model="tags"
			label="Add Tags"
			description="Every imported row gets these tags, new and known emails alike."
		/>

		<div class="space-y-2">
			<p class="text-sm text-ink-gray-5">
				{{ preview.rows.length < preview.total ? `First ${preview.rows.length} of ${preview.total} rows` : 'All rows' }}
			</p>
			<div class="overflow-x-auto">
				<List
					class="min-w-[36rem] list-row-px-0"
					:columns="['minmax(12rem,1fr)', '7rem', 'minmax(8rem,12rem)', '6rem']"
					:row-height="40"
				>
					<ListHeader>
						<ListHeaderCell>Email</ListHeaderCell>
						<ListHeaderCell>First Name</ListHeaderCell>
						<ListHeaderCell>Tags</ListHeaderCell>
						<ListHeaderCell class="justify-end">Result</ListHeaderCell>
					</ListHeader>
					<ListRows :items="rows" row-key="key">
						<template #default="{ item, value }">
							<ListRow :value="value">
								<ListCell>
									<span
										class="truncate text-base"
										:class="item.action === 'Invalid' ? 'text-ink-gray-5' : 'text-ink-gray-8'"
									>
										{{ item.email || 'No email' }}
									</span>
								</ListCell>
								<ListCell>
									<span class="truncate text-sm text-ink-gray-7">{{ item.first_name }}</span>
								</ListCell>
								<ListCell class="gap-1 overflow-hidden">
									<template v-if="imports(item.action)">
										<Badge
											v-for="tag in item.tags"
											:key="tag"
											:label="tag"
											variant="outline"
											theme="gray"
											class="shrink-0"
										/>
									</template>
								</ListCell>
								<ListCell class="justify-end">
									<Badge
										:label="RESULTS[item.action].label"
										:theme="RESULTS[item.action].theme"
										variant="subtle"
									/>
								</ListCell>
							</ListRow>
						</template>
					</ListRows>
				</List>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import TagPicker from '@/components/tags/TagPicker.vue'
import type { ImportAction, ImportPreview } from '@/types'

const props = defineProps<{ preview: ImportPreview }>()
const tags = defineModel<string[]>('tags', { required: true })

const RESULTS: Record<ImportAction, { label: string; theme: 'green' | 'blue' | 'gray' | 'red' }> = {
	New: { label: 'Add', theme: 'green' },
	Existing: { label: 'Tag only', theme: 'blue' },
	Invalid: { label: 'Skip', theme: 'red' },
	Duplicate: { label: 'Skip', theme: 'gray' },
}

const stats: { action: ImportAction; label: string }[] = [
	{ action: 'New', label: 'New subscribers' },
	{ action: 'Existing', label: 'Already on the list' },
	{ action: 'Invalid', label: 'Invalid emails' },
	{ action: 'Duplicate', label: 'Repeated in file' },
]

// The preview has the tags from the CSV. The picked tags go first, as on import.
const rows = computed(() =>
	props.preview.rows.map((row, index) => ({
		...row,
		key: index,
		tags: [...new Set([...tags.value, ...row.tags])],
	})),
)

function imports(action: ImportAction) {
	return action === 'New' || action === 'Existing'
}
</script>
