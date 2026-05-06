import pandas as pd
import os
import json
import time
from datetime import datetime, timedelta

from script.access_request_url_forecast import scrape_forecast_api
from script.scrape_weather import scrape_jma_actual_data_clean

FORECAST_CSV = 'data/forecast_history.csv'
ACTUAL_CSV = 'data/actual_history.csv'
MAPPING_JSON = 'data/jma_mapping.json'

def load_or_create_csv(filepath, default_columns):
    """CSVが存在すれば読み込み、なければ指定した列名を持つ空のDataFrameを返す"""
    if os.path.exists(filepath):
        # 既存のCSVを読み込む（日付列は自動でパースさせる）
        return pd.read_csv(filepath, parse_dates=['日付'])
    else:
        # 🌟修正: 空のDataFrameでも列名を定義しておくことでConcat時のエラーを防ぐ
        return pd.DataFrame(columns=default_columns)

def save_to_csv(new_df, filepath, subset_cols):
    """新規データを既存CSVに追記し、重複を排除して保存する"""
    if new_df.empty:
        return
        
    # カラム名が揃っているか確認（念のため）
    for col in subset_cols:
        if col not in new_df.columns:
            print(f"❌ エラー: 新規データに必須列 '{col}' が存在しません。列名: {new_df.columns.tolist()}")
            return

    existing_df = load_or_create_csv(filepath, default_columns=new_df.columns.tolist())
    
    # 結合して重複を削除
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=subset_cols, keep='last')
    
    combined_df.to_csv(filepath, index=False, encoding='utf-8-sig')
    print(f"💾 {filepath} を更新しました。 (総行数: {len(combined_df)})")


def collect_data_for_period(start_date_str, end_date_str, target_time="11"):
    """
    指定した期間の予報データと実測データを一括収集するメイン関数
    """
    start_date = datetime.strptime(start_date_str, "%Y/%m/%d")
    end_date = datetime.strptime(end_date_str, "%Y/%m/%d")
    
    # マッピング辞書の読み込み
    if not os.path.exists(MAPPING_JSON):
        print("❌ jma_mapping.json が見つかりません。")
        return
    with open(MAPPING_JSON, 'r', encoding='utf-8') as f:
        region_mapping = json.load(f)

    # 期間内の日付を1日ずつループ処理
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y/%m/%d")
        year = current_date.year
        month = current_date.month
        
        print(f"\n======================================")
        print(f"📅 取得対象日: {date_str} (予報時間: {target_time}時)")
        print(f"======================================")

        # ------------------------------------------------
        # 1. 予報データの取得と保存
        # ------------------------------------------------
        print("[1/2] 予報データを取得中...")
        df_forecast = scrape_forecast_api(date_str, target_time)
        
        if not df_forecast.empty:
            save_to_csv(df_forecast, FORECAST_CSV, subset_cols=['日付', '地方'])
        else:
            print(f"⚠ {date_str} の予報データが取得できませんでした。")

        # ------------------------------------------------
        # 2. 実測データの取得と保存（その月の分）
        # ------------------------------------------------
        # 気象庁のデータは「1ヶ月分」がまとめて取れるため、
        # 月が変わったタイミング（または初回）のみ取得すればOKという効率化を入れます。
        if current_date == start_date or current_date.day == 1:
            print(f"[2/2] 実測データ（{year}年{month}月分）を一括取得中...")
            
            # 予報データに含まれる地域をベースに実測を取りに行く
            target_regions = df_forecast['地方'].unique() if not df_forecast.empty else list(region_mapping.keys())[:5] # 空なら適当に数件
            
            monthly_actual_list = []
            for region in target_regions:
                if region in region_mapping:
                    params = region_mapping[region]
                    df_actual = scrape_jma_actual_data_clean(
                        year, month, 
                        region_name=region, 
                        prec_no=params['prec_no'], 
                        block_no=params['block_no']
                    )
                    if not df_actual.empty:
                        monthly_actual_list.append(df_actual)
            
            if monthly_actual_list:
                df_actual_monthly = pd.concat(monthly_actual_list, ignore_index=True)
                save_to_csv(df_actual_monthly, ACTUAL_CSV, subset_cols=['日付', '地方'])
        else:
            print("[2/2] この月の実測データは既に取得済みのためスキップします。")

        # 次の日へ
        current_date += timedelta(days=1)
        time.sleep(1) # APIに優しく
        
    print("\n🎉 指定期間のデータ収集がすべて完了しました！")

if __name__ == "__main__":
    # ここで取得したい期間を指定します
    START_DATE = "2025/04/01"
    END_DATE = "2026/03/31"
    
    collect_data_for_period(START_DATE, END_DATE)