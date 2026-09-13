/// <reference types="vite/client" />

declare global {
	interface Window {
		/** Injected by `bwh_os/www/os.py` boot data. */
		csrf_token?: string
		site_name?: string
		system_timezone?: string
		frappe_version?: string
		read_only_mode?: boolean
		socketio_port?: number
	}
}

export {}
