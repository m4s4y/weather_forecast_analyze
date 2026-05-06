import pandas as pd
import time
from datetime import datetime

def scrape_jma_actual_data_clean(year, month, region_name="東京", prec_no=44, block_no=47662):
    """
    気象庁の実測データ（日別）を取得・整形する関数。
    ※ 降水量・日照時間の記号(品質フラグ)を除去し、計算可能な数値データにクレンジングします！
    """
    block_no_str = str(block_no)
    
    # URL判定（5桁ならs1、それ以外はa1）
    if len(block_no_str) >= 5:
        url = f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_s1.php?prec_no={prec_no}&block_no={block_no_str}&year={year}&month={month}&day=&view="
    else:
        block_no_str = block_no_str.zfill(4)
        url = f"https://www.data.jma.go.jp/obd/stats/etrn/view/daily_a1.php?prec_no={prec_no}&block_no={block_no_str}&year={year}&month={month}&day=&view="
        
    try:
        dfs = pd.read_html(url)
        df_raw = dfs[0]
    except Exception as e:
         print(f"❌ {region_name} のデータ取得失敗: {e}")
         return pd.DataFrame()

    # --- データの整形処理 ---
    try:
        # マルチインデックスの平滑化
        new_columns = []
        for col in df_raw.columns:
            clean_col = "_".join([str(c) for c in col if "Unnamed" not in str(c)])
            new_columns.append(clean_col)
        df_raw.columns = new_columns

        # 1. 「日」列
        day_cols = [c for c in df_raw.columns if '日' in c and '日の出' not in c and '日の入' not in c]
        if not day_cols:
            return pd.DataFrame()
        day_col = day_cols[0]

        # 2. 「天気概況(昼)」列
        weather_cols = [c for c in df_raw.columns if '天気概況' in c and '昼' in c]
        weather_col = weather_cols[0] if weather_cols else None

        # 3. 「降水量」列 (a1には'合計'という文字がないため条件を緩和)
        precip_cols = [c for c in df_raw.columns if '降水' in c]
        precip_col = None
        for c in precip_cols:
            if '合計' in c:  # s1の場合は複数あるので「合計」を優先
                precip_col = c
                break
        if not precip_col and precip_cols:
            precip_col = precip_cols[0] # a1の場合は最初のものを採用

        # 4. 「日照時間」列 (マルチインデックス結合時にアンダーバーが入る対策)
        sunshine_cols = [c for c in df_raw.columns if '日照' in c]
        sunshine_col = sunshine_cols[0] if sunshine_cols else None

        # --- 列の抽出とリネーム ---
        extract_cols = [day_col]
        rename_dict = {day_col: '日'}
        
        if weather_col:
            extract_cols.append(weather_col)
            rename_dict[weather_col] = '実際_天気'
        if precip_col:
            extract_cols.append(precip_col)
            rename_dict[precip_col] = '降水量'
        if sunshine_col:
            extract_cols.append(sunshine_col)
            rename_dict[sunshine_col] = '日照時間'

        df_clean = df_raw[extract_cols].copy()
        df_clean.rename(columns=rename_dict, inplace=True)
        
        # 存在しない列は NaN で埋める
        for col in ['実際_天気', '降水量', '日照時間']:
            if col not in df_clean.columns:
                df_clean[col] = pd.NA
        
        # 🌟【重要】データのクレンジング（記号の除去と数値化）🌟
        for col in ['降水量', '日照時間']:
            # 気象庁特有の記号 ')', ']', '×' などを正規表現で空文字に置換
            df_clean[col] = df_clean[col].astype(str).str.replace(r'[)\]×]', '', regex=True)
            # '--' や空文字を NaN に変換し、データを float (小数) 型に変換
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        # --- クリーニング ---
        df_clean = df_clean[pd.to_numeric(df_clean['日'], errors='coerce').notnull()]
        df_clean['日'] = df_clean['日'].astype(int)
        
        df_clean['日付'] = pd.to_datetime(f"{year}-{month:02d}-" + df_clean['日'].astype(str).str.zfill(2))
        df_clean['地方'] = region_name
        
        # 必要な列をすべて返す
        df_final = df_clean[['日付', '地方', '実際_天気', '降水量', '日照時間']].copy()
        
        time.sleep(1) # API負荷軽減
        return df_final

    except Exception as e:
        print(f"❌ {region_name} のデータ整形中にエラーが発生しました: {e}")
        return pd.DataFrame()