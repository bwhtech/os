<template>
	<!-- The mobile header centers the current page and goes back to its parent. -->
	<PageHeaderMobile v-if="isMobile" :title="mobileTitle">
		<template v-if="backTo" #prefix>
			<PageHeaderBackButton :fallback-route="backTo" />
		</template>
		<template v-if="slots['mobile-actions'] || slots.actions" #suffix>
			<div class="flex items-center gap-1">
				<slot name="mobile-actions">
					<slot name="actions" />
				</slot>
			</div>
		</template>
	</PageHeaderMobile>

	<PageHeader v-else>
		<div class="flex min-w-0 flex-1 items-center gap-2">
			<Breadcrumbs v-if="breadcrumbs" :items="breadcrumbs" />
			<PageHeaderTitle v-else class="min-w-0">
				<h1 class="truncate">{{ title }}</h1>
			</PageHeaderTitle>
			<slot name="title-suffix" />
		</div>
		<div v-if="slots.actions" class="flex shrink-0 gap-2">
			<slot name="actions" />
		</div>
	</PageHeader>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'
import {
	Breadcrumbs,
	PageHeader,
	PageHeaderBackButton,
	PageHeaderMobile,
	PageHeaderTitle,
} from 'frappe-ui'
import type { RouteLocationRaw } from 'vue-router'
import { useIsMobile } from '@/composables/useIsMobile'

interface Crumb {
	label: string
	route?: RouteLocationRaw
}

/** A page gives a `title`, or `breadcrumbs` when it sits under a list page. */
const props = defineProps<{
	title?: string
	breadcrumbs?: Crumb[]
}>()

defineSlots<{
	/** Page actions. Mobile uses them too, unless `mobile-actions` is given. */
	actions?: () => any
	/** Compact actions for the narrow mobile header, such as icon buttons or a menu. */
	'mobile-actions'?: () => any
	/** Desktop only, next to the title. */
	'title-suffix'?: () => any
}>()

const slots = useSlots()
const isMobile = useIsMobile()

const mobileTitle = computed(() => props.breadcrumbs?.at(-1)?.label ?? props.title)
const backTo = computed(() => props.breadcrumbs?.at(-2)?.route)
</script>
