import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import japanize_matplotlib
import os

def determine_actual_weather(row):
    """
    1. 気象台の「テキスト記録」があればそれを最優先
    2. なければアメダスの「降水量・日照時間」から客観的に天気を推測する
    """
    # ① テキスト記録がある場合（東京などの気象台）
    if pd.notna(row['実際_天気']):
        w = str(row['実際_天気'])
        if "雪" in w or "吹雪" in w or "ふぶく" in w: return "雪"
        elif "雨" in w or "雷" in w or "雹" in w: return "雨"
        elif "晴" in w: return "晴れ"
        elif "曇" in w or "霧" in w or "くもり" in w: return "曇り"

    # ② テキスト記録がない場合（アメダス）は数値から判定
    precip = row['降水量']
    sunshine = row['日照時間']

    # 降水量が 0.0mm より多い場合は「雨」（※冬は雪の可能性もありますが一旦悪天候として丸めます）
    if pd.notna(precip) and precip > 0.0:
        return "雨"
    
    # 降水がない場合、日照時間で判定（例：1日4時間以上陽が照っていれば「晴れ」とする）
    if pd.notna(sunshine):
        if sunshine >= 4.0:
            return "晴れ"
        else:
            return "曇り"

    return "その他" # データが完全に欠損している場合

def simplify_forecast_weather(weather_text):
    """予報テキスト用（こちらは今まで通りテキスト判定のみ）"""
    if pd.isna(weather_text): return "不明"
    w = str(weather_text)
    if "雪" in w or "ふぶく" in w: return "雪"
    elif "雨" in w or "雷" in w: return "雨"
    elif "晴" in w: return "晴れ"
    elif "曇" in w or "くもり" in w: return "曇り"
    return "その他"

def generate_heatmap():
    forecast_path = 'data/forecast_history.csv'
    actual_path = 'data/actual_history.csv'
    
    if not os.path.exists(forecast_path) or not os.path.exists(actual_path):
        print("❌ CSVファイルが見つかりません。")
        return

    print("データを読み込んでいます...")
    df_forecast = pd.read_csv(forecast_path, parse_dates=['日付'])
    df_actual = pd.read_csv(actual_path, parse_dates=['日付'])

    # 結合
    merged_df = pd.merge(df_forecast, df_actual, on=['日付', '地方'], how='inner')
    
    if merged_df.empty:
        print("❌ 結合できるデータがありませんでした。")
        return

    # ★ ここがアップデートのポイント！行ごとに複数の列を使って判定 ★
    merged_df['予報_比較用'] = merged_df['予報_天気'].apply(simplify_forecast_weather)
    merged_df['実際_比較用'] = merged_df.apply(determine_actual_weather, axis=1)

    print(f"✅ {len(merged_df)} 件の比較データを作成しました！")

    # クロス集計とヒートマップ描画 (前回と同じ)
    cross_tb = pd.crosstab(merged_df['予報_比較用'], merged_df['実際_比較用'])
    weather_order = ['晴れ', '曇り', '雨', '雪', 'その他']
    existing_weathers = list(set(merged_df['予報_比較用']).union(set(merged_df['実際_比較用'])))
    order = [w for w in weather_order if w in existing_weathers]
    cross_tb = cross_tb.reindex(index=order, columns=order, fill_value=0)

    plt.figure(figsize=(10, 8))
    sns.heatmap(cross_tb, annot=True, cmap='Blues', fmt='d', 
                linewidths=.5, cbar_kws={'label': '日数'}, annot_kws={'size': 14})
    
    plt.title('天気予報の精度ヒートマップ (予報 vs 実測)', fontsize=16, pad=20)
    plt.xlabel('実際の天気 (気象庁 / アメダス推測含む)', fontsize=14)
    plt.ylabel('予報された天気', fontsize=14)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig('weather_accuracy_heatmap.png', dpi=300)
    print("📊 'weather_accuracy_heatmap.png' として画像を保存しました！")
    plt.show()

if __name__ == "__main__":
    generate_heatmap()