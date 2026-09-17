<template>
	<AppPageHeader title="Posts">
		<template #actions>
			<Button
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="New Post"
				:loading="insert.loading"
				@click="create()"
			/>
		</template>
		<template #mobile-actions>
			<Button
				variant="ghost"
				size="md"
				icon="lucide-plus"
				aria-label="New Post"
				:loading="insert.loading"
				@click="create()"
			/>
		</template>
	</AppPageHeader>

	<div class="px-3 pt-5 sm:px-5" :class="{ 'pb-10': layout === 'list' }">
		<div class="flex flex-wrap items-center gap-2">
			<TabButtons v-if="layout === 'list'" v-model="view" :options="VIEWS" />
			<TabButtons v-model="layout" class="ml-auto" :options="LAYOUTS" />
		</div>

		<SocialCalendar v-if="layout === 'calendar'" class="mt-4" />

		<ListSkeleton v-else-if="posts.loading && !posts.data" class="mt-5" />
		<ErrorMessage v-else-if="posts.error" class="mt-5" :message="errorMessage(posts.error)" />

		<SocialPostTable v-else-if="rows.length" class="mt-4" :posts="rows" />

		<div v-else class="flex flex-col items-center justify-center gap-3 py-16 text-center">
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-megaphone size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">{{ EMPTY[view] }}</p>
			<p class="max-w-sm text-sm text-ink-gray-5">
				{{
					connected.length
						? 'Write a post once, see it per platform, and pick when it goes out.'
						: 'Connect LinkedIn or X in Settings, then write a post here.'
				}}
			</p>
			<Button
				v-if="view !== 'published'"
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="New Post"
				class="mt-2"
				:loading="insert.loading"
				@click="create()"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, ErrorMessage, TabButtons, debounce, toast, useCall } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import SocialCalendar from '@/components/social/SocialCalendar.vue'
import SocialPostTable from '@/components/social/SocialPostTable.vue'
import { useNewSocialPost } from '@/composables/useNewSocialPost'
import { useSocialChannels } from '@/composables/useSocialChannels'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import { SOCIAL_DOCTYPES } from '@/lib/social'
import type { SocialPostRow } from '@/types'

/**
 * Social posts: what is coming and what went out, as a list or on the calendar next to
 * the videos they promote. See specs/04-social-posts.md.
 */
type View = 'upcoming' | 'published' | 'all'

type Layout = 'list' | 'calendar'

const VIEWS = [
	{ label: 'Upcoming', value: 'upcoming' },
	{ label: 'Published', value: 'published' },
	{ label: 'All', value: 'all' },
]

const LAYOUTS = [
	{ label: 'List', value: 'list', icon: 'lucide-list' },
	{ label: 'Calendar', value: 'calendar', icon: 'lucide-calendar-days' },
]

const EMPTY: Record<View, string> = {
	upcoming: 'Nothing lined up',
	published: 'Nothing published yet',
	all: 'No posts yet',
}

const route = useRoute()
const router = useRouter()
const view = ref<View>('upcoming')
// The calendar is a place to come back to, so it lives in the URL.
const layout = ref<Layout>(route.query.view === 'calendar' ? 'calendar' : 'list')
const { connected } = useSocialChannels()
const { create, insert } = useNewSocialPost()

watch(layout, syncQuery)

/** The layout is the whole of the query here, so writing it also drops what came before. */
function syncQuery() {
	router.replace({ query: layout.value === 'calendar' ? { view: 'calendar' } : {} })
}

const posts = useCall<SocialPostRow[], { view: View }>({
	url: '/api/v2/method/bwh_os.social.api.get_posts',
	params: () => ({ view: view.value }),
})

const rows = computed(() => posts.data ?? [])

onListUpdate(
	SOCIAL_DOCTYPES,
	debounce(() => posts.reload(), 300),
)

// A connect ends on the platform and comes back here. Say it worked, then drop the query.
onMounted(() => {
	const connectedProvider = route.query.connected
	if (!connectedProvider) return
	toast.success(`${connectedProvider} connected`)
	syncQuery()
})
</script>
