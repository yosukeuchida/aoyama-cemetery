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

// 事件タイトル末尾の動詞・名詞をストリップして本体名を抽出するパターン
// (例: 「廃藩置県」「王政復古の大号令」→「王政復古」)
const EVENT_SUFFIX_PATTERNS = [
  /^(.+?)の大号令$/,
  /^(.+?)条例公布$/,
  /^(.+?)条約調印$/,
  /^(.+?)閣議決定$/,
  /^(.+?)の戦い$/,
  /^(.+?)の変$/,
  /^(.+?)発布$/,
  /^(.+?)公布$/,
  /^(.+?)発足$/,
  /^(.+?)発効$/,
  /^(.+?)開戦$/,
  /^(.+?)終結$/,
  /^(.+?)勃発$/,
  /^(.+?)締結$/,
  /^(.+?)調印$/,
  /^(.+?)通告$/,
  /^(.+?)回復$/,
  /^(.+?)崩御$/,
  /^(.+?)殉死$/,
  /^(.+?)開幕$/,
  /^(.+?)開園$/,
  /^(.+?)開会$/,
  /^(.+?)成立$/,
  /^(.+?)陥落$/,
  /^(.+?)完了$/,
  /^(.+?)刊行$/,
  /^(.+?)執行$/,
  /^(.+?)会戦$/,
];

function addStrippedVariants(variants, raw) {
  if (!raw) return;
  for (const pattern of EVENT_SUFFIX_PATTERNS) {
    const m = raw.match(pattern);
    if (m && m[1] && m[1].length >= 3) {
      variants.add(m[1]);
    }
  }
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
    let prefix = null;
    let inside = null;
    if (parenMatch) {
      prefix = parenMatch[1].trim();
      inside = parenMatch[2].trim();
      if (prefix.length >= 3) variants.add(prefix);
      if (inside.length >= 3) variants.add(inside);
    }
    // 「○○○・△△△」型: 中点分割した各パートも別名としてリンク可能に
    const nakatenParts = [];
    if (title.includes('・')) {
      for (const part of title.split('・')) {
        const trimmed = part.replace(/[((].*?[))]/g, '').trim();
        if (trimmed.length >= 3) {
          variants.add(trimmed);
          nakatenParts.push(trimmed);
        }
      }
    }
    // 末尾の動詞・名詞をストリップして本体名も別名として登録
    // (例: 「廃藩置県」exact / 「地租改正条例公布」→「地租改正」 / 「奉天会戦終結」→「奉天会戦」→「奉天」)
    addStrippedVariants(variants, title);
    if (prefix) addStrippedVariants(variants, prefix);
    if (inside) addStrippedVariants(variants, inside);
    for (const part of nakatenParts) addStrippedVariants(variants, part);
    // 二段階ストリップ(例: 「奉天会戦終結」→「奉天会戦」→ さらに → 「奉天」)
    const passOne = new Set(variants);
    for (const v of passOne) addStrippedVariants(variants, v);
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
      const after = text.charAt(end);
      if (after && KANJI_RE.test(after)) {
        // 後続が漢字の場合、(name + 後続漢字) で始まる長い候補がインデックスにあるなら
        // その長い候補にマッチさせるべきなので skip
        const extended = name + after;
        let hasLonger = false;
        for (const e of INDEX) {
          if (e.name.length > name.length && e.name.startsWith(extended)) {
            hasLonger = true;
            break;
          }
        }
        if (hasLonger) {
          pos = end;
          continue;
        }
        // people の場合は保守的: 後続漢字がインデックス未収録の長い人名の可能性があるので skip
        // (例: 「税所篤」+「之」で「税所篤之」がインデックスになくても、未登録人物の可能性)
        if (kind === 'people') {
          pos = end;
          continue;
        }
        // events の場合は緩く許可: 後続漢字(例:「廃藩置県」+「後」、「王政復古」+「の」が
        // 偶然 hiragana じゃなく漢字続きでも)安全にリンクしてよい
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
