<template>
	<AppPageHeader :breadcrumbs="breadcrumbs" back-to="/social">
		<template #title-suffix>
			<Badge v-if="post.doc" :theme="POST_STATUS_THEMES[post.doc.status]" :label="post.doc.status" />
		</template>
		<template #actions>
			<PublishBar
				v-if="post.doc"
				:post="post.doc"
				:can-publish="canPublish"
				:saved-label="savedLabel"
				:channels="validation.data?.length ?? 0"
				@changed="post.reload()"
			/>
			<Dropdown :options="menu">
				<Button variant="ghost" icon="lucide-ellipsis" aria-label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<div v-if="!post.doc" class="px-3 py-6 sm:px-5">
		<ErrorMessage v-if="post.error" :message="errorMessage(post.error)" />
		<DetailSkeleton v-else class="mx-auto max-w-[770px]" />
	</div>

	<!-- Fills the space below the header, so the border of the preview runs top to bottom. -->
	<div v-else class="flex min-h-[calc(100dvh-3rem)]">
		<div class="min-w-0 flex-1 px-3 sm:px-5">
			<div class="mx-auto w-full max-w-[640px] space-y-6 py-6">
				<div>
					<p class="mb-2 text-p-sm text-ink-gray-5">Post to</p>
					<ChannelPicker v-model="picked" :channels="channels.data ?? []" :disabled="locked" />
				</div>

				<PartEditor
					v-model="texts"
					:counts="strictest?.counts"
					:limit="strictest?.limit ?? 0"
					:part-name="partName"
					:disabled="locked"
				/>

				<p v-if="locked" class="text-p-sm text-ink-gray-5">
					A {{ post.doc.status.toLowerCase() }} post cannot change.
				</p>

				<!-- What each channel made of it. Nothing to show until a publish has run. -->
				<div v-if="locked" class="border-t border-outline-gray-1 pt-6">
					<p class="mb-2 text-p-sm text-ink-gray-5">Results</p>
					<TargetResults :targets="post.doc.targets" :channels="byName" />
				</div>

				<!-- On narrow screens the preview sits under the composer instead of beside it. -->
				<div class="border-t border-outline-gray-1 pt-6 xl:hidden">
					<PostPreviews :targets="previews" :texts="texts" />
				</div>
			</div>
		</div>

		<aside class="hidden w-[24rem] shrink-0 border-l border-outline-gray-1 xl:block">
			<div class="space-y-4 px-5 py-6">
				<p class="text-p-sm text-ink-gray-5">Preview</p>
				<PostPreviews :targets="previews" :texts="texts" />
			</div>
		</aside>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, Dropdown, ErrorMessage, debounce, dialog, toast, useCall, useDoc } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import ChannelPicker from '@/components/social/ChannelPicker.vue'
import PartEditor from '@/components/social/PartEditor.vue'
import PostPreviews from '@/components/social/PostPreviews.vue'
import PublishBar from '@/components/social/PublishBar.vue'
import TargetResults from '@/components/social/TargetResults.vue'
import { useAutosave } from '@/composables/useAutosave'
import { useSocialChannels } from '@/composables/useSocialChannels'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import { POST_STATUS_THEMES, SOCIAL_DOCTYPES, isLocked, partsOf } from '@/lib/social'
import type { SocialPost, SocialPostPart, SocialPostTarget, TargetValidation } from '@/types'

/** The composer. One text, every platform, and what each platform says about it. */
const props = defineProps<{ postId: string }>()

const router = useRouter()
const { channels, byName } = useSocialChannels()

const post = useDoc<SocialPost>({ doctype: 'Social Post', name: computed(() => props.postId) })

// What the composer holds. The document is the copy on the server, and autosave moves one to the other.
const texts = ref<string[]>([])
const picked = ref<string[]>([])

const locked = computed(() => isLocked(post.doc?.status))

