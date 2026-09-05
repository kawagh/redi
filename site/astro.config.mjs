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
				{
					label: 'Guides',
					translations: { ja: 'ガイド' },
					items: [
						{
							label: 'Getting Started',
							translations: { ja: 'はじめに' },
							slug: 'guides/getting-started',
						},
					],
				},
				{
					label: 'Reference',
					translations: { ja: 'リファレンス' },
					items: [{ autogenerate: { directory: 'reference' } }],
				},
			],
		}),
	],
});
