<template>
	<div class="space-y-2">
		<!-- X's own chrome, not the OS's. A thread is one column of tweets joined by the line
		     that runs down from each avatar, which is the thing that makes it read as a thread. -->
		<div class="x-canvas rounded-[12px] p-3">
			<div class="x-card overflow-hidden rounded-[10px] border">
				<article v-for="(tweet, index) in tweets" :key="index" class="flex gap-3 px-4 pt-3">
					<div class="flex shrink-0 flex-col items-center">
						<img
							v-if="channel?.avatar_url"
							:src="channel.avatar_url"
							alt=""
							class="size-10 rounded-full"
						/>
						<div
							v-else
							class="x-fill grid size-10 place-items-center rounded-full text-base"
						>
							{{ initial }}
						</div>
						<!-- The line to the next tweet of the thread. -->
						<div v-if="index < tweets.length - 1" class="x-thread mt-1 w-0.5 flex-1" />
					</div>

					<div class="min-w-0 flex-1 pb-3">
						<div class="flex items-center gap-1 text-[15px] leading-[20px]">
							<span class="x-text truncate font-bold">{{ name }}</span>
							<span class="x-muted truncate">{{ handle }}</span>
							<span class="x-muted shrink-0 whitespace-nowrap">· now</span>
							<span class="lucide-ellipsis x-muted ml-auto size-4 shrink-0" aria-hidden="true" />
						</div>

						<p class="x-text whitespace-pre-wrap break-words pt-0.5 text-[15px] leading-[20px]">
							<template v-if="tweet.text">
								{{ shown[index].kept
								}}<span v-if="shown[index].over" class="x-over">{{ shown[index].over }}</span>
							</template>
							<span v-else-if="!index" class="x-muted">Your post shows up here.</span>
						</p>

						<video
							v-if="videoOf(tweet)"
							:src="videoOf(tweet)!.file_url"
							class="mt-3 max-h-[320px] w-full rounded-[16px] bg-black object-contain"
							controls
							preload="metadata"
						/>

						<!-- X lays images out in a rounded frame, two across once there is more than one. -->
						<div
							v-else-if="imagesOf(tweet).length"
							class="x-line mt-3 grid gap-0.5 overflow-hidden rounded-[16px] border"
							:class="imagesOf(tweet).length > 1 ? 'grid-cols-2' : 'grid-cols-1'"
						>
							<img
								v-for="(image, at) in imagesOf(tweet)"
								:key="image.file_url"
								:src="image.file_url"
								alt=""
								class="w-full bg-black/5 object-cover"
								:class="tile(imagesOf(tweet).length, at)"
							/>
						</div>

						<!-- X shows the rule under the first tweet of a conversation it applies to. -->
						<p v-if="!index && replyNote" class="x-muted flex items-center gap-1 pt-3 text-[13px]">
							<span class="lucide-globe size-3.5" aria-hidden="true" />
							{{ replyNote }}
						</p>

						<div class="x-muted flex max-w-[320px] items-center justify-between pt-3">
							<span
								v-for="action in ACTIONS"
								:key="action"
								:class="[action, 'size-[18px]']"
								aria-hidden="true"
							/>
						</div>
					</div>
				</article>
			</div>
		</div>

		<p v-for="error in errors" :key="error" class="text-p-sm text-ink-red-3">{{ error }}</p>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { splitAtLimit } from '@/lib/xText'
import { REPLY_NOTES } from '@/lib/social'
import type { DraftPart } from '@/lib/social'
import type { SocialChannel, SocialMedia, XReplySettings } from '@/types'

/** The post as X shows it: part 1 as the tweet, and each part after it as its reply. */
const props = withDefaults(
	defineProps<{
		channel?: SocialChannel
		/** Part 1 first */
		parts: DraftPart[]
		limit: number
		/** Who the post lets reply, which X prints under the first tweet. */
		replySettings?: XReplySettings
		errors?: string[]
	}>(),
	{ errors: () => [] },
)

const ACTIONS = [
	'lucide-message-circle',
	'lucide-repeat-2',
	'lucide-heart',
	'lucide-chart-no-axes-column',
	'lucide-bookmark',
]

const name = computed(() => props.channel?.display_name ?? 'X')
const handle = computed(() => (props.channel?.handle ? `@${props.channel.handle}` : '@you'))
const initial = computed(() => name.value.trim().charAt(0).toUpperCase() || 'X')
/** An empty post still draws one tweet, so the card is never a blank frame. */
const tweets = computed(() => (props.parts.length ? props.parts : [{ text: '', media: [] }]))

const replyNote = computed(() => REPLY_NOTES[props.replySettings ?? 'everyone'])

/** What X would keep of each tweet, and what falls past 280 weighted characters. */
const shown = computed(() => tweets.value.map((tweet) => splitAtLimit(tweet.text, props.limit)))

function imagesOf(tweet: DraftPart): SocialMedia[] {
	return tweet.media.filter((item) => item.kind === 'image')
}

function videoOf(tweet: DraftPart): SocialMedia | undefined {
	return tweet.media.find((item) => item.kind === 'video')
}

/** Three images put the first down the left of the frame, the way X stacks them. */
function tile(total: number, index: number): string {
	if (total === 1) return 'max-h-[320px] object-contain'
	if (total === 3 && index === 0) return 'row-span-2 h-[240px]'
	return 'h-[120px]'
}
</script>

<style scoped>
/* X's palette, light and dark, so the card reads as the timeline in either theme. */
.x-canvas {
	background: #f7f9f9;
}

:global(:root[data-theme='dark']) .x-canvas {
	background: #000000;
}

.x-card {
	--x-surface: #ffffff;
	--x-border: #eff3f4;
	--x-ink: #0f1419;
	--x-ink-muted: #536471;
	--x-fill: #e1e8ed;
	background: var(--x-surface);
	border-color: var(--x-border);
	font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

:global(:root[data-theme='dark']) .x-card {
	--x-surface: #000000;
	--x-border: #2f3336;
	--x-ink: #e7e9ea;
	--x-ink-muted: #71767b;
	--x-fill: #202327;
}

.x-text {
	color: var(--x-ink);
}

.x-muted {
	color: var(--x-ink-muted);
}

.x-fill {
	background: var(--x-fill);
	color: var(--x-ink-muted);
}

.x-line {
	border-color: var(--x-border);
}

.x-thread {
	background: var(--x-border);
}

/* Past 280 X takes nothing, so the preview keeps it in red. */
.x-over {
	background: #ffd7d7;
	color: #7f1d1d;
}
</style>
