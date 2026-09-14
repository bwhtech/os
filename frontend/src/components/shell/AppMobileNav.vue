<template>
	<MobileNav>
		<MobileNavItem
			v-for="tab in MOBILE_TABS"
			:key="tab.to"
			:label="tab.label"
			:icon="tab.icon"
			:to="tab.to"
			:active="route.path.startsWith(tab.to)"
		/>
		<MobileNavItem label="More" :active="moreOpen || !onTab" @click="moreOpen = true">
			<template #default="{ active }">
				<Avatar
					size="sm"
					:image="user?.user_image ?? undefined"
					:label="user?.full_name ?? ''"
					:class="{ 'ring-2 ring-outline-gray-4 ring-offset-1': active }"
				/>
			</template>
		</MobileNavItem>
	</MobileNav>

	<!-- Everything the desktop sidebar holds. -->
	<BottomSheet v-model:open="moreOpen">
		<div
			class="space-y-5 px-4 pb-6 [@media(display-mode:standalone)]:pb-[calc(1.5rem+env(safe-area-inset-bottom))]"
		>
			<div class="flex items-center gap-3 px-2">
				<Avatar size="xl" :image="user?.user_image ?? undefined" :label="user?.full_name ?? ''" />
				<div class="min-w-0">
					<p class="truncate text-lg-semibold text-ink-gray-9">{{ user?.full_name ?? '…' }}</p>
					<p class="truncate text-md text-ink-gray-5">{{ user?.email }}</p>
				</div>
			</div>

			<section v-for="section in SECTIONS" :key="section.label">
				<h2 class="px-2 pb-1 text-sm-medium text-ink-gray-5">{{ section.label }}</h2>
				<RouterLink
					v-for="item in section.items"
					:key="item.to"
					:to="item.to"
					:class="[ROW, 'text-ink-gray-8', route.path.startsWith(item.to) && 'bg-surface-gray-2']"
				>
					<span :class="[item.icon, 'size-5 shrink-0 text-ink-gray-6']" aria-hidden="true" />
					{{ item.label }}
				</RouterLink>
			</section>

			<section class="border-t border-outline-gray-1 pt-3">
				<button
					v-for="action in ACTIONS"
					:key="action.label"
					type="button"
					:class="[ROW, 'w-full', action.class]"
					@click="action.onClick"
				>
					<span :class="[action.icon, 'size-5 shrink-0']" aria-hidden="true" />
					{{ action.label }}
				</button>
			</section>
		</div>
	</BottomSheet>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Avatar, BottomSheet, MobileNav, MobileNavItem } from 'frappe-ui'
import { useSession } from '@/composables/useSession'
import { MOBILE_TABS, SECTIONS } from '@/lib/navigation'

const emit = defineEmits<{ 'open-settings': [] }>()

const ROW = 'flex h-12 items-center gap-3 rounded-lg px-2 text-left text-lg active:bg-surface-gray-2'

const route = useRoute()
const { user, logout } = useSession()
const moreOpen = ref(false)

const onTab = computed(() => MOBILE_TABS.some((tab) => route.path.startsWith(tab.to)))

const ACTIONS = [
	{
		label: 'Settings',
		icon: 'lucide-settings',
		class: 'text-ink-gray-8',
		onClick: () => {
			moreOpen.value = false
			emit('open-settings')
		},
	},
	{
		label: 'Desk',
		icon: 'lucide-app-window',
		class: 'text-ink-gray-8',
		onClick: () => {
			window.location.href = '/desk'
		},
	},
	{ label: 'Log out', icon: 'lucide-log-out', class: 'text-ink-red-6', onClick: () => logout() },
]

// A tapped link navigates, so the sheet gets out of the way.
watch(
	() => route.fullPath,
	() => {
		moreOpen.value = false
	}
)
</script>
