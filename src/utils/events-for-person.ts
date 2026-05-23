import { getCollection, type CollectionEntry } from 'astro:content';

export type Event = CollectionEntry<'events'>;

export async function getEventsForPerson(personSlug: string): Promise<Event[]> {
  const events = await getCollection('events');
  return events
    .filter((e) => e.data.personSlugs.includes(personSlug))
    .sort((a, b) => a.data.date.localeCompare(b.data.date));
}
