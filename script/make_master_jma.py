import requests
from bs4 import BeautifulSoup
import re
import json
import time

def generate_jma_mapping_json():
    """
    気象庁のサイトから全国の観測所名と prec_no, block_no をスクレイピングし、
    JSONファイルとして保存する関数
    """
    base_url = "https://www.data.jma.go.jp/obd/stats/etrn/select/"
    pref_url = base_url + "prefecture00.php"
    
    print("気象庁の都道府県リストを取得中...")
    response = requests.get(pref_url)
    response.encoding = response.apparent_encoding # 文字化け防止
    soup = BeautifulSoup(response.text, 'html.parser')
    
    mapping = {}
    
    # 1. 都道府県のリンク（prec_no）を取得
    # 気象庁のページは <area> タグの href に prec_no が入っています
    areas = soup.find_all('area', href=re.compile(r'prefecture\.php\?prec_no=\d+'))
    
    prefs = []
    for area in areas:
        pref_name = area.get('alt')
        match = re.search(r'prec_no=(\d+)', area.get('href'))
        if match and pref_name:
            prefs.append({'name': pref_name, 'prec_no': match.group(1)})
            
    # 重複を排除
    prefs = [dict(t) for t in {tuple(d.items()) for d in prefs}]
    
    print(f"全国 {len(prefs)} エリアの観測所データを収集します。少々お待ちください...")
    
    # 2. 各都道府県のページにアクセスし、観測所（block_no）を取得
    for i, pref in enumerate(prefs):
        prec_no = pref['prec_no']
        station_url = base_url + f"prefecture.php?prec_no={prec_no}"
        
        try:
            res = requests.get(station_url)
            res.encoding = res.apparent_encoding
            s_soup = BeautifulSoup(res.text, 'html.parser')
            
            # 観測所のリンクを探す（block_no が含まれるもの）
            station_areas = s_soup.find_all('area', href=re.compile(r'block_no=\d+'))
            
            for s_area in station_areas:
                station_name = s_area.get('alt')
                href = s_area.get('href')
                
                if not station_name or not href:
                    continue
                    
                b_match = re.search(r'block_no=(\d+)', href)
                if b_match:
                    block_no = b_match.group(1)
                    # 辞書に追加（キー：観測所名、バリュー：コードの辞書）
                    mapping[station_name] = {
                        "prec_no": int(prec_no),
                        "block_no": int(block_no),
                        "pref_name": pref['name'] # どの都道府県に属しているかも一応保存
                    }
                    
        except Exception as e:
            print(f"⚠ {pref['name']}のデータ取得に失敗しました: {e}")
            
        # サーバー負荷軽減（非常に重要）
        time.sleep(1)
        
        # 進捗表示
        if (i + 1) % 10 == 0:
            print(f"... {i + 1} / {len(prefs)} エリア完了")
            
    # 3. JSONファイルとして保存
    with open('data/jma_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=4)
        
    print(f"完了！合計 {len(mapping)} 件の観測所データを 'data/jma_mapping.json' に保存しました。")
    return mapping

if __name__ == "__main__":
    generate_jma_mapping_json()