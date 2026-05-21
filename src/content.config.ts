import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const people = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/people' }),
  schema: z.object({
    name: z.string(),
    nameKana: z.string(),
    nameRomaji: z.string(),
    birthDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD 形式で入力'),
    deathDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD 形式で入力'),
    era: z.enum(['江戸', '明治', '大正', '昭和']),
    category: z.enum(['政治家', '文化人', '軍人', '実業家', '学者', 'その他']),
    graveSection: z.string().optional(),
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
  }),
});

export const collections = { people };
