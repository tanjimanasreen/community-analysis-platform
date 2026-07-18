import React, { useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Maximize2, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import ArtifactStatusBadge from '../ArtifactStatusBadge';
import ErrorState from '../states/ErrorState';
import LoadingState from '../states/LoadingState';
import { formatCount } from '../../features/overview/overviewUtils';

export default function NetworkGraph({ network, metric, isLoading, error, onRetry }) {
  const containerRef = useRef(null);
  const graphRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 320 });

  useEffect(() => {
    const target = containerRef.current;
    if (!target) return undefined;
    const update = (width, height) => setDimensions({
      width: Math.max(width, 320),
      height: Math.max(height, 320),
    });
    if (typeof ResizeObserver === 'undefined') {
      update(target.clientWidth || 800, target.clientHeight || 320);
      return undefined;
    }
    const observer = new ResizeObserver(([entry]) => {
      update(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(target);
    return () => observer.disconnect();
  }, []);

  const graphData = useMemo(() => {
    if (!network) return { nodes: [], links: [] };
    const degree = new Map();
    for (const edge of network.edges) {
      degree.set(edge.source, (degree.get(edge.source) || 0) + 1);
      degree.set(edge.target, (degree.get(edge.target) || 0) + 1);
    }
    return {
      nodes: network.nodes.map((node) => ({
        ...node,
        group: node.community_ids[0] || 'unassigned',
        color: communityColor(node.community_ids[0] || 'unassigned'),
        val: 2.5 + Math.sqrt(degree.get(node.id) || 0),
      })),
      links: network.edges.map((edge, index) => ({
        id: `${edge.source}-${edge.target}-${index}`,
        source: edge.source,
        target: edge.target,
        value: edge.weight,
      })),
    };
  }, [network]);

  if (isLoading) return <LoadingState title="Loading network preview" />;
  if (error) return <ErrorState error={error} title="Network preview could not be loaded" onRetry={onRetry} />;

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col min-h-[430px] overflow-hidden relative">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-4 relative z-10">
        <div>
          <div className="flex items-center flex-wrap gap-2">
            <h3 className="text-sm font-bold text-text-heading">Community Network · {metric.toUpperCase()}</h3>
            {network?.sampled && (
              <ArtifactStatusBadge
                label="Sampled preview"
                status="warning"
                title="The API returned a bounded subset of the available graph."
              />
            )}
          </div>
          {network && (
            <p className="mt-2 text-xs text-muted">
              {formatCount(network.returned_nodes)} / {formatCount(network.available_nodes)} nodes ·{' '}
              {formatCount(network.returned_edges)} / {formatCount(network.available_edges)} edges
            </p>
          )}
          <p className="mt-1 text-[11px] text-muted">Node size encodes degree within this returned preview only.</p>
        </div>
        {network && graphData.nodes.length > 0 && (
          <div className="flex border border-border rounded-lg overflow-hidden">
            <GraphButton label="Zoom in" onClick={() => graphRef.current?.zoom?.(1.3, 300)} icon={ZoomIn} />
            <GraphButton label="Zoom out" onClick={() => graphRef.current?.zoom?.(0.75, 300)} icon={ZoomOut} />
            <GraphButton label="Fit graph" onClick={() => graphRef.current?.zoomToFit?.(400, 30)} icon={Maximize2} />
            <GraphButton label="Reset graph" onClick={() => {
              graphRef.current?.centerAt?.(0, 0, 300);
              graphRef.current?.zoom?.(1, 300);
            }} icon={RotateCcw} last />
          </div>
        )}
      </div>

      <div className="flex-grow w-full min-h-[320px] relative" ref={containerRef}>
        {!network || graphData.nodes.length === 0 || graphData.links.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-center" aria-live="polite">
            <div>
              <p className="font-semibold text-text-heading">No network edges available</p>
              <p className="mt-2 text-sm text-muted">The selected run and metric returned an empty graph preview.</p>
            </div>
          </div>
        ) : dimensions.width > 0 ? (
          <ForceGraph2D
            ref={graphRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeColor="color"
            nodeVal="val"
            nodeRelSize={4}
            nodeLabel={(node) => `${node.id} · community ${node.group}`}
            linkColor={() => 'rgba(148, 163, 184, 0.25)'}
            linkWidth={(link) => Math.max(0.5, Math.min(3, Number(link.value) || 0.5))}
            backgroundColor="rgba(0,0,0,0)"
            d3AlphaDecay={0.03}
            d3VelocityDecay={0.35}
            cooldownTicks={80}
            enableZoomInteraction
            enablePanInteraction
          />
        ) : null}
      </div>
    </section>
  );
}

function GraphButton({ label, onClick, icon: Icon, last = false }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`p-2 bg-panel hover:bg-panel-soft text-text transition-colors ${last ? '' : 'border-r border-border'}`}
    >
      <Icon size={15} />
    </button>
  );
}

function communityColor(value) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) % 360;
  }
  return `hsl(${hash} 68% 64%)`;
}
