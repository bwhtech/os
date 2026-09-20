<template>
	<Dialog :open="open" title="Send Lead Magnet" size="2xl" @update:open="onOpenChange">
		<template #default="{ close }">
			<div class="space-y-4">
				<p class="text-p-base text-ink-gray-6">
					Sends {{ leadMagnetTitle }} right away, to existing subscribers. There is no hourly
					batching — for a bigger list, use a newsletter instead.
				</p>

				<TabButtons v-model="pick" :options="PICK_OPTIONS" />
				<SubscriberPicker v-if="pick === 'subscribers'" v-model="subscribers" />
				<TagPicker
					v-else
					v-model="tags"
					description="Active subscribers with any of these tags."
				/>

				<Switch
					v-model="skipDownloaded"
					label="Skip people who already downloaded it"
				/>

				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<NumberCard v-bind="recipientsCard" />
					<NumberCard v-bind="alreadyHaveCard" />
				</div>

				<ErrorMessage :message="errorMessage(sendCall.error)" />

				<div class="flex justify-end gap-2 pt-2">
					<Button label="Cancel" @click="close" />
					<Button
						variant="solid"
						theme="gray"
						icon-left="lucide-send"
						:label="submitLabel"
						:loading="sendCall.loading"
						:disabled="!canSend"
						@click="submit(close)"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, Switch, TabButtons, debounce, toast, useCall } from 'frappe-ui'
import { NumberCard, type NumberCardProps } from 'frappe-ui/charts'
import SubscriberPicker from '@/components/subscribers/SubscriberPicker.vue'
import TagPicker from '@/components/tags/TagPicker.vue'
import { errorMessage } from '@/lib/errors'
import type { LeadMagnetRecipients } from '@/types'

const props = defineProps<{
	open: boolean
	leadMagnetId: string
	leadMagnetTitle: string
}>()
const emit = defineEmits<{ 'update:open': [open: boolean]; sent: [] }>()

const PICK_OPTIONS = [
	{ label: 'Subscribers', value: 'subscribers' },
	{ label: 'Tag', value: 'tags' },
]

const pick = ref<'subscribers' | 'tags'>('subscribers')
const subscribers = ref<string[]>([])
const tags = ref<string[]>([])
const skipDownloaded = ref(true)

function onOpenChange(value: boolean) {
	emit('update:open', value)
	if (!value) return
	sendCall.reset()
	pick.value = 'subscribers'
	subscribers.value = []
	tags.value = []
	skipDownloaded.value = true
}

/** What is picked, before the send: subscriber names, or a tag. */
function picks() {
	return {
		subscribers: pick.value === 'subscribers' ? subscribers.value : [],
		tags: pick.value === 'tags' ? tags.value : [],
	}
}

const params = ref(toPreviewParams())
watch(
	[pick, subscribers, tags, skipDownloaded],
	debounce(() => {
		params.value = toPreviewParams()
	}, 300),
	{ deep: true },
)

// GET sends a list as "a,b", so the preview carries subscribers and tags as JSON strings.
// The POST body below carries the same picks as real arrays — send_lead_magnet takes a list.
function toPreviewParams() {
	const { subscribers, tags } = picks()
	return {
		lead_magnet: props.leadMagnetId,
		subscribers: JSON.stringify(subscribers),
		tags: JSON.stringify(tags),
		skip_downloaded: skipDownloaded.value ? 1 : 0,
	}
}

const preview = useCall<LeadMagnetRecipients, ReturnType<typeof toPreviewParams>>({
	url: '/api/v2/method/bwh_os.mailing.api.get_lead_magnet_recipients',
	method: 'GET',
	params: () => params.value,
	refetch: true,
})

const recipients = computed(() => preview.data?.recipients ?? 0)
const limit = computed(() => preview.data?.limit ?? 50)
const picked = computed(() => (pick.value === 'subscribers' ? subscribers.value.length : tags.value.length))

const canSend = computed(() => picked.value > 0 && recipients.value > 0 && recipients.value <= limit.value)

const submitLabel = computed(() => {
	if (recipients.value > limit.value) return `Pick at most ${limit.value}`
	return `Send to ${recipients.value} ${recipients.value === 1 ? 'subscriber' : 'subscribers'}`
})

const recipientsCard = computed<NumberCardProps>(() => ({
	title: 'Recipients',
	value: picked.value ? recipients.value : null,
	deltaCaption:
		recipients.value > limit.value
			? `Over the limit of ${limit.value}`
			: 'Active subscribers, at once',
	loading: preview.loading && !preview.data,
}))

const alreadyHaveCard = computed<NumberCardProps>(() => ({
	title: 'Already have it',
	value: picked.value ? (preview.data?.already_downloaded ?? null) : null,
	deltaCaption: skipDownloaded.value ? 'Left out of the send' : 'Sent it again anyway',
	loading: preview.loading && !preview.data,
}))

function toSendParams() {
	return {
		lead_magnet: props.leadMagnetId,
		...picks(),
		skip_downloaded: skipDownloaded.value ? 1 : 0,
	}
}

const sendCall = useCall<{ sent: number; failed: string[] }, ReturnType<typeof toSendParams>>({
	url: '/api/v2/method/bwh_os.mailing.api.send_lead_magnet',
	method: 'POST',
	immediate: false,
})

async function submit(close: () => void) {
	const result = await sendCall.submit(toSendParams())
	if (!result) return
	toast.success(
		result.failed.length
			? `Sent to ${result.sent}, ${result.failed.length} failed`
			: `Sent to ${result.sent} ${result.sent === 1 ? 'subscriber' : 'subscribers'}`,
	)
	emit('sent')
	close()
}
</script>
