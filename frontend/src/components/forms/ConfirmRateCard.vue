<template>
	<NumberCard
		title="Confirm rate"
		:value="confirmations.data?.confirm_rate ?? null"
		suffix="%"
		:delta-caption="caption"
		:loading="confirmations.loading && !confirmations.data"
		:error="confirmations.error ? errorMessage(confirmations.error) : null"
	/>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCall } from 'frappe-ui'
import { NumberCard } from 'frappe-ui/charts'
import { errorMessage } from '@/lib/errors'
import type { FormConfirmations } from '@/types'

/** How many people from a double opt-in form clicked the confirm link. */
const props = defineProps<{ formId: string }>()

const confirmations = useCall<FormConfirmations, { form_id: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.get_form_confirmations',
	method: 'GET',
	params: () => ({ form_id: props.formId }),
	refetch: true,
})

const caption = computed(() => {
	const data = confirmations.data
	if (!data) return ''
	return `${data.confirmed} of ${data.signups} signups confirmed`
})
</script>
