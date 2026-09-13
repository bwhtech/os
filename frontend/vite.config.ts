import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import react from '@vitejs/plugin-react'
import frappeui from 'frappe-ui/vite'

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: '/os',
			frappeProxy: { port: 8000 },
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				indexHtmlPath: '../bwh_os/www/os.html',
				outDir: '../bwh_os/public/frontend',
				baseUrl: '/assets/bwh_os/frontend/',
			},
		}),
		vue(),
		// Only the newsletter editor uses React.
		react({ include: /\.tsx$/ }),
	],
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
		// @react-email/editor pins a newer TipTap than frappe-ui. Two copies break ProseMirror.
		dedupe: ['@tiptap/core', '@tiptap/pm'],
	},
	optimizeDeps: {
		// frappe-ui ships unbuilt source with `~icons/lucide/*` virtual imports
		// that esbuild's prebundler cannot resolve.
		exclude: ['frappe-ui'],
		// CJS deps that still need converting once frappe-ui is not prebundled.
		include: ['tippy.js', 'engine.io-client', 'socket.io-client', 'debug'],
	},
})
