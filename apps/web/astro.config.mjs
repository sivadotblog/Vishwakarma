// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	site: 'https://sivadotblog.github.io',
	base: '/vishwakarma',
	integrations: [
		starlight({
			title: 'Vishwakarma',
			social: [
				{
					icon: 'github',
					label: 'GitHub',
					href: 'https://github.com/sivadotblog/vishwakarma',
				},
			],
			sidebar: [
				{
					label: 'Guides',
					items: [
						// Each item here is one entry in the navigation menu.
						{ label: 'Getting started', slug: 'guides/getting-started' },
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
