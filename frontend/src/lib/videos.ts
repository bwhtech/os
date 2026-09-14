import type { Video, VideoStatus } from '@/types'

/** In the order a video moves through them. The same list as the `status` Select of `BWH Video`. */
export const STATUSES: VideoStatus[] = [
	'Idea',
	'Researching',
	'Scripting',
	'Recording',
	'Editing',
	'Thumbnail Pending',
	'Published',
]

export const IN_PROGRESS = STATUSES.filter((status) => status !== 'Published')

/** Blue while writing, amber while producing, green when out. */
const DOTS: Record<VideoStatus, string> = {
	Idea: 'bg-surface-gray-5',
	Researching: 'bg-surface-blue-7',
	Scripting: 'bg-surface-blue-7',
	Recording: 'bg-surface-amber-7',
	Editing: 'bg-surface-amber-7',
	'Thumbnail Pending': 'bg-surface-amber-7',
	Published: 'bg-surface-green-7',
}

const THEMES: Record<VideoStatus, 'gray' | 'blue' | 'orange' | 'green'> = {
	Idea: 'gray',
	Researching: 'blue',
	Scripting: 'blue',
	Recording: 'orange',
	Editing: 'orange',
	'Thumbnail Pending': 'orange',
	Published: 'green',
}

export function statusDot(status: VideoStatus): string {
	return DOTS[status] ?? DOTS.Idea
}

export function statusTheme(status: VideoStatus) {
	return THEMES[status] ?? 'gray'
}

/** A video in a series opens inside the series, with the series sidebar. */
export function videoRoute(video: Pick<Video, 'name' | 'series'>): string {
	return video.series ? `/series/${video.series}/videos/${video.name}` : `/videos/${video.name}`
}

export const VIDEO_DOCTYPES = ['BWH Video', 'BWH Video Series']

