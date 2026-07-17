import { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export default function NetworkGraph({ communities }) {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  useEffect(() => {
    // Resize observer to make the graph responsive
    const observeTarget = containerRef.current;
    if (!observeTarget) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        });
      }
    });

    resizeObserver.observe(observeTarget);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    // Generate mock graph data for the network visualization
    const N = 120; // nodes
    const colors = ['#7aa2f7', '#bb9af7', '#9ece6a', '#e0af68', '#f7768e', '#ff9e64', '#a9b1d6'];

    // Create clusters
    const nodes = Array.from({ length: N }).map((_, i) => ({
      id: i,
      group: Math.floor(i / (N / 6)),
      color: colors[Math.floor(i / (N / 6)) % colors.length],
      val: Math.random() * 5 + 1 // size
    }));

    // Create links between nodes in the same cluster mainly, some cross-cluster
    const links = [];
    for (let i = 0; i < N; i++) {
      const numLinks = Math.floor(Math.random() * 3) + 1;
      for (let j = 0; j < numLinks; j++) {
        // 80% chance to link within same group
        const targetGroup = Math.random() > 0.2 ? nodes[i].group : Math.floor(Math.random() * 6);
        const groupNodes = nodes.filter(n => n.group === targetGroup);
        if (groupNodes.length > 0) {
          const target = groupNodes[Math.floor(Math.random() * groupNodes.length)].id;
          if (target !== i) {
            links.push({
              source: i,
              target: target,
              value: Math.random()
            });
          }
        }
      }
    }

    setGraphData({ nodes, links });
  }, []);

  return (
    <div className="bg-panel border border-border rounded-xl p-5 flex flex-col h-full overflow-hidden relative">
      <div className="flex justify-between items-start mb-2 relative z-10">
        <div>
          <h3 className="text-sm font-bold text-text-heading flex items-center gap-2">
            Community Network (WIF)
            <div className="w-4 h-4 rounded-full border border-border flex items-center justify-center text-muted text-[10px] cursor-help">
              i
            </div>
          </h3>
          <div className="flex flex-col gap-1 mt-4">
            <div className="flex items-center gap-2 text-xs text-muted"><span className="w-2 h-2 rounded-full bg-[#7aa2f7]"></span> Current Events</div>
            <div className="flex items-center gap-2 text-xs text-muted"><span className="w-2 h-2 rounded-full bg-[#bb9af7]"></span> Personal Support</div>
            <div className="flex items-center gap-2 text-xs text-muted"><span className="w-2 h-2 rounded-full bg-[#9ece6a]"></span> Civic Discourse</div>
            <div className="flex items-center gap-2 text-xs text-muted"><span className="w-2 h-2 rounded-full bg-[#e0af68]"></span> Education</div>
            <div className="flex items-center gap-2 text-xs text-muted"><span className="w-2 h-2 rounded-full bg-[#f7768e]"></span> Emotional Topics</div>
            <div className="flex items-center gap-2 text-xs text-muted"><span className="w-2 h-2 rounded-full bg-[#ff9e64]"></span> News Discussion</div>
            <div className="flex items-center gap-2 text-xs text-muted"><span className="w-2 h-2 rounded-full bg-[#a9b1d6]"></span> Other</div>
          </div>
          <div className="mt-4 text-xs font-medium text-muted">
            <p>Nodes: <span className="text-text">12,458</span></p>
            <p>Edges: <span className="text-text">78,932</span></p>
          </div>
        </div>

        {/* Graph controls mockup */}
        <div className="flex flex-col border border-border rounded-lg overflow-hidden z-10">
          <button className="p-1.5 bg-panel hover:bg-panel-soft text-text border-b border-border transition-colors">⛶</button>
          <button className="p-1.5 bg-panel hover:bg-panel-soft text-text border-b border-border transition-colors">+</button>
          <button className="p-1.5 bg-panel hover:bg-panel-soft text-text border-b border-border transition-colors">-</button>
          <button className="p-1.5 bg-panel hover:bg-panel-soft text-text transition-colors">⟲</button>
        </div>
      </div>

      <div className="flex-grow w-full h-[300px] mt-[-180px] relative z-0" ref={containerRef}>
        {dimensions.width > 0 && dimensions.height > 0 && (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height + 180}
            graphData={graphData}
            nodeColor="color"
            nodeRelSize={4}
            linkColor={() => 'rgba(169, 177, 214, 0.15)'}
            linkWidth={0.5}
            backgroundColor="transparent"
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            cooldownTicks={100}
            enableZoomInteraction={false}
            enablePanInteraction={false}
          />
        )}
      </div>
    </div>
  );
}
