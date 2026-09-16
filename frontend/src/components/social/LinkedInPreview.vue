<template>
	<div class="space-y-2">
		<!-- LinkedIn's own chrome, not the OS's: a preview is worth having only if it looks like the feed.
		     The card sits on the colour LinkedIn puts behind the feed, so it reads as a card there. -->
		<div class="li-canvas rounded-[12px] p-3">
			<div class="li-card overflow-hidden rounded-[10px] border">
				<div class="flex items-start gap-2 px-4 pt-3">
					<img
						v-if="channel?.avatar_url"
						:src="channel.avatar_url"
						alt=""
						class="size-12 rounded-full"
					/>
					<div
						v-else
						class="li-fill grid size-12 shrink-0 place-items-center rounded-full text-base"
					>
						{{ initial }}
					</div>
					<div class="min-w-0 flex-1 leading-[16px]">
						<p class="li-text truncate text-[14px] font-semibold">{{ name }}</p>
						<p class="li-muted truncate pt-0.5 text-[12px]">
							{{ channel?.handle ?? 'Your profile' }}
						</p>
						<p class="li-muted flex items-center gap-1 pt-0.5 text-[12px]">
							Now ·
							<span class="lucide-globe size-3" aria-hidden="true" />
						</p>
					</div>
					<span class="lucide-ellipsis li-muted size-4 shrink-0" aria-hidden="true" />
				</div>

				<p class="li-text whitespace-pre-wrap break-words px-4 pt-3 text-[14px] leading-[20px]">
					<template v-if="text">
						{{ shown.kept }}<span v-if="shown.over" class="li-over">{{ shown.over }}</span
						><button v-if="folded" type="button" class="li-more" @click="expanded = true">
							…see more
						</button>
					</template>
					<span v-else class="li-muted">Your post shows up here.</span>
				</p>

				<div class="li-line mx-4 mt-3 flex items-center justify-between border-t py-1">
					<span v-for="action in ACTIONS" :key="action.label" class="li-action">
						<span :class="[action.icon, 'size-[18px]']" aria-hidden="true" />
						{{ action.label }}
					</span>
				</div>

				<!-- A part after the first becomes a comment under the post, so it sits inside the card. -->
				<div v-if="comments.length" class="li-line border-t px-4 py-3">
					<div
						v-for="(_comment, index) in comments"
						:key="index"
						class="flex gap-2 pt-3 first:pt-0"
					>
						<img
							v-if="channel?.avatar_url"
							:src="channel.avatar_url"
							alt=""
							class="size-8 shrink-0 rounded-full"
						/>
						<div
							v-else
							class="li-fill grid size-8 shrink-0 place-items-center rounded-full text-p-sm"
						>
							{{ initial }}
						</div>
						<div class="li-fill min-w-0 flex-1 rounded-[8px] px-3 py-2">
							<p class="li-text truncate text-[13px] font-semibold">{{ name }}</p>
							<p
								class="li-text whitespace-pre-wrap break-words pt-1 text-[14px] leading-[20px]"
							>
								{{ body(index + 1).kept
								}}<span v-if="body(index + 1).over" class="li-over">{{
									body(index + 1).over
								}}</span>
							</p>
							<p class="li-muted flex gap-2 pt-1.5 text-[12px] font-semibold">
								<span>Like</span>
								<span class="font-normal">·</span>
								<span>Reply</span>
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>

		<p v-for="error in errors" :key="error" class="text-p-sm text-ink-red-3">{{ error }}</p>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SocialChannel } from '@/types'

/** The post as LinkedIn shows it: the feed card, the action bar, then each comment under it. */
const props = withDefaults(
	defineProps<{
		channel?: SocialChannel
		/** Part 1 first */
		texts: string[]
		limit: number
		errors?: string[]
	}>(),
	{ errors: () => [] },
)

// Where LinkedIn folds a feed post behind "see more".
const FOLD = 210

const ACTIONS = [
	{ label: 'Like', icon: 'lucide-thumbs-up' },
	{ label: 'Comment', icon: 'lucide-message-square' },
	{ label: 'Repost', icon: 'lucide-repeat-2' },
	{ label: 'Send', icon: 'lucide-send' },
]

const expanded = ref(false)

const name = computed(() => props.channel?.display_name ?? 'LinkedIn')
const initial = computed(() => name.value.trim().charAt(0).toUpperCase() || 'L')
const text = computed(() => props.texts[0] ?? '')
const comments = computed(() => props.texts.slice(1))

// The fold stays open while you keep writing, and closes again for another channel.
watch(
	() => props.channel?.name,
	() => (expanded.value = false),
)

const folded = computed(() => !expanded.value && text.value.length > FOLD)

/** The body of the post: the fold cuts it first, the limit marks what LinkedIn would drop. */
const shown = computed(() => {
	const full = body(0)
	if (!folded.value) return full
	// LinkedIn folds on a word, not through one, and "…see more" carries on that line.
	const cut = full.kept.slice(0, FOLD)
	const lastSpace = cut.lastIndexOf(' ')
	return { kept: (lastSpace > FOLD - 30 ? cut.slice(0, lastSpace) : cut).trimEnd(), over: '' }
})

/** What the platform would keep, and what falls past its limit. */
function body(index: number): { kept: string; over: string } {
	const value = props.texts[index] ?? ''
	if (!props.limit || value.length <= props.limit) return { kept: value, over: '' }
	return { kept: value.slice(0, props.limit), over: value.slice(props.limit) }
}
</script>

<style scoped>
/* LinkedIn's palette, light and dark, so the card reads as the feed in either theme. */
.li-canvas {
	background: #f4f2ee;
}

:global(:root[data-theme='dark']) .li-canvas {
	background: #000000;
}

.li-card {
	--li-surface: #ffffff;
	--li-border: #e0dfdc;
	--li-ink: rgb(0 0 0 / 0.9);
	--li-ink-muted: rgb(0 0 0 / 0.6);
	--li-fill: #eef3f8;
	background: var(--li-surface);
	border-color: var(--li-border);
	font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

:global(:root[data-theme='dark']) .li-card {
	--li-surface: #1b1f23;
	--li-border: #38434f;
	--li-ink: rgb(255 255 255 / 0.9);
	--li-ink-muted: rgb(255 255 255 / 0.6);
	--li-fill: #293138;
}

.li-text {
	color: var(--li-ink);
}

.li-muted {
	color: var(--li-ink-muted);
}

.li-fill {
	background: var(--li-fill);
	color: var(--li-ink-muted);
}

.li-line {
	border-color: var(--li-border);
}

/* The bar holds four actions in a narrow panel, so it gives each one room and no more. */
.li-action {
	display: flex;
	flex: 1;
	min-width: 0;
	align-items: center;
	justify-content: center;
	gap: 5px;
	padding: 8px 2px;
	font-size: 12px;
	font-weight: 600;
	color: var(--li-ink-muted);
}

/* LinkedIn puts the fold at the end of the line the text stops on, not under it. */
.li-more {
	display: inline;
	color: var(--li-ink-muted);
	font-size: 14px;
}

/* Past the limit LinkedIn keeps nothing, so the preview keeps it in red. */
.li-over {
	background: #ffd7d7;
	color: #7f1d1d;
}
</style>
