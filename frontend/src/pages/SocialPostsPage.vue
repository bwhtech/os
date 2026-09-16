<template>
	<AppPageHeader title="Posts">
		<template #actions>
			<Button
				variant="solid"
				theme="gray"
				icon-left="lucide-plus"
				label="New Post"
				:loading="insert.loading"
				@click="newPost"
			/>
		</template>
		<template #mobile-actions>
			<Button
				variant="ghost"
				size="md"
				icon="lucide-plus"
				aria-label="New Post"
				:loading="insert.loading"
				@click="newPost"
			/>
		</template>
	</AppPageHeader>

	<div class="px-3 pb-10 pt-5 sm:px-5">
		<TabButtons v-model="view" :options="VIEWS" />

		<ListSkeleton v-if="posts.loading && !posts.data" class="mt-5" />
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
				@click="newPost"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, ErrorMessage, TabButtons, debounce, toast, useCall } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import ListSkeleton from '@/components/list/ListSkeleton.vue'
import SocialPostTable from '@/components/social/SocialPostTable.vue'
import { useSocialChannels } from '@/composables/useSocialChannels'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import { SOCIAL_DOCTYPES, postRoute } from '@/lib/social'
import type { SocialPost, SocialPostRow } from '@/types'

/** Social posts: the list of what is coming and what went out. See specs/04-social-posts.md. */
type View = 'upcoming' | 'published' | 'all'

const VIEWS = [
	{ label: 'Upcoming', value: 'upcoming' },
	{ label: 'Published', value: 'published' },
	{ label: 'All', value: 'all' },
]

const EMPTY: Record<View, string> = {
	upcoming: 'Nothing lined up',
	published: 'Nothing published yet',
	all: 'No posts yet',
}

const route = useRoute()
const router = useRouter()
const view = ref<View>('upcoming')
const { connected } = useSocialChannels()

const posts = useCall<SocialPostRow[], { view: View }>({
	url: '/api/v2/method/bwh_os.social.api.get_posts',
	params: () => ({ view: view.value }),
})

const rows = computed(() => posts.data ?? [])

onListUpdate(
	SOCIAL_DOCTYPES,
	debounce(() => posts.reload(), 300),
)

const insert = useCall<SocialPost, Partial<SocialPost>>({
	url: '/api/v2/document/Social Post',
	method: 'POST',
	immediate: false,
})

/** A new post starts as a Draft for every connected channel, so attachments have a document. */
async function newPost() {
	try {
		const post = await insert.submit({
			status: 'Draft',
			targets: connected.value.map((channel) => ({
				channel: channel.name,
			})) as SocialPost['targets'],
			parts: [{ text: '' }] as SocialPost['parts'],
		})
		if (post) router.push(postRoute(post))
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

// A connect ends on the platform and comes back here. Say it worked, then drop the query.
onMounted(() => {
	const connectedProvider = route.query.connected
	if (!connectedProvider) return
	toast.success(`${connectedProvider} connected`)
	router.replace({ query: {} })
})
</script>
