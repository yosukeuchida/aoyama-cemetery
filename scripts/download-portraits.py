#!/usr/bin/env python3
"""
Wikimedia Commons から偉人の肖像画像を一括ダウンロード。

Special:FilePath はレート制限が厳しいので、
MediaWiki API 経由でサムネイル URL を取得し、CDN (upload.wikimedia.org) から取得する。

保存先: src/assets/portraits/<slug>.jpg
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAIRS = [
    ("akiyama-yoshifuru", "Akiyama_Yoshifuru.jpg"),
    ("goto-shinpei", "Shimpei_Gotō.jpg"),
    ("hamaguchi-osachi", "HAMAGUCHI_Osachi.jpg"),
    ("hirose-takeo", "Hirose_Takeo.jpg"),
    ("inoue-junnosuke", "Junnosuke_Inoue.jpg"),
    ("inukai-tsuyoshi", "Inukai_Tsuyoshi.jpg"),
    ("kato-takaaki", "Takaaki_Kato_suit.jpg"),
    ("kato-tomosaburo", "Admiral_Kato_Tomosaburo.jpg"),
    ("kitasato-shibasaburo", "Shibasaburō_Kitasato_1910.jpg"),
    ("komura-jutaro", "Portrait_of_Komura_Jutaro.jpg"),
    ("kunikida-doppo", "Doppo_Kunikida.jpg"),
    ("kuroda-kiyotaka", "Kiyotaka_Kuroda_formal.jpg"),
    ("makino-nobuaki", "Nobuaki_Makino_in_later_years.jpg"),
    ("matsukata-masayoshi", "4_MatsukataM.jpg"),
    ("matsuoka-yosuke", "Yohsuke_matsuoka1932.jpg"),
    ("mikimoto-kokichi", "MIKIMOTO_Kokichi.jpg"),
    ("mori-arinori", "Arinori_Mori_2.jpg"),
    ("nakae-chomin", "Nakae_Chomin_2.JPG"),
    ("nishi-amane", "Nishi_Amane,_supervisor_of_the_Tokyo_Normal_School.jpg"),
    ("nogi-maresuke", "Maresuke_Nogi,_近世名士写真_其1_-_Photo_only.jpg"),
    ("otori-keisuke", "Otori_Keisuke.jpg"),
    ("ozaki-koyo", "Koyo_Ozaki.jpg"),
    ("saito-mokichi", "Mokichi_Saito.1892.jpg"),
    ("sano-tsunetami", "Sano_Tsunetami.jpg"),
    ("shiga-naoya", "Shiga_Naoya_1938.jpg"),
    ("tanaka-hisashige", "TanakaHisashige.jpg"),
    ("ueki-emori", "Emori_Ueki.JPG"),
    ("yamamoto-gonbee", "Gonbee_Yamamoto.jpg"),
    # 2026-05-22 追加分(public domain 確認済)
    ("goto-shojiro", "Goto_Shojiro.jpg"),
    ("soejima-taneomi", "Taneomi_Soejima.jpg"),
    ("morinaga-taichiro", "Taichiro_Morinaga.png"),
    ("sato-giryo", "Yoshisuke_Sato.jpg"),
    ("kawaji-toshiyoshi", "Kawaji_Toshiyoshi.jpg"),
    ("nishi-takeichi", "Nishi_Takeichi.jpg"),
    ("nagayo-sensai", "Nagayo_Sensai.jpg"),
    ("joseph-heco", "Joseph_Heco.JPG"),
    # 2026-05-22 追加分その2(public domain 確認済)
    ("koiso-kuniaki", "Kuniaki_Koiso.jpg"),
    ("ooki-takato", "Takato_Oki.jpg"),
    ("nozu-michitsura", "Nozu_Michitsura.jpg"),
    ("uehara-yusaku", "Uehara_Yusaku.jpg"),
    ("togo-shigenori", "Shigenori_Togo.jpg"),
    ("hayashi-tadasu", "Tadasu_Hayashi.jpg"),
    ("toyama-mitsuru", "Toyama_Mitsuru.jpg"),
    ("saigo-itoko", "Saigō_Itoko.jpg"),
    ("nakamura-kichiemon-i", "Kichiemon_Nakamura_I_1951.jpg"),
    # katsu-kokichi: Wikipedia に肖像なし(没後 70 年経過済だが画像未収録)
    # 2026-05-22 追加分その3
    ("yoshihara-shigetoshi", "Yoshihara_Shigetoshi.jpg"),
    ("matsudaira-tsuneo", "Tsuneo_Matsudaira.jpg"),
    ("verbeck", "Guido_Herman_Fridolin_Verbeck.jpg"),
    ("chiossone", "Edoardo_Chiossone.jpg"),
    ("kim-okgyun", "KimOkkyun.jpg"),
    ("mishima-michitsune", "Mishima_Michitsune.jpg"),
    ("ijichi-masaharu", "Masaharu_Ijichi.jpg"),
    ("ogata-taketora", "Taketora_Ogata.jpg"),
    # sugita-gentan: Wikipedia に肖像なし
    # watanabe-noboru: Wikipedia 単独記事なし(同名人物多数の曖昧さ回避ページのみ)
    # 2026-05-22 追加分その4
    ("ichikawa-danjuro-ix", "Ichikawa_Danjuro_IX.jpg"),
    ("kimura-yoshitake", "Kaisyu_Kimura_1865.jpg"),
    ("yoshii-tomozane", "Yoshii_Tomozane.jpg"),
    ("kawakami-soroku", "Kawakami_Soroku.jpg"),
    ("kaieda-nobuyoshi", "Kaieda_Nobuyoshi.jpg"),
    ("ga-noriyuki", "Noriyuki_ga.jpg"),
    ("shinohara-tainoshin", "Shinohara_Tainoshin.jpg"),
    ("saisho-atsushi", "Saisho_Atsushi.jpg"),
    # sagara-sozo: Wikipedia には墓所写真のみ、本人肖像なし
    # inumaru-tetsuzo: 1981 没で PD 未経過(2052 年に PD)
    # 2026-05-22 追加分その5(12名追加バッチ、PD 確認済)
    ("kagawa-keizo", "Keizo_Kagawa_01.jpg"),
    ("wagener", "ワグネル氏肖像.png"),
    ("tatsumi-naofumi", "Tatsumi_Naofumi.jpg"),
    ("sawa-tarozaemon", "Sawa_Tarōzaemonn.jpg"),
    ("ueno-eizaburo", "Hidesaburō_Ueno.jpg"),
    ("yamaguchi-tamon", "TamonYamaguchi.jpg"),
    ("du-bousquet", "Members_of_French_Military_Mission_to_Japan_in_1867.png"),
    # ikeda-hayato: 1965 没で PD 未経過(2036 年)
    # miyazawa-kiichi: 2007 没で PD 未経過(2078 年)
    # miyawaki-shunzo: 2003 没で PD 未経過(2074 年)
    # nagayo-shuntatsu: 1854 没、Wikipedia に肖像なし
    # arimura-jizaemon: 1860 没・22 歳没、Wikipedia に肖像なし
    # 2026-05-25 追加
    ("saisho-atsuko", "Saisho_Atsuko.jpg"),
    # 2026-05-22 追加分その6(9名追加バッチ、PD 確認済)
    ("mori-kaku", "Tsutomu_mori.jpg"),
    ("odachi-shigeo", "ODACHI_Shigeo.jpg"),
    ("kimura-heitaro", "Kimura_Heitaro.jpg"),
    ("takaki-kanehiro", "Kanehiro_Takaki.JPG"),
    ("miura-goro", "Miura_Goro.jpg"),
    ("takashima-tomonosuke", "Takashima_Tomonosuke.jpg"),
    ("eastlake", "William_Clark_Eastlake_and_his_son_Frederic.jpg"),
    # shiramine-shunme: 海援隊集合写真のみ、単独肖像なし
    # hirai-kao: Wikipedia に肖像なし
    # 2026-05-24 追加分(18名バッチ、PD 確認済 / PD 未経過は除外)
    ("oku-yasukata", "Oku_Yasukata.jpg"),
    ("nagata-tetsuzan", "Tessan_Nagata_2.jpg"),
    ("shirakawa-yoshinori", "Yoshinori_Shirakawa_Color.jpg"),
    ("ijuin-goro", "Ijuin_Goro.jpg"),
    ("shimamura-hayao", "Shimamura_Hayao.jpg"),
    ("arima-ryokitsu", "Arima_Ryokitsu.jpg"),
    ("takarabe-takeshi", "Takeshi_takarabe.jpg"),
    # yamanashi-katsunoshin: 1967 没で PD 未経過(2038 年に PD)
    ("yamakawa-kenjiro", "Kenjiro_Yamakawa_2.jpg"),
    ("nagaoka-hantaro", "Hantaro_Nagaoka.jpg"),
    ("tsuda-sen", "Tsuda_Sen.jpg"),
    ("oki-kibataro", "Oki_Kibataro.png"),
    ("ikegai-shotaro", "Ikegai_Shôtarô.jpg"),
    ("yanase-chotaro", "Yanase_Chōtarō.jpg"),
    ("okamoto-kido", "Kido_okamoto.jpg"),
    ("brinkley", "Captain_Francis_Brinkley.jpg"),
    # nagayo-yoshiro: 1961 没で PD 未経過(2032 年に PD)
    # eto-jun: 1999 没で PD 未経過(2070 年に PD)
    # 2026-05-25 追加分(3名、PD 確認済)
    ("ushijima-mitsuru", "Mitsuru_Ushijima.jpg"),
    ("soeda-juichi", "Juichi_Soyeda.jpg"),
    ("yamashita-gentaro", "Yamashita_Gentaro.jpg"),
]

OUT_DIR = "src/assets/portraits"
API = "https://commons.wikimedia.org/w/api.php"
THUMB_WIDTH = 600  # 表示は max 280px、retina 用に 600px 取得
UA = "aoyama-cemetery-portrait-fetcher/1.1 (https://github.com/yosukeuchida/aoyama-cemetery; educational use)"

os.makedirs(OUT_DIR, exist_ok=True)


def http_get(url: str, retries: int = 5) -> bytes:
    delay = 4
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"  429, retry in {delay}s...", file=sys.stderr)
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise
    raise RuntimeError("retries exhausted")


def get_thumb_url(fname: str) -> str:
    params = {
        "action": "query",
        "titles": f"File:{fname}",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": str(THUMB_WIDTH),
        "format": "json",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    data = json.loads(http_get(url).decode("utf-8"))
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    if "imageinfo" not in page:
        raise RuntimeError(f"no imageinfo for {fname}")
    info = page["imageinfo"][0]
    return info.get("thumburl") or info["url"]


errors = []
for slug, fname in PAIRS:
    ext = os.path.splitext(fname)[1].lower()
    if ext == ".jpeg":
        ext = ".jpg"
    out_path = os.path.join(OUT_DIR, f"{slug}{ext}")
    if os.path.exists(out_path):
        print(f"skip (exists): {out_path}")
        continue
    try:
        thumb_url = get_thumb_url(fname)
        time.sleep(0.8)
        data = http_get(thumb_url)
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"ok: {out_path} ({len(data)} bytes)")
        time.sleep(0.8)
    except Exception as e:
        errors.append((slug, fname, str(e)))
        print(f"ERROR {slug}: {e}", file=sys.stderr)
        time.sleep(2)

if errors:
    print(f"\n{len(errors)} errors occurred.", file=sys.stderr)
    for slug, fname, msg in errors:
        print(f"  - {slug} ({fname}): {msg}", file=sys.stderr)
    sys.exit(1)
print(f"\ndone: portraits in {OUT_DIR}/")
