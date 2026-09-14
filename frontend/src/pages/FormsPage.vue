<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Forms</h1>
		</PageHeaderTitle>
		<Button
			variant="solid"
			theme="gray"
			icon-left="lucide-plus"
			label="New Form"
			@click="newOpen = true"
		/>
	</PageHeader>

	<div class="px-3 py-5 pb-10 sm:px-5">
		<ListSkeleton v-if="forms.loading && !forms.data" />
		<ErrorMessage v-else-if="forms.error" :message="forms.error.message" />

		<div
			v-else-if="!forms.data?.length"
			class="flex flex-col items-center justify-center gap-3 py-16 text-center"
		>
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-clipboard-list size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">No forms yet</p>
			<p class="text-sm text-ink-gray-5">Make one form for each place people sign up.</p>
			<Button
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="New Form"
				class="mt-2"
				@click="newOpen = true"
			/>
		</div>

		<!-- Rows are links, so the hover surface bleeds into the gutter. -->
		<div v-else class="-mx-3 overflow-x-auto">
			<List
				class="min-w-[36rem] list-row-px-3"
				:columns="['minmax(12rem,1fr)', '12rem', '6rem', '6rem']"
				:row-height="44"
			>
				<ListHeader>
					<ListHeaderCell>Title</ListHeaderCell>
					<ListHeaderCell>Form ID</ListHeaderCell>
					<ListHeaderCell>Status</ListHeaderCell>
					<ListHeaderCell class="justify-end">Signups</ListHeaderCell>
				</ListHeader>
				<ListRows :items="forms.data" row-key="name">
					<template #default="{ item, value }">
						<ListRow :value="value" :to="`/forms/${item.name}`">
							<ListCell>
								<span class="truncate text-base text-ink-gray-8">{{ item.title }}</span>
							</ListCell>
							<ListCell>
								<code class="truncate font-mono text-sm text-ink-gray-6">{{ item.form_id }}</code>
							</ListCell>
							<ListCell>
								<Badge
									:label="item.is_active ? 'Active' : 'Closed'"
									:theme="item.is_active ? 'green' : 'gray'"
									variant="subtle"
								/>
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

	<NewFormDialog v-model:open="newOpen" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
	Badge,
	Button,
	ErrorMessage,
	PageHeader,
	PageHeaderTitle,
	useCall,
	useList,
} from 'frappe-ui'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import NewFormDialog from '@/components/forms/NewFormDialog.vue'
import type { SignupForm } from '@/types'

const newOpen = ref(false)

const forms = useList<SignupForm>({
	doctype: 'Signup Form',
	fields: ['name', 'title', 'form_id', 'is_active'],
	orderBy: 'creation desc',
	limit: 200,
})

const counts = useCall<Record<string, number>>({
	url: '/api/v2/method/bwh_os.mailing.api.get_signup_counts',
})
</script>
