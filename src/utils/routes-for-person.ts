import { getCollection, type CollectionEntry } from 'astro:content';

export type Route = CollectionEntry<'routes'>;

export async function getRoutesForPerson(personSlug: string): Promise<Route[]> {
  const routes = await getCollection('routes');
  return routes
    .filter((r) => r.data.stops.some((s) => s.slug === personSlug))
    .sort((a, b) => a.data.order - b.data.order);
}
