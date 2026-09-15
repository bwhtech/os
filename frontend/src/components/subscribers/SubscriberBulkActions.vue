<template>
	<Dropdown v-if="compact" :options="mobileOptions" align="end">
		<Button variant="ghost" size="md" icon="lucide-ellipsis" aria-label="Actions for selected" />
	</Dropdown>
	<template v-else>
		<Button variant="ghost" label="Clear" @click="emit('clear')" />
		<Dropdown :options="desktopOptions" align="end">
			<Button label="Change status" icon-left="lucide-circle-dot" icon-right="lucide-chevron-down" />
		</Dropdown>
		<Button theme="red" label="Delete" icon-left="lucide-trash-2" @click="confirmDelete" />
	</template>
</template>

<script setup lang="ts">
import { Button, Dropdown, dialog, toast, useCall, type DropdownOptions } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { SubscriberStatus } from '@/types'

const STATUSES: SubscriberStatus[] = ['Active', 'Pending', 'Unsubscribed', 'Bounced']

const props = defineProps<{
	names: string[]
	/** One menu button for the narrow mobile header. */
	compact?: boolean
}>()

const emit = defineEmits<{
	/** The selected subscribers changed or went away. */
	done: []
	clear: []
}>()

const setStatus = useCall<number, { names: string[]; status: SubscriberStatus }>({
	url: '/api/v2/method/bwh_os.mailing.api.set_subscriber_status',
	method: 'POST',
	immediate: false,
})

const deleteSubscribers = useCall<{ deleted: string[]; kept: string[] }, { names: string[] }>({
	url: '/api/v2/method/bwh_os.mailing.api.delete_subscribers',
	method: 'POST',
	immediate: false,
})

const statusOptions = STATUSES.map((status) => ({ label: status, onClick: () => changeStatus(status) }))

const desktopOptions: DropdownOptions = [{ group: 'Mark as', options: statusOptions }]

const mobileOptions: DropdownOptions = [
	{ label: 'Mark as', icon: 'lucide-circle-dot', submenu: statusOptions },
	{ label: 'Clear selection', icon: 'lucide-x', onClick: () => emit('clear') },
	{ label: 'Delete', icon: 'lucide-trash-2', theme: 'red', onClick: () => confirmDelete() },
]

async function changeStatus(status: SubscriberStatus) {
	const changed = await setStatus.submit({ names: props.names, status })
	if (changed === null) {
		toast.error(errorMessage(setStatus.error))
		return
	}
	toast.success(`${plural(changed)} marked ${status}`)
	emit('done')
}

function confirmDelete() {
	dialog.danger({
		title: `Delete ${plural(props.names.length)}?`,
		message: 'This cannot be undone. To stop sending to someone, mark them Unsubscribed instead.',
		onConfirm: async () => {
			const result = await deleteSubscribers.submit({ names: props.names })
			// Throwing shows the error in the dialog.
			if (!result) throw new Error(errorMessage(deleteSubscribers.error))
			const { deleted, kept } = result
			if (kept.length) {
				toast.info(`Deleted ${plural(deleted.length)}. Kept ${plural(kept.length)} with newsletter or download history.`)
			} else {
				toast.success(`Deleted ${plural(deleted.length)}`)
			}
			emit('done')
		},
	})
}

function plural(n: number) {
	return `${n} ${n === 1 ? 'subscriber' : 'subscribers'}`
}
</script>
