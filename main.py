import pandas as pd
import os
import json

# これまでに作った関数をインポートする想定
from script.access_request_url_forecast import scrape_forecast_api
from script.scrape_weather import scrape_jma_actual_data_clean
from visuallize.tools_preprocess_plot import simplify_weather, plot_weather_heatmap

# 保存先のファイル名定義
FORECAST_CSV = 'data/forecast_history.csv'
ACTUAL_CSV = 'data/actual_history.csv'
MAPPING_JSON = 'data/jma_mapping.json'

def load_or_create_csv(filepath):
    """ローカルのCSVを読み込む。存在しない場合は空のデータフレームを返す"""
    if os.path.exists(filepath):
        print(f"📁 {filepath} を読み込みました。")
        # 日付列を文字列ではなくdatetime型として読み込むための処理
        df = pd.read_csv(filepath, parse_dates=['日付'])
        return df
    else:
        print(f"🆕 {filepath} が見つかりません。新規作成します。")
        return pd.DataFrame()

def save_data_with_deduplication(new_df, filepath, subset_cols):
    """既存データと新規データを結合し、重複を排除して保存する"""
    if new_df.empty:
        print("追加する新規データがありません。")
        return load_or_create_csv(filepath)

    # 1. 既存データを読み込む
    existing_df = load_or_create_csv(filepath)
    
    # 2. データを縦に結合 (Concat)
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    
    # 3. 重複を排除 (例: '日付'と'地方'が全く同じ行があれば、最新のもの(last)を残す)
    combined_df = combined_df.drop_duplicates(subset=subset_cols, keep='last')
    
    # 4. CSVとして保存 (BOM付きUTF-8で保存するとExcelで文字化けしません)
    combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"💾 データを {filepath} に保存しました。(総データ数: {len(combined_df)}件)")
    
    return combined_df

# ==========================================
# メインパイプライン処理
# ==========================================
def run_pipeline(target_date_str, target_time_str, target_year, target_month):
    print("=== 🚀 天気予報データパイプラインを開始します ===")
    
    # ------------------------------------------------
    # 1. マスターデータの読み込み
    # ------------------------------------------------
    if not os.path.exists(MAPPING_JSON):
        print("エラー: jma_mapping.json がありません。先にマッピング生成スクリプトを実行してください。")
        return
        
    with open(MAPPING_JSON, 'r', encoding='utf-8') as f:
        region_mapping = json.load(f)

    # ------------------------------------------------
    # 2. 予報データの取得と保存
    # ------------------------------------------------
    print("\n--- [Step 1] 予報データの処理 ---")
    # 例: "2026/03/04", "11"
    new_forecast_df = scrape_forecast_api(target_date_str, target_time_str) 
    
    # 取得したデータを保存（日付と地方がカブっていたら上書き）
    df_forecast_all = save_data_with_deduplication(
        new_forecast_df, 
        FORECAST_CSV, 
        subset_cols=['日付', '地方']
    )

    # ------------------------------------------------
    # 3. 気象庁データ（実測）の取得と保存
    # ------------------------------------------------
    print("\n--- [Step 2] 気象庁(実測)データの処理 ---")
    # 今回取得した予報データに含まれる地域だけをループ処理
    unique_regions = new_forecast_df['地方'].unique() if not new_forecast_df.empty else df_forecast_all['地方'].unique()
    
    new_actual_data_list = []
    
    for region in unique_regions:
        if region in region_mapping:
            params = region_mapping[region]
            print(f"[{region}] の実測データを取得中...")
            
            # APIや気象庁のページからデータをスクレイピング
            df_actual_part = scrape_jma_actual_data_clean(
                target_year, 
                target_month, 
                region_name=region, 
                prec_no=params['prec_no'], 
                block_no=params['block_no']
            )
            if not df_actual_part.empty:
                new_actual_data_list.append(df_actual_part)
                
    if new_actual_data_list:
        new_actual_df = pd.concat(new_actual_data_list, ignore_index=True)
    else:
        new_actual_df = pd.DataFrame()
        
    # 取得した実測データを保存
    df_actual_all = save_data_with_deduplication(
        new_actual_df, 
        ACTUAL_CSV, 
        subset_cols=['日付', '地方']
    )

    # ------------------------------------------------
    # 4. データの結合と丸め込み（分析フェーズ）
    # ------------------------------------------------
    print("\n--- [Step 3] データの結合と可視化 ---")
    # すべての蓄積データを使って結合
    df_actual_all['実際_天気_シンプル'] = df_actual_all['実際_天気'].apply(simplify_weather)
    
    merged_df = pd.merge(
        df_forecast_all, 
        df_actual_all, 
        on=['日付', '地方'], 
        how='inner'
    )
    
    print(f"✨ 比較可能なデータが {len(merged_df)} 件揃いました！")
    
    # ヒートマップの出力
    plot_weather_heatmap(merged_df)
    
    print("=== 🎉 パイプライン処理が完了しました ===")

# 実行エントリーポイント
if __name__ == "__main__":
    # 例：システムを起動して、特定の日付のデータを処理する
    run_pipeline(
        target_date_str="2026/03/04", 
        target_time_str="11",
        target_year=2026,
        target_month=3
    )