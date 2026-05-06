import json
import time
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

def fetch_coordinates():
    data_path = 'weather-dashboard/src/assets/dashboard_data.json'
    output_path = 'weather-dashboard/src/assets/region_coords.json'
    
    if not os.path.exists(data_path):
        print(f"❌ {data_path} が見つかりません。")
        return

    print("⏳ データを読み込んでいます...")
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 重複を排除して地域名のリストを作成
    regions = sorted(list(set([d['地方'] for d in data])))
    print(f"📍 全 {len(regions)} か所の地域を検出しました。座標を取得します...")

    # OpenStreetMapのAPIを使用（無料）
    geolocator = Nominatim(user_agent="weather_accuracy_dashboard")
    coords_dict = {}

    for i, region in enumerate(regions):
        # 検索精度を上げるために「日本」と「気象台」などのコンテキストを付与
        search_query = f"日本, {region}"
        
        try:
            # APIの負荷制限（マナー）のため1秒待機
            time.sleep(1)
            location = geolocator.geocode(search_query, timeout=10)
            
            if location:
                # [経度(Longitude), 緯度(Latitude)] の順で保存 (多くの地図ライブラリの標準仕様)
                coords_dict[region] = [location.longitude, location.latitude]
                print(f"[{i+1}/{len(regions)}] ✅ {region}: {location.longitude}, {location.latitude}")
            else:
                print(f"[{i+1}/{len(regions)}] ⚠️ {region}: 見つかりませんでした")
                coords_dict[region] = None # 後で手動で埋められるようにNoneにしておく

        except GeocoderTimedOut:
            print(f"[{i+1}/{len(regions)}] ❌ {region}: タイムアウトしました")
            coords_dict[region] = None

    # 結果をJSONとして保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(coords_dict, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 完了！ '{output_path}' に座標データを保存しました。")
    print("※ ⚠️ や ❌ が出た地域は、出力されたJSONを直接開いて、手動でGoogleマップ等から数値を入力してください。")

if __name__ == "__main__":
    fetch_coordinates()