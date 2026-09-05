// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	// 参考: https://docs.astro.build/ja/guides/deploy/github/
	site: 'https://kawagh.github.io',
	base: '/redi',
	integrations: [
		starlight({
			title: 'redi',
			// 英語をルート (/) に、日本語を /ja/ に置く
			defaultLocale: 'root',
			locales: {
				root: { label: 'English', lang: 'en' },
				ja: { label: '日本語' },
			},
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/kawagh/redi' }],
			sidebar: [
				{ label: 'Getting Started', translations: { ja: 'はじめに' }, slug: 'getting-started' },
				{ label: 'TUI', slug: 'tui' },
				// ページを足せば並ぶ。ラベルは各ページの title から取られるので言語ごとに正しく出る
				{ label: 'CLI', items: [{ autogenerate: { directory: 'cli' } }] },
				{ label: 'Configuration', translations: { ja: '設定' }, slug: 'configuration' },
			],
		}),
	],
});
