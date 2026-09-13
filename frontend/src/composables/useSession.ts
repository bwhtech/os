import { computed, watch } from 'vue'
import { call, useCall, useDoc } from 'frappe-ui'

interface SessionUser {
	name: string
	full_name: string
	user_image: string | null
}

/** The logged-in user. A module singleton, so every caller shares one request. */
let session: ReturnType<typeof createSession> | null = null

export function useSession() {
	if (!session) session = createSession()
	return session
}

/** Resolve the session once for the router guard. `''` means Guest. */
export function resolveLoggedUser(): Promise<string> {
	const { userId, ready } = useSession()
	if (ready.value) return Promise.resolve(userId.value)
	return new Promise((resolve) => {
		const stop = watch(ready, (value) => {
			if (!value) return
			stop()
			resolve(userId.value)
		})
	})
}

function createSession() {
	const loggedUser = useCall<string>({
		url: '/api/v2/method/frappe.auth.get_logged_user',
		method: 'GET',
	})

	const userId = computed(() => {
		const value = loggedUser.data
		return value && value !== 'Guest' ? value : ''
	})

	const userDoc = useDoc<SessionUser>({ doctype: 'User', name: userId })

	const ready = computed(() => Boolean(loggedUser.isFinished || loggedUser.error))

	async function logout() {
		try {
			await call('logout')
		} finally {
			window.location.href = '/login'
		}
	}

	return { userId, user: computed(() => userDoc.doc), ready, logout }
}
