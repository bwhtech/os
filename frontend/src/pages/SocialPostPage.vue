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

				<div v-if="previews.length > 1" class="border-t border-outline-gray-1 pt-4">
					<ContentTabs
						v-model="tab"
						:targets="previews"
						:customized="customized"
						:disabled="locked"
						@customize="customize"
					/>
				</div>

				<p v-if="tab && !customized.includes(tab)" class="text-p-sm text-ink-gray-5">
					This channel posts what every channel gets. Turn on Customize to write for it alone.
				</p>

				<PartEditor
					v-model="editing"
					:post-name="postId"
					:counts="strictest?.counts"
					:limit="strictest?.limit ?? 0"
					:max-images="maxImages"
					:media-after-part-one="mediaAfterPartOne"
					:part-name="partName"
					:disabled="locked || (Boolean(tab) && !customized.includes(tab))"
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
					<PostPreviews :targets="previews" />
				</div>
			</div>
		</div>

		<aside class="hidden w-[24rem] shrink-0 border-l border-outline-gray-1 xl:block">
			<div class="space-y-4 px-5 py-6">
				<p class="text-p-sm text-ink-gray-5">Preview</p>
				<PostPreviews :targets="previews" />
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
import ContentTabs from '@/components/social/ContentTabs.vue'
import PartEditor from '@/components/social/PartEditor.vue'
import PostPreviews from '@/components/social/PostPreviews.vue'
import PublishBar from '@/components/social/PublishBar.vue'
import TargetResults from '@/components/social/TargetResults.vue'
import { useAutosave } from '@/composables/useAutosave'
import { useSocialChannels } from '@/composables/useSocialChannels'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import { POST_STATUS_THEMES, SOCIAL_DOCTYPES, draftPartsOf, isLocked, partsOf } from '@/lib/social'
import type { DraftPart } from '@/lib/social'
import type { SocialPost, SocialPostPart, SocialPostTarget, TargetValidation } from '@/types'

/** The composer. One text, every platform, and what each platform says about it. */
const props = defineProps<{ postId: string }>()

const router = useRouter()
const { channels, byName } = useSocialChannels()

const post = useDoc<SocialPost>({ doctype: 'Social Post', name: computed(() => props.postId) })

/**
 * What the composer holds. The document is the copy on the server, and autosave moves
 * one to the other. Content comes in groups: the empty key is what every channel gets,
 * and a channel key is the text written for that channel alone.
 */
const groups = ref<Record<string, DraftPart[]>>({ '': [{ text: '', media: [] }] })
const picked = ref<string[]>([])
/** The channels writing their own content, which is `use_custom_content` on their row. */
const customized = ref<string[]>([])
/** The group being written. The empty value is the one every channel gets. */
const tab = ref('')

/** A channel that writes nothing of its own shows the shared content, and cannot edit it. */
const editing = computed({
	get: () => groups.value[group.value] ?? [],
	set: (parts: DraftPart[]) => (groups.value = { ...groups.value, [group.value]: parts }),
})

const group = computed(() => (tab.value && customized.value.includes(tab.value) ? tab.value : ''))

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
		const targets = post.doc?.targets ?? []
		customized.value = targets.filter((target) => target.use_custom_content).map((row) => row.channel)
		groups.value = Object.fromEntries([
			['', draftPartsOf(post.doc)],
			...customized.value.map((channel) => [channel, draftPartsOf(post.doc, channel)]),
		])
		picked.value = targets.map((target) => target.channel)
		tab.value = ''
	},
	{ immediate: true },
)

watch(groups, () => {
	if (!locked.value) autosave.queue({ parts: buildParts() })
})

/**
 * Turning Customize on starts this channel from the shared content, so nobody rewrites a
 * post to change one line. Turning it off drops what was written for it, as the server does.
 */
function customize(channel: string, on: boolean) {
	if (on) {
		customized.value = [...customized.value, channel]
		groups.value = { ...groups.value, [channel]: clone(groups.value[channel] ?? groups.value['']) }
	} else {
		customized.value = customized.value.filter((name) => name !== channel)
		const { [channel]: _dropped, ...rest } = groups.value
		groups.value = rest
	}
	autosave.queue({ parts: buildParts(), targets: buildTargets() })
}

function clone(parts: DraftPart[]): DraftPart[] {
	return parts.map((part) => ({ text: part.text, media: [...part.media] }))
}

watch(picked, () => {
	if (!locked.value) autosave.queue({ targets: buildTargets() })
})

/**
 * The shared parts, in order, keeping the row a text already had. Content written for one
 * channel stays as it is: the picker and this editor never touch it.
 */
function buildParts(): SocialPostPart[] {
	return ['', ...customized.value].flatMap((channel) => rowsOf(channel))
}

/** One group as rows, keeping the row a text already had so its name and media survive. */
function rowsOf(channel: string): SocialPostPart[] {
	const existing = partsOf(post.doc, channel || null)
	return (groups.value[channel] ?? []).map((part, index) => ({
		...(existing[index] ?? {}),
		channel: channel || null,
		part_no: index + 1,
		text: part.text,
		// The column holds JSON, and the document API stores what it is given.
		media: JSON.stringify(part.media),
	})) as SocialPostPart[]
}

/** A channel that stays keeps its row, so its result and its released parts survive an edit. */
function buildTargets(): SocialPostTarget[] {
	const rows = new Map((post.doc?.targets ?? []).map((target) => [target.channel, target]))
	return picked.value.map((channel) => ({
		...(rows.get(channel) ?? { channel, provider: byName.value[channel]?.provider }),
		use_custom_content: customized.value.includes(channel) ? 1 : 0,
	})) as SocialPostTarget[]
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

watch([groups, picked, customized, () => post.doc?.name], check, { immediate: true })

/**
 * The platform the counter answers to. On a channel's own tab that is the channel; on the
 * shared tab it is whichever of the channels reading the shared text would refuse first.
 */
const strictest = computed(() => {
	// A platform the OS cannot post to yet has no rules to hold the writing to.
	const results = (validation.data ?? []).filter((result) => result.limit > 0)
	if (group.value) return results.find((result) => result.channel === group.value)
	const sharing = results.filter((result) => !result.use_custom_content)
	return (sharing.length ? sharing : results).reduce<TargetValidation | undefined>(
		(tightest, result) => (!tightest || result.limit < tightest.limit ? result : tightest),
		undefined,
	)
})

/** Images stop at the tightest of the platforms picked, as the counter does for text. */
const maxImages = computed(() => strictest.value?.max_images ?? 4)

/** A part after the first takes media only where every platform picked allows it. */
const mediaAfterPartOne = computed(() =>
	group.value
		? Boolean(strictest.value?.media_after_part_one)
		: Boolean(validation.data?.length) && validation.data!.every((result) => result.media_after_part_one),
)

const previews = computed(() =>
	(validation.data ?? []).map((result) => ({
		result,
		channel: byName.value[result.channel],
		parts: groups.value[result.use_custom_content ? result.channel : ''] ?? [],
	})),
)

/** LinkedIn calls part 2 a comment, X calls it a reply. */
const partName = computed(() => {
	const results = group.value
		? (validation.data ?? []).filter((result) => result.channel === group.value)
		: (validation.data ?? [])
	return results.length && results.every((result) => result.provider === 'X') ? 'Reply' : 'Comment'
})

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
