// 出身地文字列を「旧国/藩(または地域)」レベルに正規化する。
// 同郷エッジを引くための統一キー。文字列マッチで失敗したら "その他" を返す。

export type Region =
  | '薩摩' | '長州' | '土佐' | '肥前' | '会津' | '越後' | '加賀'
  | '尾張' | '紀州' | '水戸' | '筑前' | '伊予' | '桑名' | '津和野'
  | '伊勢' | '佐倉' | '広島' | '備前' | '備中' | '備後' | '備前美作'
  | '阿波' | '讃岐' | '日向' | '播磨' | '長崎' | '大村'
  | '江戸' | '東北' | '東日本' | '海外' | 'その他';

interface Rule {
  region: Region;
  keywords: string[];
}

// 旧国/藩名を最優先、次に現代県名で判定
const RULES: Rule[] = [
  { region: '薩摩', keywords: ['薩摩', '鹿児島'] },
  { region: '長州', keywords: ['長州', '長門', '周防', '山口県', '萩'] },
  { region: '土佐', keywords: ['土佐', '高知'] },
  { region: '肥前', keywords: ['佐賀', '肥前', '伊万里'] },
  { region: '大村', keywords: ['大村'] },
  { region: '会津', keywords: ['会津'] },
  { region: '越後', keywords: ['越後', '新潟', '長岡'] },
  { region: '水戸', keywords: ['水戸', '常陸', '茨城'] },
  { region: '筑前', keywords: ['筑前', '福岡'] },
  { region: '伊予', keywords: ['伊予', '愛媛', '松山'] },
  { region: '桑名', keywords: ['桑名'] },
  { region: '津和野', keywords: ['津和野', '石見'] },
  { region: '伊勢', keywords: ['伊勢', '三重', '津市'] },
  { region: '佐倉', keywords: ['佐倉'] },
  { region: '広島', keywords: ['広島', '安芸', '備後'] },
  { region: '日向', keywords: ['日向', '宮崎', '都城', '飫肥'] },
  { region: '長崎', keywords: ['長崎'] },
  { region: '紀州', keywords: ['紀州', '紀伊', '和歌山'] },
  { region: '尾張', keywords: ['尾張', '愛知', '名古屋'] },
  { region: '加賀', keywords: ['加賀', '石川県', '金沢'] },
  { region: '播磨', keywords: ['播磨', '兵庫'] },
  { region: '阿波', keywords: ['阿波', '徳島'] },
  { region: '東北', keywords: ['岩手', '宮城', '秋田', '山形', '青森', '福島'] },
  { region: '江戸', keywords: ['江戸', '東京'] },
  { region: '海外', keywords: ['アメリカ', 'オランダ', 'ドイツ', 'イタリア', 'フランス', 'ベルギー', 'サルデーニャ', '朝鮮', '韓国', '英国', 'イギリス'] },
];

export function normalizeRegion(birthPlace: string | undefined): Region {
  if (!birthPlace) return 'その他';
  for (const rule of RULES) {
    if (rule.keywords.some((kw) => birthPlace.includes(kw))) {
      return rule.region;
    }
  }
  return 'その他';
}