// A publish runs in a worker and writes as it goes, so the page follows it live.
onListUpdate(
	SOCIAL_DOCTYPES,
	debounce(() => post.reload(), 300),
)

const breadcrumbs = computed(() => [
	{ label: 'Posts', route: '/social' },
	{ label: post.doc?.title || 'Untitled post' },
])

const menu = [{ label: 'Delete', icon: 'lucide-trash-2', theme: 'red' as const, onClick: remove }]

async function save(values: Partial<SocialPost>) {
	try {
		await post.setValue.submit(values)
	} catch (error) {
		toast.error(errorMessage(error as Error))
		throw error
	}
}

const autosave = useAutosave<SocialPost>(save)

const savedLabel = computed(() => {
	if (autosave.state.value === 'saving') return 'Saving…'
	if (autosave.state.value === 'error') return 'Not saved'
	return autosave.state.value === 'saved' ? 'Saved' : ''
})

// Load the post once. Our own saves come back and must not reset what is being typed.
watch(
	() => post.doc?.name,
	() => {
		texts.value = partsOf(post.doc).map((part) => part.text ?? '')
		if (!texts.value.length) texts.value = ['']
		picked.value = (post.doc?.targets ?? []).map((target) => target.channel)
	},
	{ immediate: true },
)

watch(texts, () => {
	if (!locked.value) autosave.queue({ parts: buildParts() })
})

watch(picked, () => {
	if (!locked.value) autosave.queue({ targets: buildTargets() })
})

/**
 * The shared parts, in order, keeping the row a text already had. Content written for one
 * channel stays as it is: the picker and this editor never touch it.
 */
function buildParts(): SocialPostPart[] {
	const existing = partsOf(post.doc)
	const shared = texts.value.map((text, index) => ({
		...(existing[index] ?? {}),
		channel: null,
		part_no: index + 1,
		text,
	})) as SocialPostPart[]
	const custom = (post.doc?.parts ?? []).filter((part) => part.channel)
	return [...shared, ...custom]
}

/** A channel that stays keeps its row, so its result and its released parts survive an edit. */
function buildTargets(): SocialPostTarget[] {
	const rows = new Map((post.doc?.targets ?? []).map((target) => [target.channel, target]))
	return picked.value.map(
		(channel) =>
			rows.get(channel) ?? ({ channel, provider: byName.value[channel]?.provider } as SocialPostTarget),
	)
}

const validation = useCall<TargetValidation[], { post: string }>({
	url: '/api/v2/method/bwh_os.social.api.validate_post',
	method: 'POST',
	immediate: false,
})

// The server owns the rules, so the counter and the errors come from it while you type.
const check = debounce(() => {
	if (!post.doc) return
	validation.submit({
		post: JSON.stringify({ ...post.doc, parts: buildParts(), targets: buildTargets() }),
	})
}, 400)

watch([texts, picked, () => post.doc?.name], check, { immediate: true })

/** The platform that would refuse first: the composer counts against that one. */
const strictest = computed(() =>
	(validation.data ?? []).reduce<TargetValidation | undefined>(
		(tightest, result) => (!tightest || result.limit < tightest.limit ? result : tightest),
		undefined,
	),
)

const previews = computed(() =>
	(validation.data ?? []).map((result) => ({ result, channel: byName.value[result.channel] })),
)

/** LinkedIn calls part 2 a comment, X calls it a reply. */
const partName = computed(() =>
	validation.data?.length && validation.data.every((result) => result.provider === 'X')
		? 'Reply'
		: 'Comment',
)

/** The server checks again before anything goes out. This only keeps the button honest. */
const canPublish = computed(
	() => Boolean(validation.data?.length) && validation.data!.every((result) => !result.errors.length),
)

function remove() {
	dialog.danger({
		title: 'Delete this post?',
		message: 'Its text, media and results go with it. Anything already published stays on the platform.',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await post.delete.submit()
			toast.success('Post deleted')
			router.push('/social')
		},
	})
}
</script>
