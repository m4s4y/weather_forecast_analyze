import pandas as pd
import re
import os

def get_primary_weather(weather_text):
    """
    「のち」「時々」「一時」などで分割し、先頭のメイン天気を取得して分類する共通関数
    """
    if pd.isna(weather_text): return "不明"
    w = str(weather_text)
    
    # 接続詞で分割し、最初の部分（先頭のメイン天気）だけを抽出する
    base_weather = re.split(r'後|時々|一時|伴う|、|か|で', w)[0]
    
    # 抽出した先頭部分から、4つの基本天気に分類
    if any(kw in base_weather for kw in ["雪", "ふぶく", "吹雪", "みぞれ"]): 
        return "雪"
    elif any(kw in base_weather for kw in ["雨", "霧", "雷", "雹", "あられ"]): 
        return "雨"
    elif any(kw in base_weather for kw in ["晴", "快晴"]): 
        return "晴れ"
    elif any(kw in base_weather for kw in ["曇", "くもり", "薄曇"]): 
        return "曇り"
        
    return "その他"

def determine_actual_weather(row):
    """実際の実測データから天気を推測する（先頭マッチング採用版）"""
    
    # ① 気象台のテキスト記録がある場合
    if pd.notna(row['実際_天気']):
        return get_primary_weather(row['実際_天気'])

    # ② アメダスなどでテキストがない場合は数値から判定
    # ※Python側で既に欠損値や記号を0.0にクレンジングしているため、エラーなく安全に比較できます
    precip = row['降水量']
    sunshine = row['日照時間']

    # 降水量があれば「雨」
    if precip > 0.0:
        return "雨"
    
    if sunshine >= 6.0:
        return "晴れ"
    else:
        return "曇り"

def simplify_forecast_weather(weather_text):
    """予報テキストの丸め込み"""
    return get_primary_weather(weather_text)

def export_to_json():
    forecast_path = 'data/forecast_history.csv'
    actual_path = 'data/actual_history.csv'
    output_path = 'data/dashboard_data.json'
    
    if not os.path.exists(forecast_path) or not os.path.exists(actual_path):
        print("❌ CSVファイルが見つかりません。")
        return

    print("⏳ CSVを読み込んでいます...")
    df_forecast = pd.read_csv(forecast_path)
    df_actual = pd.read_csv(actual_path)

    print("🧹 異常値や記号をクレンジングしています...")
    # 🌟【重要】ここで欠損値や「×」「)」などの記号を強制的にNaNにし、0.0で埋める
    if '降水量' in df_actual.columns:
        df_actual['降水量'] = pd.to_numeric(df_actual['降水量'], errors='coerce').fillna(0.0)
    if '日照時間' in df_actual.columns:
        df_actual['日照時間'] = pd.to_numeric(df_actual['日照時間'], errors='coerce').fillna(0.0)

    print("⏳ データを結合・整形しています...")
    merged_df = pd.merge(df_forecast, df_actual, on=['日付', '地方'], how='inner')
    
    merged_df['予報'] = merged_df['予報_天気'].apply(simplify_forecast_weather)
    merged_df['実際'] = merged_df.apply(determine_actual_weather, axis=1)

    # ブラウザが軽く動くように、必要な列だけを抽出！
    export_df = merged_df[['日付', '地方', '予報', '実際']].copy()
    
    # 日付のフォーマットを統一 (YYYY-MM-DD)
    export_df['日付'] = pd.to_datetime(export_df['日付']).dt.strftime('%Y-%m-%d')

    print("⏳ JSONに書き出しています...")
    export_df.to_json(output_path, orient='records', force_ascii=False)
    
    print(f"✅ 完了！ {len(export_df)}件のデータを '{output_path}' として保存しました。")
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"📊 ファイルサイズ: 約 {file_size_mb:.1f} MB")

if __name__ == "__main__":
    export_to_json()