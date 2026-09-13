// Ambient module declarations. Keep this file free of top-level imports and exports.

// frappe-ui imports lucide glyphs through `unplugin-icons` virtual modules.
declare module '~icons/*' {
	import type { FunctionalComponent, SVGAttributes } from 'vue'
	const component: FunctionalComponent<SVGAttributes>
	export default component
}
