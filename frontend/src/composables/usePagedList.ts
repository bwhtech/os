import { computed, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'
import { useCall } from 'frappe-ui'

export const PAGE_LENGTHS = [20, 50, 100]

type ListParams = { fields: string; filters: string; order_by: string; start: number; limit: number }
type CountParams = { doctype: string; filters: string }

interface PagedListOptions {
	doctype: string
	fields: unknown[]
	filters: MaybeRefOrGetter<Record<string, unknown>>
	orderBy: string
	pageLength?: number
}

/**
 * One page of a list, and the total count for the pager. frappe-ui `useList` appends pages for
 * "load more", so this reads the v2 list endpoint one page at a time. A filter change goes to page 1.
 */
export function usePagedList<T>(options: PagedListOptions) {
	const page = ref(1)
	const pageLength = ref(options.pageLength ?? PAGE_LENGTHS[1])
	const filters = computed(() => JSON.stringify(toValue(options.filters)))

	const rows = useCall<T[], ListParams>({
		url: `/api/v2/document/${options.doctype}`,
		params: () => ({
			fields: JSON.stringify(options.fields),
			filters: filters.value,
			order_by: options.orderBy,
			start: (page.value - 1) * pageLength.value,
			limit: pageLength.value,
		}),
		refetch: true,
	})

	const count = useCall<number, CountParams>({
		url: '/api/v2/method/bwh_os.api.get_count',
		params: () => ({ doctype: options.doctype, filters: filters.value }),
		refetch: true,
	})

	watch([filters, pageLength], () => {
		page.value = 1
	})

	return {
		rows,
		page,
		pageLength,
		total: computed(() => count.data ?? 0),
		reload() {
			rows.reload()
			count.reload()
		},
	}
}
