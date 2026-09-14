import { onScopeDispose } from 'vue'
import { io, type Socket } from 'socket.io-client'

/**
 * Frappe realtime over socket.io. frappe-ui 1.0 does not open a connection,
 * so the app keeps one lazy socket for all listeners.
 *
 * The namespace must be the site name, or the server rejects the connection
 * and no event arrives.
 */
let socket: Socket | null = null

export function getSocket(): Socket {
	socket ??= io(socketUrl(), { withCredentials: true, reconnectionAttempts: 5 })
	return socket
}

/** Listen to a `frappe.publish_realtime` event while the current scope lives. */
export function onRealtime<T>(event: string, handler: (payload: T) => void) {
	const listener = (payload: T) => handler(payload)
	getSocket().on(event, listener)
	onScopeDispose(() => {
		getSocket().off(event, listener)
	})
}

/**
 * Call `handler` when a document of one of the doctypes is saved or deleted.
 * Frappe sends `list_update` only to the room of the doctype, so join it, and
 * join again after a reconnect because the server forgets the rooms.
 */
export function onListUpdate(doctypes: string[], handler: (doctype: string) => void) {
	const subscribe = () => doctypes.forEach((doctype) => getSocket().emit('doctype_subscribe', doctype))
	subscribe()
	getSocket().on('connect', subscribe)
	onRealtime<{ doctype: string }>('list_update', ({ doctype }) => {
		if (doctypes.includes(doctype)) handler(doctype)
	})
	onScopeDispose(() => {
		getSocket().off('connect', subscribe)
		doctypes.forEach((doctype) => getSocket().emit('doctype_unsubscribe', doctype))
	})
}

function socketUrl() {
	const { hostname, port, protocol } = window.location
	const siteName = window.site_name ?? hostname
	// A port in the URL means `bench start` or vite, where socket.io has its own port.
	if (port) return `http://${hostname}:${window.socketio_port ?? 9000}/${siteName}`
	return `${protocol}//${hostname}/${siteName}`
}
