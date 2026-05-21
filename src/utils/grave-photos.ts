import type { ImageMetadata } from 'astro';

export interface GravePhoto {
  date: string;
  caption: string | null;
  image: ImageMetadata;
}

const FILENAME_RE = /^(\d{4}-\d{2}-\d{2})(?:-(.+))?\.(jpg|jpeg|png|webp)$/i;

const modules = import.meta.glob<{ default: ImageMetadata }>(
  '/src/assets/grave-photos/*/*.{jpg,jpeg,png,webp,JPG,JPEG,PNG,WEBP}',
  { eager: true }
);

const bySlug: Map<string, GravePhoto[]> = (() => {
  const map = new Map<string, GravePhoto[]>();
  for (const [path, mod] of Object.entries(modules)) {
    const parts = path.split('/');
    const filename = parts[parts.length - 1];
    const slug = parts[parts.length - 2];
    const match = FILENAME_RE.exec(filename);
    if (!match) {
      console.warn(
        `[grave-photos] skipped invalid filename: ${path} (expected YYYY-MM-DD[-caption].{jpg|jpeg|png|webp})`
      );
      continue;
    }
    const [, date, captionRaw] = match;
    const caption = captionRaw ? captionRaw.replace(/-/g, ' ').trim() : null;
    const list = map.get(slug) ?? [];
    list.push({ date, caption, image: mod.default });
    map.set(slug, list);
  }
  for (const list of map.values()) {
    list.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  }
  return map;
})();

export function getGravePhotos(slug: string): GravePhoto[] {
  return bySlug.get(slug) ?? [];
}
