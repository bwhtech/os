import { createApp } from 'vue'
import { FrappeUI, call, setConfig } from 'frappe-ui'
import App from './App.vue'
import router from './router'
import './style.css'

/**
 * In production the jinjaBootData plugin writes the boot dict from
 * `bwh_os/www/os.py` onto `window`. The dev server serves `index.html` as is,
 * so fetch the same dict over the API instead.
 */
async function loadDevBootData() {
	if (!import.meta.env.DEV) return
	try {
		const boot = await call<Record<string, unknown>>('bwh_os.www.os.get_context_for_dev')
		Object.assign(window, boot)
	} catch {
		// Only available in developer mode. The app runs without it.
	}
}

async function start() {
	await loadDevBootData()
	setConfig('systemTimezone', window.system_timezone ?? null)

	const app = createApp(App)
	app.use(router)
	app.use(FrappeUI)
	app.mount('#app')
}

start()
