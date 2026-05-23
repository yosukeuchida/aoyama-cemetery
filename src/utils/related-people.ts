import { getCollection, type CollectionEntry } from 'astro:content';

export type Person = CollectionEntry<'people'>;

export interface ResolvedRelatedPerson {
  person: Person;
  relation: string;
}

export async function getRelatedPeopleFor(person: Person): Promise<ResolvedRelatedPerson[]> {
  const list = person.data.relatedPeople;
  if (!list || list.length === 0) return [];

  const all = await getCollection('people');
  const bySlug = new Map(all.map((p) => [p.id, p]));

  const resolved: ResolvedRelatedPerson[] = [];
  for (const entry of list) {
    const target = bySlug.get(entry.slug);
    if (!target) {
      console.warn(`[relatedPeople] ${person.id}: unknown slug "${entry.slug}" — skipping`);
      continue;
    }
    resolved.push({ person: target, relation: entry.relation });
  }
  return resolved;
}
