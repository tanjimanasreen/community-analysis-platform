import React, { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Maximize2, RotateCcw, Tags, X, ZoomIn, ZoomOut } from 'lucide-react';
import ArtifactStatusBadge from '../ArtifactStatusBadge';
import ErrorState from '../states/ErrorState';
import LoadingState from '../states/LoadingState';
import { formatCount } from '../../features/overview/overviewUtils';
import {
  metricWeightLabel,
  transformNetworkResponse,
} from '../../features/networks/networkModel';

const ForceGraph2D = lazy(() => import('react-force-graph-2d'));

export default function NetworkGraph({
  network,
  metric,
  selectedCommunityId = null,
  isLoading,
  error,
  onRetry,
  onSelectCommunity,
  onSelectNode,
  onClearSelection,
  height = 320,
}) {
  const containerRef = useRef(null);
  const graphRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height });
  const [showLabels, setShowLabels] = useState(false);
  const [communityChoices, setCommunityChoices] = useState(null);

  useEffect(() => {
    const target = containerRef.current;
    if (!target) return undefined;
    const update = (width, nextHeight) => setDimensions({
      width: Math.max(width, 320),
      height: Math.max(nextHeight, height),
    });
    if (typeof ResizeObserver === 'undefined') {
      update(target.clientWidth || 800, target.clientHeight || height);
      return undefined;
    }
    const observer = new ResizeObserver(([entry]) => {
      update(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(target);
    return () => observer.disconnect();
  }, [height]);

  const graphData = useMemo(
    () => transformNetworkResponse(network, selectedCommunityId),
    [network, selectedCommunityId],
  );

  const handleNodeClick = (node) => {
    onSelectNode?.(node);
    if (node.communityIds.length === 1) {
      onSelectCommunity?.(node.communityIds[0]);
      setCommunityChoices(null);
      return;
    }
    if (node.communityIds.length > 1) {
      setCommunityChoices(node);
      return;
    }
    setCommunityChoices(null);
  };

  if (isLoading) return <LoadingState title="Loading network graph" />;
  if (error) return <ErrorState error={error} title="Network graph could not be loaded" onRetry={onRetry} />;

  return (
    <section className="bg-panel border border-border rounded-xl p-5 flex flex-col overflow-hidden relative h-full" style={{ minHeight: Math.max(430, height + 110) }}>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-4 relative z-10">
        <div>
          <div className="flex items-center flex-wrap gap-2">
            <h3 className="text-sm font-bold text-text-heading">Community Network · {metric.toUpperCase()}</h3>
            {network?.sampled && (
              <ArtifactStatusBadge
                label="Sampled graph"
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
          <p className="mt-1 text-[11px] text-muted">
            Node size is degree within returned graph. Edge width and opacity encode {metricWeightLabel(metric).toLowerCase()}.
          </p>
        </div>
        {network && graphData.nodes.length > 0 && (
          <div className="flex border border-border rounded-lg overflow-hidden">
            <GraphButton label="Zoom in" onClick={() => graphRef.current?.zoom?.(1.3, 300)} icon={ZoomIn} />
            <GraphButton label="Zoom out" onClick={() => graphRef.current?.zoom?.(0.75, 300)} icon={ZoomOut} />
            <GraphButton label="Zoom to fit" onClick={() => graphRef.current?.zoomToFit?.(400, 30)} icon={Maximize2} />
            <GraphButton
              label={showLabels ? 'Hide node labels' : 'Show node labels'}
              onClick={() => setShowLabels((current) => !current)}
              icon={Tags}
            />
            {onClearSelection && (
              <GraphButton label="Clear community selection" onClick={onClearSelection} icon={X} />
            )}
            <GraphButton
              label="Reset graph view"
              onClick={() => {
                graphRef.current?.centerAt?.(0, 0, 300);
                graphRef.current?.zoom?.(1, 300);
              }}
              icon={RotateCcw}
              last
            />
          </div>
        )}
      </div>

      <div className="flex-grow w-full relative" style={{ minHeight: height }} ref={containerRef}>
        {!network || graphData.nodes.length === 0 || graphData.links.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center text-center" aria-live="polite">
            <div>
              <p className="font-semibold text-text-heading">No network edges available</p>
              <p className="mt-2 text-sm text-muted">The selected run, metric, and minimum weight returned an empty graph.</p>
            </div>
          </div>
        ) : dimensions.width > 0 ? (
          <Suspense fallback={<LoadingState title="Preparing interactive graph" />}>
            <ForceGraph2D
              ref={graphRef}
              width={dimensions.width}
              height={dimensions.height}
              graphData={graphData}
              nodeColor="color"
              nodeVal="val"
              nodeRelSize={4}
              nodeLabel={(node) => [
                `Node ${node.id}`,
                `In-degree within returned graph: ${node.inDegree}`,
                `Out-degree within returned graph: ${node.outDegree}`,
                `Communities: ${node.communityIds.length ? node.communityIds.join(', ') : 'unassigned'}`,
              ].join('\n')}
              nodeCanvasObject={showLabels ? drawNodeLabel : undefined}
              nodeCanvasObjectMode={showLabels ? () => 'after' : undefined}
              onNodeClick={handleNodeClick}
              linkColor={(link) => `rgba(148, 163, 184, ${link.opacity})`}
              linkWidth={(link) => link.width}
              linkLabel={(link) => `${metric.toUpperCase()} weight: ${link.weight}`}
              backgroundColor="rgba(0,0,0,0)"
              d3AlphaDecay={0.03}
              d3VelocityDecay={0.35}
              cooldownTicks={80}
              enableZoomInteraction
              enablePanInteraction
            />
          </Suspense>
        ) : null}

        {network && graphData.links.length > 0 && (
          <div className="absolute bottom-3 left-3 z-10 rounded-lg border border-border bg-panel/90 px-3 py-2 text-[11px] text-muted">
            <span className="mr-2 inline-block h-0.5 w-8 align-middle bg-slate-400" />
            {metricWeightLabel(metric)}
          </div>
        )}

        {communityChoices && (
          <div className="absolute right-3 top-3 z-20 w-64 rounded-xl border border-border bg-panel p-4 shadow-lg">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-text-heading">Choose a community</p>
                <p className="mt-1 text-[11px] text-muted">Node {communityChoices.id} belongs to multiple returned communities.</p>
              </div>
              <button
                type="button"
                aria-label="Close community chooser"
                onClick={() => setCommunityChoices(null)}
                className="rounded p-1 text-muted hover:bg-panel-soft hover:text-text-heading"
              >
                <X size={14} />
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {communityChoices.communityIds.map((communityId) => (
                <button
                  type="button"
                  key={communityId}
                  onClick={() => {
                    onSelectCommunity?.(communityId);
                    setCommunityChoices(null);
                  }}
                  className="rounded-lg border border-border px-2.5 py-1.5 text-xs font-semibold text-primary hover:bg-primary/10"
                >
                  {communityId}
                </button>
              ))}
            </div>
          </div>
        )}
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

function drawNodeLabel(node, context, globalScale) {
  const label = String(node.id);
  const fontSize = Math.max(3, 11 / globalScale);
  context.font = `${fontSize}px sans-serif`;
  context.fillStyle = 'rgba(226, 232, 240, 0.9)';
  context.fillText(label, node.x + 6, node.y + 3);
}
