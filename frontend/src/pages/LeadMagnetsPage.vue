<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Lead Magnets</h1>
		</PageHeaderTitle>
		<Button
			variant="solid"
			theme="gray"
			icon-left="lucide-plus"
			label="New Lead Magnet"
			@click="newOpen = true"
		/>
	</PageHeader>

	<div class="px-3 py-5 pb-10 sm:px-5">
		<LoadingText v-if="leadMagnets.loading && !leadMagnets.data" :lines="4" />
		<ErrorMessage v-else-if="leadMagnets.error" :message="leadMagnets.error.message" />

		<div
			v-else-if="!leadMagnets.data?.length"
			class="flex flex-col items-center justify-center gap-3 py-16 text-center"
		>
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-gift size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">No lead magnets yet</p>
			<p class="text-sm text-ink-gray-5">Upload a file that people get when they sign up.</p>
			<Button
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="New Lead Magnet"
				class="mt-2"
				@click="newOpen = true"
			/>
		</div>

		<!-- Rows are links, so the hover surface bleeds into the gutter. -->
		<div v-else class="-mx-3 overflow-x-auto">
			<List
				class="min-w-[30rem] list-row-px-3"
				:columns="['minmax(12rem,1fr)', 'minmax(10rem,14rem)', '6rem']"
				:row-height="44"
			>
				<ListHeader>
					<ListHeaderCell>Title</ListHeaderCell>
					<ListHeaderCell>File</ListHeaderCell>
					<ListHeaderCell class="justify-end">Downloads</ListHeaderCell>
				</ListHeader>
				<ListRows :items="leadMagnets.data" row-key="name">
					<template #default="{ item, value }">
						<ListRow :value="value" :to="`/lead-magnets/${item.name}`">
							<ListCell>
								<span class="truncate text-base text-ink-gray-8">{{
									item.title
								}}</span>
							</ListCell>
							<ListCell>
								<span class="truncate text-sm text-ink-gray-6">{{
									fileName(item.file)
								}}</span>
							</ListCell>
							<ListCell class="justify-end">
								<span class="text-sm tabular-nums text-ink-gray-7">
									{{ counts.data?.[item.name] ?? 0 }}
								</span>
							</ListCell>
						</ListRow>
					</template>
				</ListRows>
			</List>
		</div>
	</div>

	<NewLeadMagnetDialog v-model:open="newOpen" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	PageHeaderTitle,
	useCall,
	useList,
} from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import NewLeadMagnetDialog from '@/components/lead-magnets/NewLeadMagnetDialog.vue'
import type { LeadMagnet } from '@/types'

const newOpen = ref(false)

const leadMagnets = useList<LeadMagnet>({
	doctype: 'Lead Magnet',
	fields: ['name', 'title', 'file'],
	orderBy: 'creation desc',
	limit: 200,
})

const counts = useCall<Record<string, number>>({
	url: '/api/v2/method/bwh_os.mailing.api.get_download_counts',
})

function fileName(url: string) {
	return decodeURIComponent(url.split('/').pop() ?? '')
}
</script>
