import requests
import pandas as pd

def scrape_forecast_api(target_date_str, target_time_str):
    """
    APIからJSONを取得し、正しい階層構造に合わせてDataFrameに変換する関数
    """
    dt = pd.to_datetime(target_date_str)
    yyyy_mm = dt.strftime("%Y%m")
    yyyy_mm_dd = dt.strftime("%Y%m%d")
    url = f"https://sdc.weathermap.co.jp/JMApast/JMA_Yohou/{yyyy_mm}/{yyyy_mm_dd}_{target_time_str}.json"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    print(f"予報データ取得中: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        
        forecast_list = []
        
        # 1. JPSA, JPSB などのルートキーをループ
        for root_key, root_data in json_data.items():
            if not isinstance(root_data, dict):
                continue
                
            yohou_data = root_data.get("Yohou", {})
            
            # 2. 地方コード（11000など）の階層をループ
            for y_code, y_info in yohou_data.items():
                if not isinstance(y_info, dict):
                    continue
                
                # --- [広域の地名を取得] ---
                area_name = y_info.get("Name", "")
                
                # --- [詳細な地名を取得] ---
                # TempPart が WeatherPart と同じ階層にあるため y_info から取得
                detailed_name = area_name # 初期値は広域名にしておく
                temp_part = y_info.get("TempPart", {})
                
                # TempPartの1つ下の階層（都市コード: 11016など）をループ
                for t_code, t_info in temp_part.items():
                    # さらにその下（2個下）にある Name 属性を取得
                    if isinstance(t_info, dict) and "Name" in t_info:
                        detailed_name = t_info["Name"]
                        break # 詳細名が1つ見つかればOKとする
                
                # --- [天気の取得] ---
                weather_part = y_info.get("WeatherPart", {})
                
                # 日付ごとに抽出 ("2026-03-04" など)
                for date_str, w_data in weather_part.items():
                    if not isinstance(w_data, dict):
                        continue
                        
                    weather_text = w_data.get("Weather", "")
                    if not weather_text:
                        weather_text = w_data.get("Sentence", "")
                        
                    # リストに格納
                    forecast_list.append({
                        "日付": date_str,
                        "地方": detailed_name,  # "稚内" などの詳細名
                        "広域名": area_name,    # "宗谷地方" などの広域名
                        "予報_天気": weather_text
                    })
                    
        # 3. DataFrameに変換
        df_forecast = pd.DataFrame(forecast_list)
        
        if not df_forecast.empty:
            df_forecast['日付'] = pd.to_datetime(df_forecast['日付'])
            
        return df_forecast

    except Exception as e:
        print(f"❌ 予報データの取得または解析に失敗しました: {e}")
        return pd.DataFrame()

# ==========================================
# テスト実行
# ==========================================
if __name__ == "__main__":
    df_test = scrape_forecast_api("2026/03/04", "11")
    if not df_test.empty:
        print("\n✅ パース成功！取得した予報データ（先頭15件）:")
        # 抽出した列だけを綺麗に表示
        print(df_test[['日付', '広域名', '地方', '予報_天気']].head(15))