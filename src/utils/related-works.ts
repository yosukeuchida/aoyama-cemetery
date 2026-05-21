import { getCollection, type CollectionEntry } from 'astro:content';

export type Work = CollectionEntry<'works'>;

const TYPE_ORDER: Record<string, number> = {
  代表作: 1,
  小説: 2,
  評伝: 3,
  研究本: 4,
  漫画: 5,
  映画: 6,
  ドラマ: 7,
  NHK大河: 8,
  その他: 9,
};

export async function getWorksForPerson(personSlug: string): Promise<Work[]> {
  const all = await getCollection('works');
  const filtered = all.filter((w) => w.data.personSlugs.includes(personSlug));

  filtered.sort((a, b) => {
    const ta = TYPE_ORDER[a.data.type] ?? 99;
    const tb = TYPE_ORDER[b.data.type] ?? 99;
    if (ta !== tb) return ta - tb;
    const ya = typeof a.data.year === 'number' ? a.data.year : parseInt(String(a.data.year ?? '0'), 10);
    const yb = typeof b.data.year === 'number' ? b.data.year : parseInt(String(b.data.year ?? '0'), 10);
    return ya - yb;
  });

  return filtered;
}
