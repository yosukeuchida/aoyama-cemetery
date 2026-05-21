// @ts-check
import { defineConfig } from 'astro/config';

import sitemap from '@astrojs/sitemap';
import remarkLinkPeople from './plugins/remark-link-people.mjs';

// https://astro.build/config
export default defineConfig({
  site: 'https://aoyama-cemetery.pages.dev',
  integrations: [sitemap()],
  markdown: {
    remarkPlugins: [remarkLinkPeople],
  },
});