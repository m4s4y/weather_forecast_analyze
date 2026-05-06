import React, { useMemo, useState, useEffect } from 'react';
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

const getAccuracyColor = (accuracy: number): [number, number, number, number] => {
  if (accuracy >= 90) return [51, 154, 240, 220]; // 青
  if (accuracy >= 80) return [169, 227, 75, 220]; // 黄緑
  if (accuracy >= 70) return [252, 196, 25, 220]; // 黄
  if (accuracy >= 60) return [255, 146, 43, 220]; // 橙
  return [250, 82, 82, 220];                      // 赤
};

export default function App() {
  const [activeTab, setActiveTab] = useState<'matrix' | 'map'>('map');
  const [selectedSeason, setSelectedSeason] = useState<string>('通年');
  const [selectedMapForecast, setSelectedMapForecast] = useState<string>('すべて');
  const [targetForecast, setTargetForecast] = useState<string>('晴れ');
  const [hoverInfo, setHoverInfo] = useState<any>(null);

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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
    new ScatterplotLayer({
      id: 'accuracy-points',
      data: mapData,
      getPosition: (d: any) => d.COORDINATES,
      getRadius: 15000, 
      getFillColor: (d: any) => getAccuracyColor(d.accuracy),
      getLineColor: [255, 255, 255, 150], 
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
      onHover: (info) => setHoverInfo(info),
      transitions: {
        getFillColor: 500,
        getRadius: 500
      }
    })
  ];

  const matrix = useMemo(() => {
    const counts: Record<string, Record<string, number>> = {};
    WEATHER_TYPES.forEach(f => { counts[f] = {}; WEATHER_TYPES.forEach(a => { counts[f][a] = 0; }); });
    filteredData.forEach(d => { if (counts[d.予報] && counts[d.予報][d.実際] !== undefined) counts[d.予報][d.実際]++; });
    return counts;
  }, [filteredData]);

  const maxCount = useMemo(() => {
    let max = 0;
    WEATHER_TYPES.forEach(f => WEATHER_TYPES.forEach(a => { if (matrix[f][a] > max) max = matrix[f][a]; }));
    return max || 1;
  }, [matrix]);

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
    // 🌟 修正ポイント：maxWidthを1500pxに拡張し、widthを95%に設定して横幅をフル活用
    <div style={{ maxWidth: '1500px', width: '95%', margin: '0 auto', padding: isMobile ? '1rem 0' : '2rem 0', fontFamily: 'sans-serif' }}>
      <h1 style={{ fontSize: isMobile ? '1.5rem' : '2.2rem', borderBottom: '2px solid #eee', paddingBottom: '1rem', color: '#343a40' }}>
        🌦️ 天気予報 精度ダッシュボード
      </h1>
      
      <div style={{ 
        background: '#f8f9fa', padding: '1.5rem', borderRadius: '12px', marginBottom: '1.5rem', 
        display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: isMobile ? '1rem' : '2.5rem', 
        alignItems: isMobile ? 'stretch' : 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' 
      }}>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <label style={{ fontWeight: 'bold', fontSize: '0.95rem', color: '#495057' }}>季節: </label>
          <select value={selectedSeason} onChange={(e) => setSelectedSeason(e.target.value)} style={{ padding: '0.6rem', marginTop: '0.4rem', borderRadius: '6px', border: '1px solid #ced4da', fontSize: '1rem' }}>
            {['通年', '春', '夏', '秋', '冬'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        {activeTab === 'map' && (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <label style={{ fontWeight: 'bold', fontSize: '0.95rem', color: '#495057' }}>対象の予報: </label>
            <select value={selectedMapForecast} onChange={(e) => setSelectedMapForecast(e.target.value)} style={{ padding: '0.6rem', marginTop: '0.4rem', borderRadius: '6px', border: '1px solid #ced4da', fontSize: '1rem' }}>
              {['すべて', ...WEATHER_TYPES].map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
        )}
        <div style={{ marginLeft: isMobile ? '0' : 'auto', fontWeight: 'bold', color: '#495057', textAlign: isMobile ? 'right' : 'left', fontSize: '1.1rem' }}>
          🎯 分析対象: <span style={{ color: '#339af0', fontSize: '1.3rem' }}>{filteredData.length.toLocaleString()}</span> 件
        </div>
      </div>

      <div style={{ display: 'flex', marginBottom: '1.5rem', borderBottom: '2px solid #dee2e6' }}>
        <button onClick={() => setActiveTab('map')} style={{ flex: isMobile ? 1 : 'none', padding: '1rem 2rem', fontSize: '1.1rem', cursor: 'pointer', border: 'none', background: activeTab === 'map' ? '#339af0' : 'transparent', color: activeTab === 'map' ? '#fff' : '#495057', fontWeight: 'bold', borderRadius: '8px 8px 0 0', transition: 'all 0.2s' }}>🗺️ 空間精度マップ</button>
        <button onClick={() => setActiveTab('matrix')} style={{ flex: isMobile ? 1 : 'none', padding: '1rem 2rem', fontSize: '1.1rem', cursor: 'pointer', border: 'none', background: activeTab === 'matrix' ? '#339af0' : 'transparent', color: activeTab === 'matrix' ? '#fff' : '#495057', fontWeight: 'bold', borderRadius: '8px 8px 0 0', transition: 'all 0.2s' }}>📊 予報別分布分析</button>
      </div>

      {activeTab === 'map' && (
        // 🌟 地図の高さもワイド画面に合わせて少しだけ高く設定（650px -> 700px）
        <div style={{ position: 'relative', height: isMobile ? '500px' : '700px', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.15)' }}>
          <DeckGL initialViewState={INITIAL_VIEW_STATE} controller={true} layers={layers}>
            <Map mapStyle="https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json" />
          </DeckGL>

          <div style={{ 
            position: 'absolute', top: 20, right: 20, background: 'rgba(255,255,255,0.95)', 
            padding: isMobile ? '0.8rem' : '1.2rem', borderRadius: '10px', zIndex: 10, 
            width: isMobile ? '160px' : '260px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' 
          }}>
            <h4 style={{ margin: `0 0 ${isMobile ? '8px' : '15px'} 0`, fontSize: isMobile ? '0.8rem' : '1rem' }}>予報正答率</h4>
            <div style={{ position: 'relative', height: '30px', marginBottom: isMobile ? '5px' : '20px' }}>
              <div style={{ height: '10px', borderRadius: '5px', background: 'linear-gradient(90deg, #fa5252 0%, #ff922b 25%, #fcc419 50%, #a9e34b 75%, #339af0 100%)' }}></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.8rem', fontWeight: 'bold', color: '#495057' }}>
                <span>60%</span><span>80%</span><span>100%</span>
              </div>
            </div>
            {!isMobile && (
              <p style={{ fontSize: '0.85rem', color: '#868e96', lineHeight: '1.5', margin: 0 }}>
                各観測地点ごとの精度を色で表しています。青い円ほど予報が安定しています。
              </p>
            )}
          </div>

          {hoverInfo && hoverInfo.object && (
            <div style={{
              position: 'absolute', zIndex: 1, pointerEvents: 'none',
              left: isMobile ? '50%' : hoverInfo.x, 
              top: isMobile ? 'auto' : hoverInfo.y, 
              bottom: isMobile ? '20px' : 'auto',
              transform: isMobile ? 'translateX(-50%)' : 'translate(-50%, -110%)',
              width: isMobile ? '90%' : '240px',
              background: 'rgba(33, 37, 41, 0.95)', color: '#f8f9fa',
              padding: '1.2rem', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
            }}>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '1.2rem', color: '#339af0' }}>📍 {hoverInfo.object.region}</h3>
              <div style={{ fontSize: '0.9rem' }}>
                <p style={{ margin: '0 0 10px 0', borderBottom: '1px solid #495057', paddingBottom: '6px' }}>
                  全体正答率: <strong>{hoverInfo.object.accuracy.toFixed(1)}%</strong>
                </p>
                <p style={{ margin: '0 0 6px 0', fontWeight: 'bold' }}>実際の結果分布:</p>
                {Object.entries(hoverInfo.object.distribution)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([weather, count]) => {
                    const cnt = count as number;
                    if (cnt === 0) return null;
                    const pct = ((cnt / hoverInfo.object.total) * 100).toFixed(1);
                    return (
                      <div key={weather} style={{ display: 'flex', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ width: '45px' }}>{weather}</span>
                        <div style={{ flex: 1, background: '#495057', height: '8px', borderRadius: '4px', margin: '0 10px' }}>
                          <div style={{ width: `${pct}%`, background: '#ff922b', height: '100%', borderRadius: '4px' }}></div>
                        </div>
                        <span style={{ width: '45px', textAlign: 'right', fontSize: '0.8rem' }}>{pct}%</span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'matrix' && (
         <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '2rem' }}>
         <div style={{ background: '#f8f9fa', padding: isMobile ? '1rem' : '2rem', borderRadius: '12px', overflowX: 'auto', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
           <h2 style={{ fontSize: isMobile ? '1.2rem' : '1.6rem', color: '#343a40', marginBottom: '1rem' }}>予報 vs 実際の天気</h2>
           {isMobile && <p style={{ fontSize: '0.8rem', color: '#666', margin: '0 0 10px 0' }}>※表は横にスクロールできます</p>}
           
           <div style={{ minWidth: '450px', display: 'grid', gridTemplateColumns: '80px repeat(5, 1fr)', gap: '6px' }}>
             <div></div>
             {WEATHER_TYPES.map(a => <div key={`h-${a}`} style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '1rem', color: '#495057' }}>{a}</div>)}
             {WEATHER_TYPES.map(forecast => (
               <React.Fragment key={forecast}>
                 <div style={{ display: 'flex', alignItems: 'center', fontWeight: 'bold', fontSize: '1rem', color: '#495057' }}>{forecast}</div>
                 {WEATHER_TYPES.map(actual => {
                   const val = matrix[forecast][actual];
                   const intensity = val / maxCount;
                   const bgColor = val > 0 ? `rgba(51, 154, 240, ${0.1 + (intensity * 0.9)})` : '#fff';
                   return (
                     <div key={`${forecast}-${actual}`} onClick={() => setTargetForecast(forecast)}
                       style={{ 
                         background: bgColor, color: intensity > 0.6 ? '#fff' : '#333', 
                         border: forecast === targetForecast ? '3px solid #ff922b' : '1px solid #dee2e6', 
                         padding: '1.2rem 0', textAlign: 'center', cursor: 'pointer', borderRadius: '6px', 
                         fontSize: '1rem', fontWeight: 'bold', transition: 'all 0.2s'
                       }}
                     >{val}</div>
                   );
                 })}
               </React.Fragment>
             ))}
           </div>
         </div>
         
         <div style={{ background: '#f8f9fa', padding: isMobile ? '1rem' : '2rem', borderRadius: '12px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
           <h2 style={{ fontSize: isMobile ? '1.2rem' : '1.6rem', color: '#343a40', marginBottom: '1rem' }}>🎯 「{targetForecast}」と予報された日の結果</h2>
           <div style={{ width: '100%', height: 400 }}>
             <ResponsiveContainer>
               <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                 <CartesianGrid strokeDasharray="3 3" vertical={false} />
                 <XAxis dataKey="name" fontSize={14} tickMargin={10} />
                 <YAxis fontSize={14} />
                 <RechartsTooltip formatter={(value: any, name: any, props: any) => {
                   if (name === '日数') return [`${value}日 (${props.payload.確率}%)`, name];
                   return [value, name];
                 }} />
                 <Legend wrapperStyle={{ fontSize: '14px', paddingTop: '10px' }} />
                 <Bar dataKey="日数" name="日数" radius={[4, 4, 0, 0]}>
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