import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const people = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/people' }),
  schema: ({ image }) =>
    z.object({
      name: z.string(),
      nameKana: z.string(),
      nameRomaji: z.string(),
      birthDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD 形式で入力'),
      deathDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD 形式で入力'),
      era: z.array(z.enum(['江戸', '明治', '大正', '昭和'])).min(1).max(2),
      category: z.enum(['政治家', '文化人', '軍人', '実業家', '学者', 'その他']),
      graveSection: z.string().optional(),
      coords: z
        .object({
          lat: z.number().gte(35.66).lte(35.68),
          lng: z.number().gte(139.71).lte(139.73),
        })
        .optional(),
      hideMap: z.boolean().optional(),
      mapQuery: z.string().optional(),
      shortDescription: z.string().min(20).max(100),
      tags: z.array(z.string()).optional(),
      references: z
        .array(
          z.object({
            title: z.string(),
            url: z.string().url(),
          })
        )
        .optional(),
      ogImage: z.string().optional(),
      portrait: image().optional(),
      portraitCaption: z.string().optional(),
      portraitCredit: z.string().optional(),
    }),
});

const works = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/works' }),
  schema: z.object({
    title: z.string(),
    type: z.enum(['小説', '映画', '漫画', 'ドラマ', 'NHK大河', '研究本', '評伝', '代表作', 'その他']),
    creator: z.string(),
    year: z.union([z.number(), z.string()]).optional(),
    publisher: z.string().optional(),
    personSlugs: z.array(z.string()).min(1),
    url: z.string().url().optional(),
  }),
});

export const collections = { people, works };
