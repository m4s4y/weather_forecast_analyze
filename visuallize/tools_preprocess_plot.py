import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import japanize_matplotlib  # 日本語フォント用（pip install japanize-matplotlib が必要です）

def simplify_weather(weather_str):
    """
    複雑な天気テキストを基本の4パターンに丸め込む関数
    ※優先順位が重要です（雪＞雨＞晴れ＞曇り など、分析の目的に合わせて調整します）
    """
    if pd.isna(weather_str):
        return "不明"
    
    w = str(weather_str)
    
    # 悪天候を優先して判定するロジック（例：「晴のち雨」は「雨」としてカウントする場合）
    if "雪" in w:
        return "雪"
    elif "雨" in w or "雷" in w or "雹" in w:
        return "雨"
    elif "晴" in w:
        return "晴れ"
    elif "曇" in w or "霧" in w:
        return "曇り"
    else:
        return "その他"

def merge_and_prepare_data(df_forecast, df_actual):
    """
    予報データと実測データを結合し、分析用に整形する関数
    """
    # 1. 予報データの事前準備
    # APIから取得した日付文字列（例:"20260304"または"2026/03/04"）を datetime 型に統一
    df_forecast['日付'] = pd.to_datetime(df_forecast['日付'])
    # 予報テキストの表記ゆれ防止（「晴れ」などから余計な空白を消す）
    df_forecast['予報_天気'] = df_forecast['予報_天気'].str.strip()
    
    # 2. 実測データの事前準備
    # 気象庁の複雑な天気をシンプルに丸め込む
    df_actual['実際_天気_シンプル'] = df_actual['実際_天気'].apply(simplify_weather)
    
    # 3. データの結合 (日付と地方をキーにして横に繋ぐ)
    # ※APIのJSONキー名が '地方' ではなく 'region' 等の場合は、適宜書き換えてください
    merged_df = pd.merge(
        df_forecast, 
        df_actual, 
        on=['日付', '地方'], # この2つの条件が両方一致する行を結合
        how='inner'        # 両方に存在するデータのみ残す
    )
    
    return merged_df

# ----------------------------------------
# Step 4: ヒートマップの描画
# ----------------------------------------
def plot_weather_heatmap(merged_df):
    """
    結合されたデータから精度ヒートマップを出力する関数
    """
    if merged_df.empty:
        print("結合されたデータがありません。")
        return
        
    # クロス集計表の作成（縦軸：予報、横軸：実際の天気）
    cross_tb = pd.crosstab(merged_df['予報_天気'], merged_df['実際_天気_シンプル'])
    
    # 軸の順番を綺麗に揃える（存在する天気のみ）
    weather_order = ['晴れ', '曇り', '雨', '雪', 'その他']
    existing_weathers = list(set(merged_df['予報_天気']).union(set(merged_df['実際_天気_シンプル'])))
    order = [w for w in weather_order if w in existing_weathers]
    
    cross_tb = cross_tb.reindex(index=order, columns=order, fill_value=0)

    # 描画設定
    plt.figure(figsize=(8, 6))
    sns.heatmap(cross_tb, annot=True, cmap='Blues', fmt='d', linewidths=.5,
                cbar_kws={'label': '日数'}, annot_kws={'size': 14})
    
    plt.title('天気予報の精度ヒートマップ (11時発表予報 vs 昼の実測)', fontsize=16, pad=15)
    plt.xlabel('実際の天気 (気象庁)', fontsize=12)
    plt.ylabel('予報された天気', fontsize=12)
    
    # グラフのレイアウト調整と表示
    plt.tight_layout()
    plt.show()

# ==========================================
# 実行イメージ（これまでの関数を繋げる）
# ==========================================
if __name__ == "__main__":
    # ここには前回までに作成した関数から取得したdfが入っている想定です
    # df_forecast = scrape_forecast_api("2023/10/01", "11") 
    # df_actual = scrape_jma_actual_data_clean(2023, 10, "東京")
    
    # --- テスト用のダミーデータで動作確認 ---
    df_f_dummy = pd.DataFrame({
        '日付': ['2023-10-01', '2023-10-02', '2023-10-03', '2023-10-04'],
        '地方': ['東京', '東京', '東京', '東京'],
        '予報_天気': ['晴れ', '曇り', '雨', '晴れ']
    })
    
    df_a_dummy = pd.DataFrame({
        '日付': pd.to_datetime(['2023-10-01', '2023-10-02', '2023-10-03', '2023-10-04']),
        '地方': ['東京', '東京', '東京', '東京'],
        '実際_天気': ['快晴', '晴後薄曇', '大雨', '曇一時雨'] # 気象庁の複雑なデータ
    })
    
    print("データを結合・整形します...")
    merged_df = merge_and_prepare_data(df_f_dummy, df_a_dummy)
    print("\n結合結果プレビュー:\n", merged_df[['日付', '予報_天気', '実際_天気', '実際_天気_シンプル']])
    
    print("\nヒートマップを描画します...")
    plot_weather_heatmap(merged_df)