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
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/kawagh/redi' }],
			sidebar: [
				{
					label: 'Guides',
					items: [
						// Each item here is one entry in the navigation menu.
						{ label: 'Getting Started', slug: 'guides/getting-started' },
					],
				},
				{
					label: 'Reference',
					items: [{ autogenerate: { directory: 'reference' } }],
				},
			],
		}),
	],
});
