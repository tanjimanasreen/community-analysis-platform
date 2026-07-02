import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import ForceGraph2D from 'react-force-graph-2d';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import './index.css';

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [dataset, setDataset] = useState('telegram');
  const [datasets, setDatasets] = useState(['telegram', 'twitter']);
  const [month, setMonth] = useState('october');
  const [overview, setOverview] = useState(null);
  const [networkData, setNetworkData] = useState({ nodes: [], links: [] });
  const [dailyStats, setDailyStats] = useState([]);
  const [themes, setThemes] = useState([]);
  const [membershipImages, setMembershipImages] = useState([]);
  const [currentImageIdx, setCurrentImageIdx] = useState(0);
  const [themeSimilarityType, setThemeSimilarityType] = useState('general');
  const [loading, setLoading] = useState(true);
  
  const fgRef = useRef();

  useEffect(() => {
    // Fetch available datasets
    axios.get(`${API_BASE}/datasets`)
      .then(res => {
        if (res.data.datasets.length > 0) {
          setDatasets(res.data.datasets);
          if (!res.data.datasets.includes(dataset)) {
            setDataset(res.data.datasets[0]);
          }
        }
      })
      .catch(err => console.error("Could not fetch datasets", err));
  }, []);

  // Update default month when dataset changes
  useEffect(() => {
    if (dataset === 'twitter' && month === 'october') {
      setMonth('march');
    } else if (dataset === 'telegram' && month !== 'october') {
      setMonth('october');
    }
  }, [dataset]);

  useEffect(() => {
    setLoading(true);
    
    // Fetch all data for selected dataset
    Promise.all([
      axios.get(`${API_BASE}/${dataset}/overview?month=${month}`),
      axios.get(`${API_BASE}/${dataset}/network?month=${month}`),
      axios.get(`${API_BASE}/${dataset}/daily-stats?month=${month}`),
      axios.get(`${API_BASE}/${dataset}/themes?month=${month}`),
      axios.get(`${API_BASE}/membership-images`)
    ]).then(([resOverview, resNetwork, resDaily, resThemes, resMemImg]) => {
      setOverview(resOverview.data);
      setNetworkData(resNetwork.data);
      setDailyStats(resDaily.data);
      setThemes(resThemes.data);
      setMembershipImages(resMemImg.data.images || []);
    }).catch(err => {
      console.error("Error fetching data:", err);
      // Fallback if APIs fail (e.g. data missing)
      setOverview(null);
      setNetworkData({ nodes: [], links: [] });
      setDailyStats([]);
      setThemes([]);
      setMembershipImages([]);
    }).finally(() => {
      setLoading(false);
    });
  }, [dataset, month]);

  const nextImage = () => setCurrentImageIdx((prev) => (prev + 1) % membershipImages.length);
  const prevImage = () => setCurrentImageIdx((prev) => (prev - 1 + membershipImages.length) % membershipImages.length);

  // Network graph node painting
  const paintNode = useCallback((node, ctx, globalScale) => {
    const label = node.id;
    const fontSize = 12 / globalScale;
    ctx.font = `${fontSize}px Sans-Serif`;
    const textWidth = ctx.measureText(label).width;
    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

    ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
    ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#38bdf8'; // Accent color
    ctx.fillText(label, node.x, node.y);

    node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
  }, []);

  const paintNodePointerArea = useCallback((node, color, ctx) => {
    ctx.fillStyle = color;
    const bckgDimensions = node.__bckgDimensions;
    bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
  }, []);

  return (
    <div className="app-container">
      <header>
        <h1>Community Intelligence Dashboard</h1>
        <div className="controls">
          <select 
              value={month} 
              onChange={e => setMonth(e.target.value)}
              className="dataset-selector"
            >
              {dataset === 'twitter' ? (
                <>
                  <option value="january">January 2017</option>
                  <option value="february">February 2017</option>
                  <option value="march">March 2017</option>
                  <option value="april">April 2017</option>
                </>
              ) : (
                <option value="october">October</option>
              )}
          </select>
          <select value={dataset} onChange={e => setDataset(e.target.value)}>
            {datasets.map(d => <option key={d} value={d}>{d.toUpperCase()}</option>)}
          </select>
        </div>
      </header>

      <main className="main-content">
        {loading ? (
          <div className="glass-panel loading">Loading pipeline data...</div>
        ) : (
          <>
            <div className="grid-overview">
              <div className="glass-panel metric-card">
                <span className="metric-title">Total Users</span>
                <span className="metric-value">
                  {overview?.users?.absolute?.toLocaleString() || '0'}
                </span>
              </div>
              <div className="glass-panel metric-card">
                <span className="metric-title">Total Messages</span>
                <span className="metric-value">
                  {overview?.messages?.absolute?.toLocaleString() || '0'}
                </span>
              </div>
              <div className="glass-panel metric-card">
                <span className="metric-title">Detected Communities</span>
                <span className="metric-value">
                  {overview?.communities?.absolute?.toLocaleString() || '0'}
                </span>
              </div>
              <div className="glass-panel metric-card">
                <span className="metric-title">Matched Themes</span>
                <span className="metric-value">
                  {overview?.communities?.matched?.toLocaleString() || '0'}
                </span>
              </div>
            </div>

            <div className="flex-row">
              <div className="glass-panel chart-container flex-1">
                <h2>
                  Interactive Community Network 
                  {networkData.is_mock && <span style={{ fontSize: '0.8rem', marginLeft: '1rem', background: '#eab308', color: '#000', padding: '0.2rem 0.5rem', borderRadius: '4px' }}>Demo Data</span>}
                </h2>
                <div className="graph-wrapper">
                  {networkData.nodes.length > 0 ? (
                    <ForceGraph2D
                      ref={fgRef}
                      graphData={networkData}
                      nodeCanvasObject={paintNode}
                      nodePointerAreaPaint={paintNodePointerArea}
                      linkColor={() => 'rgba(255,255,255,0.2)'}
                      backgroundColor="#020617"
                      d3VelocityDecay={0.1}
                      cooldownTicks={100}
                      onEngineStop={() => fgRef.current.zoomToFit(400)}
                    />
                  ) : (
                    <div className="loading" style={{ height: '100%' }}>No community graph data available for this month.</div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex-row" style={{ marginTop: '2rem' }}>
              <div className="glass-panel chart-container flex-1">
                <h2>Daily Message Velocity</h2>
                {dailyStats.length > 0 ? (
                  <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                      <LineChart data={dailyStats}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="date" stroke="#94a3b8" />
                        <YAxis stroke="#94a3b8" />
                        <RechartsTooltip 
                          contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid #38bdf8', borderRadius: '8px' }}
                        />
                        <Line type="monotone" dataKey="absolute" stroke="#38bdf8" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 8 }} />
                        <Line type="monotone" dataKey="weighted" stroke="#f472b6" strokeWidth={3} dot={{ r: 4 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="loading">No daily stats available.</div>
                )}
              </div>

              <div className="glass-panel chart-container flex-1">
                <h2>Top Community Themes</h2>
                {themes.length > 0 ? (
                  <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                      <BarChart data={themes} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis type="number" stroke="#94a3b8" />
                        <YAxis dataKey="theme" type="category" stroke="#94a3b8" width={150} />
                        <RechartsTooltip 
                          contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid #38bdf8', borderRadius: '8px' }}
                        />
                        <Bar dataKey="score" fill="#38bdf8" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="loading">No themes data available.</div>
                )}
              </div>
            </div>

            <div className="flex-row" style={{ marginTop: '2rem' }}>
              <div className="glass-panel chart-container flex-1">
                <h2>Temporal Analysis: Community Transition (Sankey)</h2>
                <div style={{ width: '100%', height: 600, borderRadius: '8px', overflow: 'hidden' }}>
                  <iframe 
                    src={`${API_BASE.replace('/api', '')}/api/static/sankey/community_transition.html`} 
                    style={{ width: '100%', height: '100%', border: 'none', background: 'white' }}
                    title="Community Transition Sankey"
                  />
                </div>
              </div>
            </div>

            <div className="flex-row" style={{ marginTop: '2rem' }}>
              <div className="glass-panel chart-container flex-1">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h2>Thematic Similarity Heatmap</h2>
                  <select 
                    value={themeSimilarityType} 
                    onChange={e => setThemeSimilarityType(e.target.value)}
                    style={{ padding: '0.4rem', borderRadius: '4px' }}
                  >
                    <option value="general">General Similarity</option>
                    <option value="absolute">Absolute Centrality</option>
                    <option value="weighted">Weighted Centrality</option>
                  </select>
                </div>
                <div style={{ width: '100%', height: 700, borderRadius: '8px', overflow: 'hidden', marginTop: '1rem' }}>
                  <iframe 
                    src={`${API_BASE.replace('/api', '')}/api/static/theme_similarity/${themeSimilarityType}_theme.html`} 
                    style={{ width: '100%', height: '100%', border: 'none', background: 'white' }}
                    title="Thematic Similarity Heatmap"
                  />
                </div>
              </div>
            </div>

            {membershipImages.length > 0 && (
              <div className="flex-row" style={{ marginTop: '2rem' }}>
                <div className="glass-panel chart-container flex-1">
                  <h2>Membership Changes Over Time</h2>
                  <div style={{ position: 'relative', width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
                      <button onClick={prevImage} style={{ background: '#38bdf8', color: '#000', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>Previous</button>
                      <span>Image {currentImageIdx + 1} of {membershipImages.length}</span>
                      <button onClick={nextImage} style={{ background: '#38bdf8', color: '#000', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer' }}>Next</button>
                    </div>
                    <img 
                      src={`${API_BASE.replace('/api', '')}${membershipImages[currentImageIdx]}`} 
                      alt="Membership Change" 
                      style={{ maxWidth: '100%', maxHeight: '600px', objectFit: 'contain', marginTop: '1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}
                    />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
