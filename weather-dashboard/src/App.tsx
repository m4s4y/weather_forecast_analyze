import React, { useMemo, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import Map from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

import weatherData from './assets/dashboard_data_new.json';
import regionCoordsData from './assets/region_coords.json';

type WeatherRecord = { 日付: string; 地方: string; 予報: string; 実際: string; };
const data = weatherData as WeatherRecord[];
const regionCoords = regionCoordsData as unknown as Record<string, [number, number] | null>;
const WEATHER_TYPES = ['晴れ', '曇り', '雨', '雪', 'その他'];

const INITIAL_VIEW_STATE = { longitude: 137.5, latitude: 38.0, zoom: 4.5, pitch: 30, bearing: 0 };

// 🌟 精度に応じた色を返す関数（和算せず地点ごとに色を決定）
const getAccuracyColor = (accuracy: number): [number, number, number, number] => {
  if (accuracy >= 90) return [51, 154, 240, 220]; // 青 (高精度)
  if (accuracy >= 80) return [169, 227, 75, 220]; // 黄緑
  if (accuracy >= 70) return [252, 196, 25, 220]; // 黄
  if (accuracy >= 60) return [255, 146, 43, 220]; // 橙
  return [250, 82, 82, 220];                      // 赤 (低精度)
};

export default function App() {
  const [activeTab, setActiveTab] = useState<'matrix' | 'map'>('map');
  const [selectedSeason, setSelectedSeason] = useState<string>('通年');
  const [selectedMapForecast, setSelectedMapForecast] = useState<string>('すべて');
  const [targetForecast, setTargetForecast] = useState<string>('晴れ');
  const [hoverInfo, setHoverInfo] = useState<any>(null);

  const filteredData = useMemo(() => {
    return data.filter(d => {
      if (selectedSeason !== '通年') {
        const month = parseInt(d.日付.split('-')[1], 10);
        if (selectedSeason === '春' && !(month >= 3 && month <= 5)) return false;
        if (selectedSeason === '夏' && !(month >= 6 && month <= 8)) return false;
        if (selectedSeason === '秋' && !(month >= 9 && month <= 11)) return false;
        if (selectedSeason === '冬' && !(month === 12 || month === 1 || month === 2)) return false;
      }
      if (activeTab === 'map' && selectedMapForecast !== 'すべて' && d.予報 !== selectedMapForecast) return false;
      return true;
    });
  }, [selectedSeason, selectedMapForecast, activeTab]);

  const regionStats = useMemo(() => {
    const stats: Record<string, { total: number; correct: number; distribution: Record<string, number> }> = {};
    filteredData.forEach(d => {
      if (!stats[d.地方]) {
        stats[d.地方] = { total: 0, correct: 0, distribution: { 晴れ: 0, 曇り: 0, 雨: 0, 雪: 0, その他: 0 } };
      }
      stats[d.地方].total++;
      if (d.予報 === d.実際) stats[d.地方].correct++;
      if (stats[d.地方].distribution[d.実際] !== undefined) stats[d.地方].distribution[d.実際]++;
    });
    return stats;
  }, [filteredData]);

  const mapData = useMemo(() => {
    return Object.entries(regionStats)
      .map(([region, stat]) => {
        const coords = regionCoords[region];
        if (!coords) return null;
        const accuracy = stat.total > 0 ? (stat.correct / stat.total) * 100 : 0;
        return { region, COORDINATES: coords, accuracy, ...stat };
      })
      .filter(d => d !== null);
  }, [regionStats]);

  const layers = [
    // 🌟 HeatmapLayerを廃止し、ScatterplotLayerで点として直接色分けする
    new ScatterplotLayer({
      id: 'accuracy-points',
      data: mapData,
      getPosition: (d: any) => d.COORDINATES,
      getRadius: 15000, // 見やすさのために少し大きく
      getFillColor: (d: any) => getAccuracyColor(d.accuracy),
      getLineColor: [255, 255, 255, 150], // 境界線を見やすく
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
      onHover: (info) => setHoverInfo(info),
      transitions: {
        getFillColor: 500, // フィルタリング時の色の変化を滑らかに
        getRadius: 500
      }
    })
  ];

  // マトリックス用計算
  const matrix = useMemo(() => {
    const counts: Record<string, Record<string, number>> = {};
    WEATHER_TYPES.forEach(f => { counts[f] = {}; WEATHER_TYPES.forEach(a => { counts[f][a] = 0; }); });
    filteredData.forEach(d => { if (counts[d.予報] && counts[d.予報][d.実際] !== undefined) counts[d.予報][d.実際]++; });
    return counts;
  }, [filteredData]);

  // ヒートマップの色の濃さを決めるための最大値計算
  const maxCount = useMemo(() => {
    let max = 0;
    WEATHER_TYPES.forEach(f => WEATHER_TYPES.forEach(a => { if (matrix[f][a] > max) max = matrix[f][a]; }));
    return max || 1;
  }, [matrix]);

  // 棒グラフ用のデータ計算
  const chartData = useMemo(() => {
    const subset = filteredData.filter(d => d.予報 === targetForecast);
    if (subset.length === 0) return [];
    const counts: Record<string, number> = { 晴れ: 0, 曇り: 0, 雨: 0, 雪: 0, その他: 0 };
    subset.forEach(d => { if (counts[d.実際] !== undefined) counts[d.実際]++; });
    return WEATHER_TYPES.map(weather => ({
      name: weather, 日数: counts[weather], 確率: ((counts[weather] / subset.length) * 100).toFixed(1)
    })).filter(item => item.日数 > 0);
  }, [filteredData, targetForecast]);

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>🌦️ 天気予報 精度ダッシュボード</h1>
      
      {/* 画面上部の操作部 */}
      <div style={{ background: '#f8f9fa', padding: '1.2rem', borderRadius: '12px', marginBottom: '2rem', display: 'flex', gap: '2rem', alignItems: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
        <div>
          <label style={{ fontWeight: 'bold' }}>季節: </label>
          <select value={selectedSeason} onChange={(e) => setSelectedSeason(e.target.value)} style={{ padding: '0.4rem' }}>
            {['通年', '春', '夏', '秋', '冬'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        {activeTab === 'map' && (
          <div>
            <label style={{ fontWeight: 'bold' }}>対象の予報: </label>
            <select value={selectedMapForecast} onChange={(e) => setSelectedMapForecast(e.target.value)} style={{ padding: '0.4rem' }}>
              {['すべて', ...WEATHER_TYPES].map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
        )}
        <div style={{ marginLeft: 'auto', fontWeight: 'bold', color: '#495057' }}>
          分析対象: {filteredData.length.toLocaleString()} 件
        </div>
      </div>

      <div style={{ display: 'flex', marginBottom: '1.5rem', borderBottom: '2px solid #dee2e6' }}>
        <button onClick={() => setActiveTab('map')} style={{ padding: '0.8rem 1.5rem', cursor: 'pointer', border: 'none', background: activeTab === 'map' ? '#339af0' : 'transparent', color: activeTab === 'map' ? '#fff' : '#495057', fontWeight: 'bold', borderRadius: '8px 8px 0 0' }}>🗺️ 空間精度マップ</button>
        <button onClick={() => setActiveTab('matrix')} style={{ padding: '0.8rem 1.5rem', cursor: 'pointer', border: 'none', background: activeTab === 'matrix' ? '#339af0' : 'transparent', color: activeTab === 'matrix' ? '#fff' : '#495057', fontWeight: 'bold', borderRadius: '8px 8px 0 0' }}>📊 予報別分布分析</button>
      </div>

      {activeTab === 'map' && (
        <div style={{ position: 'relative', height: '650px', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
          <DeckGL initialViewState={INITIAL_VIEW_STATE} controller={true} layers={layers}>
            <Map mapStyle="https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json" />
          </DeckGL>

          {/* 凡例パネル */}
          <div style={{ position: 'absolute', top: 20, right: 20, background: 'rgba(255,255,255,0.95)', padding: '1.2rem', borderRadius: '10px', zIndex: 10, width: '240px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
            <h4 style={{ margin: '0 0 15px 0', fontSize: '0.95rem' }}>予報正答率の対応</h4>
            
            <div style={{ position: 'relative', height: '40px', marginBottom: '20px' }}>
              <div style={{ 
                height: '12px', borderRadius: '6px', 
                background: 'linear-gradient(90deg, #fa5252 0%, #ff922b 25%, #fcc419 50%, #a9e34b 75%, #339af0 100%)' 
              }}></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.75rem', fontWeight: 'bold', color: '#495057' }}>
                <span>60%以下</span>
                <span>80%</span>
                <span>100%</span>
              </div>
            </div>

            <p style={{ fontSize: '0.8rem', color: '#868e96', lineHeight: '1.4', margin: 0 }}>
              各観測地点ごとの精度を色で表しています。青い円ほど予報が安定しています。
            </p>
          </div>

          {/* ツールチップ */}
          {hoverInfo && hoverInfo.object && (
            <div style={{
              position: 'absolute', zIndex: 1, pointerEvents: 'none',
              left: hoverInfo.x, top: hoverInfo.y, transform: 'translate(-50%, -110%)',
              background: 'rgba(33, 37, 41, 0.95)', color: '#f8f9fa',
              padding: '1rem', borderRadius: '8px', minWidth: '220px'
            }}>
              <h3 style={{ margin: '0 0 5px 0', fontSize: '1.1rem', color: '#339af0' }}>📍 {hoverInfo.object.region}</h3>
              <div style={{ fontSize: '0.85rem' }}>
                <p style={{ margin: '0 0 8px 0', borderBottom: '1px solid #495057' }}>
                  全体正答率: <strong>{hoverInfo.object.accuracy.toFixed(1)}%</strong>
                </p>
                <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>実際の結果分布:</p>
                {Object.entries(hoverInfo.object.distribution)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([weather, count]) => {
                    const cnt = count as number;
                    if (cnt === 0) return null;
                    const pct = ((cnt / hoverInfo.object.total) * 100).toFixed(1);
                    return (
                      <div key={weather} style={{ display: 'flex', alignItems: 'center', marginBottom: '3px' }}>
                        <span style={{ width: '40px' }}>{weather}</span>
                        <div style={{ flex: 1, background: '#495057', height: '6px', borderRadius: '3px', margin: '0 8px' }}>
                          <div style={{ width: `${pct}%`, background: '#ff922b', height: '100%', borderRadius: '3px' }}></div>
                        </div>
                        <span style={{ width: '40px', textAlign: 'right', fontSize: '0.75rem' }}>{pct}%</span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* タブ 2: マトリックス分析 */}
      {activeTab === 'matrix' && (
         <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
         <div style={{ background: '#f8f9fa', padding: '1.5rem', borderRadius: '8px' }}>
           <h2>予報 vs 実際の天気 (ヒートマップ)</h2>
           <div style={{ display: 'grid', gridTemplateColumns: '80px repeat(5, 1fr)', gap: '4px', marginTop: '1rem' }}>
             <div></div>
             {WEATHER_TYPES.map(a => <div key={`h-${a}`} style={{ textAlign: 'center', fontWeight: 'bold' }}>{a}</div>)}
             {WEATHER_TYPES.map(forecast => (
               <React.Fragment key={forecast}>
                 <div style={{ display: 'flex', alignItems: 'center', fontWeight: 'bold' }}>{forecast}</div>
                 {WEATHER_TYPES.map(actual => {
                   const val = matrix[forecast][actual];
                   const intensity = val / maxCount;
                   const bgColor = val > 0 ? `rgba(51, 154, 240, ${0.1 + (intensity * 0.9)})` : '#fff';
                   return (
                     <div key={`${forecast}-${actual}`} onClick={() => setTargetForecast(forecast)}
                       style={{ background: bgColor, color: intensity > 0.6 ? '#fff' : '#333', border: forecast === targetForecast ? '2px solid #ff922b' : '1px solid #ddd', padding: '1rem 0', textAlign: 'center', cursor: 'pointer', borderRadius: '4px' }}
                     >{val}</div>
                   );
                 })}
               </React.Fragment>
             ))}
           </div>
         </div>
         <div style={{ background: '#f8f9fa', padding: '1.5rem', borderRadius: '8px' }}>
           <h2>🎯 「{targetForecast}」と予報された日の結果</h2>
           <div style={{ width: '100%', height: 350, marginTop: '1rem' }}>
             <ResponsiveContainer>
               <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} />
                 <XAxis dataKey="name" />
                 <YAxis />
                 <RechartsTooltip formatter={(value: any, name: any, props: any) => {
                   if (name === '日数') return [`${value}日 (${props.payload.確率}%)`, name];
                   return [value, name];
                 }} />
                 <Legend />
                 <Bar dataKey="日数" name="日数">
                   {chartData.map((entry, index) => (
                     <Cell key={`cell-${index}`} fill={entry.name === targetForecast ? '#4dabf7' : '#ced4da'} />
                   ))}
                 </Bar>
               </BarChart>
             </ResponsiveContainer>
           </div>
         </div>
       </div>
      )}
    </div>
  );
}