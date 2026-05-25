import { getCollection, type CollectionEntry } from 'astro:content';

export type Person = CollectionEntry<'people'>;

const BLOCK_RE = /^(\d+種[イロ]\d+号)/;

export function extractBlock(graveSection: string | undefined): string | null {
  if (!graveSection) return null;
  // 立山墓地は本園と独立して同じ番地表記が存在するため(例: 立山墓地と本園の双方に「1種イ1号3側」が存在)、
  // graveSection に「立山」を含む偉人はすべて単一の「立山墓地」ブロックとして扱い、本園と混同しない
  if (graveSection.includes('立山')) return '立山墓地';
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
