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
      birthPlace: z.string().optional(),
      deathPlace: z.string().optional(),
      jobTitle: z.string().optional(),
      knowsAbout: z.array(z.string()).optional(),
      nationality: z.string().default('JP'),
      alumniOf: z.array(z.string()).optional(),
      honorificSuffix: z.string().optional(),
      award: z.array(z.string()).optional(),
      memberOf: z.array(z.string()).optional(),
      references: z
        .array(
          z.object({
            title: z.string(),
            url: z.string().url(),
          })
        )
        .optional(),
      relatedPeople: z
        .array(
          z.object({
            slug: z.string(),
            relation: z.string().min(1).max(60),
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

const routes = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/routes' }),
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    theme: z.enum([
      '維新',
      '戊辰戦争',
      '坂の上の雲',
      '昭和',
      '太平洋戦争',
      '文人',
      'お雇い外国人',
      '女性とハチ公',
      '軍人',
      '実業家',
      '官僚',
      'その他',
    ]),
    description: z.string().min(40).max(400),
    estimatedMinutes: z.number().int().positive(),
    stops: z
      .array(
        z.object({
          slug: z.string(),
          note: z.string().optional(),
        })
      )
      .min(3),
    order: z.number().int().default(100),
  }),
});

const events = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/events' }),
  schema: z.object({
    title: z.string(),
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'YYYY-MM-DD 形式で入力'),
    summary: z.string().min(10).max(200),
    personSlugs: z.array(z.string()).min(1),
    category: z.enum(['政変', '戦争', '事件', '条約', '内閣', '災害', '社会']),
    url: z.string().url().optional(),
  }),
});

export const collections = { people, works, routes, events };
