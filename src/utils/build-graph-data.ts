import { getCollection } from 'astro:content';
import { normalizeRegion, type Region } from './normalize-region';

export type EdgeType = 'family' | 'mentorship' | 'opposition' | 'alliance' | 'same-origin' | 'shared-event';

export interface GraphNode {
  id: string;
  name: string;
  category: string;
  era: string[];
  region: Region;
  jobTitle?: string;
  shortDescription: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  label?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// relatedPeople.relation の自由文を 4 種類のエッジタイプに分類
function classifyRelation(relation: string): EdgeType {
  const family = /父|母|息子|娘|妻|夫|兄|弟|姉|妹|養子|養女|岳父|義父|義母|義兄|義弟|甥|姪|孫|長男|次男|三男|長女|次女|血族|親戚|配偶|嫁|婿|家督|実父|実母/;
  const mentorship = /師事|門下|薫陶|学ぶ|教え|抜擢|推挙|育成|引き上げ|手ほどき|教育を授|門人/;
  const opposition = /対立|政敵|論敵|対峙|反目|敵対|ライバル|刃|刺し|暗殺/;
  if (family.test(relation)) return 'family';
  if (mentorship.test(relation)) return 'mentorship';
  if (opposition.test(relation)) return 'opposition';
  return 'alliance'; // それ以外は 盟友/同志/関連 にまとめる
}

// ユニーク無向エッジのキー(source-target をソートして重複防止)
function undirectedKey(a: string, b: string): string {
  return a < b ? `${a}--${b}` : `${b}--${a}`;
}

export async function buildGraphData(): Promise<GraphData> {
  const people = await getCollection('people');
  const events = await getCollection('events');

  // --- nodes ---
  const nodes: GraphNode[] = people.map((p) => ({
    id: p.id,
    name: p.data.name,
    category: p.data.category,
    era: p.data.era,
    region: normalizeRegion(p.data.birthPlace),
    jobTitle: p.data.jobTitle,
    shortDescription: p.data.shortDescription,
  }));

  const validSlugs = new Set(nodes.map((n) => n.id));

  // --- edges: relatedPeople 由来 ---
  const edgeMap = new Map<string, GraphEdge>(); // key: undirectedKey + ":" + type
  const addEdge = (source: string, target: string, type: EdgeType, label?: string) => {
    if (source === target) return;
    if (!validSlugs.has(source) || !validSlugs.has(target)) return;
    const key = `${undirectedKey(source, target)}:${type}`;
    if (edgeMap.has(key)) {
      // 既存ラベルとの結合(共通事件のみラベル集約、他は最初の relation を残す)
      if (type === 'shared-event' && label) {
        const existing = edgeMap.get(key)!;
        if (existing.label && !existing.label.includes(label)) {
          existing.label = `${existing.label}, ${label}`;
        }
      }
      return;
    }
    edgeMap.set(key, {
      id: key,
      source,
      target,
      type,
      label,
    });
  };

  for (const p of people) {
    const list = p.data.relatedPeople ?? [];
    for (const r of list) {
      const type = classifyRelation(r.relation);
      addEdge(p.id, r.slug, type, r.relation);
    }
  }

  // --- edges: 同郷(同 region でクラスタ内 fully-connect) ---
  const byRegion = new Map<Region, string[]>();
  for (const n of nodes) {
    if (n.region === 'その他') continue; // その他クラスタは引かない(意味薄)
    if (!byRegion.has(n.region)) byRegion.set(n.region, []);
    byRegion.get(n.region)!.push(n.id);
  }
  for (const [region, ids] of byRegion.entries()) {
    if (ids.length < 2) continue;
    // クラスタ内全ペア(N が大きい region でも 海外 6, 薩摩 ~15 程度なので問題なし)
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        addEdge(ids[i], ids[j], 'same-origin', region);
      }
    }
  }

  // --- edges: 共通事件(各 event の personSlugs で全ペア) ---
  for (const ev of events) {
    const slugs = ev.data.personSlugs;
    if (slugs.length < 2) continue;
    for (let i = 0; i < slugs.length; i++) {
      for (let j = i + 1; j < slugs.length; j++) {
        addEdge(slugs[i], slugs[j], 'shared-event', ev.data.title);
      }
    }
  }

  return { nodes, edges: Array.from(edgeMap.values()) };
}
