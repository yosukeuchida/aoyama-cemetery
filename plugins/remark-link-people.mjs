import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { visit, SKIP } from 'unist-util-visit';

const PEOPLE_DIR = 'src/content/people';
const EVENTS_DIR = 'src/content/events';

function readFrontmatterField(text, field) {
  const m = text.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return undefined;
  const re = new RegExp(`^${field}:\\s*(.+)$`, 'm');
  const fm = m[1].match(re);
  if (!fm) return undefined;
  return fm[1].trim().replace(/^["']|["']$/g, '');
}

function buildPeopleIndex() {
  const files = readdirSync(PEOPLE_DIR).filter((f) => f.endsWith('.md'));
  const seen = new Map();
  for (const f of files) {
    const slug = f.replace(/\.md$/, '');
    const text = readFileSync(join(PEOPLE_DIR, f), 'utf8');
    const name = readFrontmatterField(text, 'name');
    if (!name) continue;
    const variants = new Set([name, name.replace(/\s+/g, '')]);
    for (const v of variants) {
      if (v.length < 2) continue;
      if (!seen.has(v)) seen.set(v, { slug, kind: 'people' });
    }
  }
  return seen;
}

function buildEventsIndex() {
  const files = readdirSync(EVENTS_DIR).filter((f) => f.endsWith('.md'));
  const seen = new Map();
  for (const f of files) {
    const slug = f.replace(/\.md$/, '');
    const text = readFileSync(join(EVENTS_DIR, f), 'utf8');
    const title = readFrontmatterField(text, 'title');
    if (!title) continue;
    const variants = new Set([title]);
    // 「○○○(△△△)」型: 括弧前後の両方を別名としてリンク可能にする
    const parenMatch = title.match(/^([^((]+)[((](.+?)[))]/);
    if (parenMatch) {
      const prefix = parenMatch[1].trim();
      const inside = parenMatch[2].trim();
      if (prefix.length >= 3) variants.add(prefix);
      if (inside.length >= 3) variants.add(inside);
    }
    // 「○○○・△△△」型: 中点分割した各パートも別名としてリンク可能に
    if (title.includes('・')) {
      for (const part of title.split('・')) {
        const trimmed = part.replace(/[((].*?[))]/g, '').trim();
        if (trimmed.length >= 3) variants.add(trimmed);
      }
    }
    for (const v of variants) {
      if (v.length < 3) continue;
      if (!seen.has(v)) seen.set(v, { slug, kind: 'events' });
    }
  }
  return seen;
}

function buildCombinedIndex() {
  const combined = new Map();
  // people first, events second (people は短いことが多いが、ここでは長さ順 sort するので順序は問題ない)
  for (const [k, v] of buildPeopleIndex()) combined.set(k, v);
  for (const [k, v] of buildEventsIndex()) {
    if (!combined.has(k)) combined.set(k, v);
  }
  return Array.from(combined.entries())
    .map(([name, entry]) => ({ name, slug: entry.slug, kind: entry.kind }))
    .sort((a, b) => b.name.length - a.name.length);
}

const INDEX = buildCombinedIndex();

const KANJI_RE = /[一-鿿㐀-䶿豈-﫿]/;

function findMatches(text, currentKind, currentSlug) {
  const taken = [];
  for (const entry of INDEX) {
    if (entry.kind === currentKind && entry.slug === currentSlug) continue;
    const { name, slug, kind } = entry;
    let pos = 0;
    while (pos < text.length) {
      const found = text.indexOf(name, pos);
      if (found < 0) break;
      const end = found + name.length;
      // 後続文字が CJK 統合漢字なら、より長い候補の途中の可能性が高いので skip
      // (人名: 「税所篤」が「税所篤之」「税所篤胤」の前半にマッチするのを防ぐ)
      // (事件名: 「桜田門外の変」が「桜田門外の変子」のような偽続にマッチするのを防ぐ)
      const after = text.charAt(end);
      if (after && KANJI_RE.test(after)) {
        pos = end;
        continue;
      }
      const overlaps = taken.some((t) => !(end <= t.start || found >= t.end));
      if (!overlaps) taken.push({ start: found, end, name, slug, kind });
      pos = end;
    }
  }
  return taken.sort((a, b) => a.start - b.start);
}

function linkify(text, currentKind, currentSlug) {
  const matches = findMatches(text, currentKind, currentSlug);
  if (matches.length === 0) return null;
  const nodes = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start > cursor) {
      nodes.push({ type: 'text', value: text.slice(cursor, m.start) });
    }
    nodes.push({
      type: 'link',
      url: `/${m.kind}/${m.slug}/`,
      title: null,
      children: [{ type: 'text', value: m.name }],
    });
    cursor = m.end;
  }
  if (cursor < text.length) {
    nodes.push({ type: 'text', value: text.slice(cursor) });
  }
  return nodes;
}

function getCurrentInfo(file) {
  const path = file?.path ?? file?.history?.[0] ?? '';
  const peopleMatch = path.match(/content\/people\/([^/]+)\.md$/);
  if (peopleMatch) return { kind: 'people', slug: peopleMatch[1] };
  const routesMatch = path.match(/content\/routes\/([^/]+)\.md$/);
  if (routesMatch) return { kind: 'routes', slug: routesMatch[1] };
  const eventsMatch = path.match(/content\/events\/([^/]+)\.md$/);
  if (eventsMatch) return { kind: 'events', slug: eventsMatch[1] };
  const worksMatch = path.match(/content\/works\//);
  if (worksMatch) return { kind: 'works', slug: null };
  return { kind: 'other', slug: null };
}

export default function remarkLinkPeople() {
  return (tree, file) => {
    const { kind, slug: currentSlug } = getCurrentInfo(file);
    // people / routes / events の各 markdown 本文に対して people 名・event 名を auto-link
    if (kind !== 'people' && kind !== 'routes' && kind !== 'events') return;

    visit(tree, 'text', (node, index, parent) => {
      if (!parent || index == null) return;
      if (parent.type === 'link') return;
      if (parent.type === 'heading') return;
      const replacement = linkify(node.value, kind, currentSlug);
      if (!replacement) return;
      parent.children.splice(index, 1, ...replacement);
      return [SKIP, index + replacement.length];
    });
  };
}
