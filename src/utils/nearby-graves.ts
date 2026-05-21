import { getCollection, type CollectionEntry } from 'astro:content';

export type Person = CollectionEntry<'people'>;

const BLOCK_RE = /^(\d+種[イロ]\d+号)/;

export function extractBlock(graveSection: string | undefined): string | null {
  if (!graveSection) return null;
  const m = graveSection.match(BLOCK_RE);
  return m ? m[1] : null;
}

export async function getNearbyPeople(person: Person): Promise<{
  block: string | null;
  nearby: Person[];
}> {
  const block = extractBlock(person.data.graveSection);
  if (!block) return { block: null, nearby: [] };

  const all = await getCollection('people');
  const nearby = all
    .filter((p) => p.id !== person.id && extractBlock(p.data.graveSection) === block)
    .sort((a, b) => a.data.name.localeCompare(b.data.name, 'ja'));

  return { block, nearby };
}
