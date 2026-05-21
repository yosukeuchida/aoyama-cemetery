import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { visit, SKIP } from 'unist-util-visit';

const PEOPLE_DIR = 'src/content/people';

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
      if (!seen.has(v)) seen.set(v, slug);
    }
  }
  return Array.from(seen.entries())
    .map(([name, slug]) => ({ name, slug }))
    .sort((a, b) => b.name.length - a.name.length);
}

const INDEX = buildPeopleIndex();

function findMatches(text, currentSlug) {
  const taken = [];
  for (const { name, slug } of INDEX) {
    if (slug === currentSlug) continue;
    let pos = 0;
    while (pos < text.length) {
      const found = text.indexOf(name, pos);
      if (found < 0) break;
      const end = found + name.length;
      const overlaps = taken.some((t) => !(end <= t.start || found >= t.end));
      if (!overlaps) taken.push({ start: found, end, name, slug });
      pos = end;
    }
  }
  return taken.sort((a, b) => a.start - b.start);
}

function linkify(text, currentSlug) {
  const matches = findMatches(text, currentSlug);
  if (matches.length === 0) return null;
  const nodes = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start > cursor) {
      nodes.push({ type: 'text', value: text.slice(cursor, m.start) });
    }
    nodes.push({
      type: 'link',
      url: `/people/${m.slug}/`,
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
  const worksMatch = path.match(/content\/works\//);
  if (worksMatch) return { kind: 'works', slug: null };
  return { kind: 'other', slug: null };
}

export default function remarkLinkPeople() {
  return (tree, file) => {
    const { kind, slug: currentSlug } = getCurrentInfo(file);
    if (kind !== 'people') return;

    visit(tree, 'text', (node, index, parent) => {
      if (!parent || index == null) return;
      if (parent.type === 'link') return;
      if (parent.type === 'heading') return;
      const replacement = linkify(node.value, currentSlug);
      if (!replacement) return;
      parent.children.splice(index, 1, ...replacement);
      return [SKIP, index + replacement.length];
    });
  };
}
