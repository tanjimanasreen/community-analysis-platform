import React, { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Eye, EyeOff, Maximize2, Minimize2, RotateCcw, Search, Tags, X, ZoomIn, ZoomOut } from 'lucide-react';
import ArtifactStatusBadge from '../ArtifactStatusBadge';
import ErrorState from '../states/ErrorState';
import LoadingState from '../states/LoadingState';
import { formatCount } from '../../features/overview/overviewUtils';
import {
  metricWeightLabel,
  parseMinWeight,
  transformNetworkResponse,
} from '../../features/networks/networkModel';

const ForceGraph2D = lazy(() => import('react-force-graph-2d'));

export default function NetworkGraph({
  network,
  metric,
  periodLabel = null,
  selectedCommunityId = null,
  highlightNodeId = null,
  isLoading,
  error,
  onRetry,
  onSelectCommunity,
  onSelectNode,
  onClearSelection,
  onInteraction,
  height = 320,
}) {
  const panelRef = useRef(null);
  const stageRef = useRef(null);
  const graphRef = useRef(null);
  const [stageWidth, setStageWidth] = useState(0);
  const [showLabels, setShowLabels] = useState(false);
  const [showIsolated, setShowIsolated] = useState(true);
  const [minimumWeight, setMinimumWeight] = useState(0);
  const [communitySearch, setCommunitySearch] = useState('');
  const [hoveredNodeId, setHoveredNodeId] = useState(null);
  const [communityChoices, setCommunityChoices] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [viewportHeight, setViewportHeight] = useState(() => windowHeight());
  const graphHeight = isFullscreen ? Math.max(420, viewportHeight - 220) : height;
  const view = network?.view ?? 'users';
  const communityMap = view === 'communities';
  const isStatic = network?.sampling_strategy === 'full_graph';
  const prefersReducedMotion = usePrefersReducedMotion();
  const staticLayout = isStatic || prefersReducedMotion;

  useEffect(() => {
    const target = stageRef.current;
    if (!target) return undefined;
    const updateWidth = (width) => setStageWidth(Math.max(Math.floor(width), 240));
    updateWidth(target.clientWidth || 800);
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(([entry]) => updateWidth(entry.contentRect.width));
    observer.observe(target);
    return () => observer.disconnect();
  }, [isFullscreen]);

  useEffect(() => {
    const updateViewportHeight = () => setViewportHeight(windowHeight());
    window.addEventListener('resize', updateViewportHeight);
    return () => window.removeEventListener('resize', updateViewportHeight);
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      const active = document.fullscreenElement === panelRef.current;
      setIsFullscreen(active);
      requestAnimationFrame(() => {
        graphRef.current?.resize?.();
        graphRef.current?.zoomToFit?.(350, 36);
      });
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const graphData = useMemo(
    () => transformNetworkResponse(network, selectedCommunityId),
    [network, selectedCommunityId],
  );

  const visibleGraphData = useMemo(() => {
    if (!communityMap) return graphData;
    const links = graphData.links.filter((link) => link.weight >= minimumWeight);
    const connected = new Set(links.flatMap((link) => [linkEndpointId(link.source), linkEndpointId(link.target)]));
    const nodes = showIsolated
      ? graphData.nodes
      : graphData.nodes.filter((node) => connected.has(node.id));
    const nodeIds = new Set(nodes.map((node) => node.id));
    return {
      ...graphData,
      nodes,
      links: links.filter((link) => nodeIds.has(linkEndpointId(link.source)) && nodeIds.has(linkEndpointId(link.target))),
    };
  }, [communityMap, graphData, minimumWeight, showIsolated]);

  const maxInternalWeight = useMemo(
    () => Math.max(1, ...graphData.nodes.map((node) => Number(node.internalWeight) || 0)),
    [graphData.nodes],
  );

  const largestCommunityIds = useMemo(
    () => new Set(
      [...graphData.nodes]
        .sort((left, right) => (right.memberCount ?? 0) - (left.memberCount ?? 0))
        .slice(0, 8)
        .map((node) => node.id),
    ),
    [graphData.nodes],
  );

  const handleNodeClick = (node) => {
    onSelectNode?.(node);
    if (node.nodeType === 'community') {
      onSelectCommunity?.(node.id);
      setCommunityChoices(null);
      return;
    }
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

  useEffect(() => {
    if (!visibleGraphData.nodes.length || stageWidth <= 0) return undefined;
    const timer = setTimeout(() => {
      graphRef.current?.resize?.();
      graphRef.current?.zoomToFit?.(350, 36);
    }, 140);
    return () => clearTimeout(timer);
  }, [graphHeight, stageWidth, visibleGraphData.nodes.length, visibleGraphData.links.length]);

  useEffect(() => {
    if (!communityMap) return;
    for (const node of graphData.nodes) {
      delete node.fx;
      delete node.fy;
    }
    if (!selectedCommunityId) return;
    const selected = graphData.nodes.find((node) => node.id === String(selectedCommunityId));
    if (!selected) return;
    selected.fx = selected.x;
    selected.fy = selected.y;
    if (!staticLayout) graphRef.current?.d3ReheatSimulation?.();
  }, [communityMap, graphData.nodes, selectedCommunityId, staticLayout]);

  useEffect(() => {
    const targetId = communityMap ? selectedCommunityId : highlightNodeId;
    if (!targetId || !visibleGraphData.nodes.length) return;
    const node = visibleGraphData.nodes.find((candidate) => candidate.id === String(targetId));
    if (!node) return;
    const timer = setTimeout(() => {
      const duration = prefersReducedMotion ? 0 : 500;
      graphRef.current?.centerAt?.(node.x, node.y, duration);
      graphRef.current?.zoom?.(communityMap ? 2 : 3, duration);
    }, 160);
    return () => clearTimeout(timer);
  }, [communityMap, highlightNodeId, prefersReducedMotion, selectedCommunityId, visibleGraphData.nodes]);

  const locateCommunity = () => {
    const query = normalizeCommunitySearch(communitySearch);
    if (!query) return;
    const node = graphData.nodes.find((candidate) => normalizeCommunitySearch(candidate.id) === query);
    if (!node) return;
    onSelectCommunity?.(node.id);
    const duration = prefersReducedMotion ? 0 : 500;
    graphRef.current?.centerAt?.(node.x, node.y, duration);
    graphRef.current?.zoom?.(2.6, duration);
  };

  const toggleFullscreen = async () => {
    if (!panelRef.current || !document.fullscreenEnabled) {
      graphRef.current?.zoomToFit?.(350, 36);
      return;
    }
    if (document.fullscreenElement === panelRef.current) await document.exitFullscreen();
    else await panelRef.current.requestFullscreen();
  };

  if (isLoading) return <LoadingState title="Loading network graph" />;
  if (error) return <ErrorState error={error} title="Network graph could not be loaded" onRetry={onRetry} />;

  const coverage = network?.coverage;
  const graphTitle = communityMap ? 'Prominent Community Network' : 'User Network Sample';
  const crossEdgesAvailable = coverage?.cross_community_edges_available ?? false;

  return (
    <section
      ref={panelRef}
      className={`panel network-graph-panel ${isFullscreen ? 'network-graph-panel--fullscreen' : ''}`}
      style={{ minHeight: Math.max(470, height + 150) }}
      onPointerDown={onInteraction}
    >
      <div className="page-header network-graph-header">
        <div>
          <div className="flex items-center flex-wrap gap-2">
            <h3 className="text-sm font-bold text-text-heading">
              {graphTitle}{periodLabel ? ` · ${periodLabel}` : ''} · {metric.toUpperCase()}
            </h3>
            {communityMap && coverage?.is_complete && (
              <ArtifactStatusBadge
                label="Complete prominent partition"
                status="verified"
                title="All published prominent communities are represented."
              />
            )}
            {communityMap && !crossEdgesAvailable && (
              <ArtifactStatusBadge
                label="Legacy nodes-only view"
                status="warning"
                title="This run predates the canonical cross-community interaction artifact. No links are inferred."
              />
            )}
            {network?.sampled && (
              <ArtifactStatusBadge
                label="Bounded response"
                status="warning"
                title="The API returned a deterministic bounded subset and reports exact coverage."
              />
            )}
          </div>

          {network && communityMap && coverage && (
            <p className="mt-2 text-xs text-muted">
              {formatCount(coverage.represented_communities)} / {formatCount(coverage.available_communities)} prominent communities ·{' '}
              {formatCount(coverage.represented_users)} / {formatCount(coverage.available_users)} members ·{' '}
              {formatCount(network.returned_edges)} / {formatCount(network.available_edges)} cross-community directions
              {coverage.weight_coverage_ratio !== null && coverage.weight_coverage_ratio !== undefined
                ? ` · ${(coverage.weight_coverage_ratio * 100).toFixed(1)}% of ${metric.toUpperCase()} cross-community weight`
                : ''}
            </p>
          )}
          {network && !communityMap && (
            <p className="mt-2 text-xs text-muted">
              {formatCount(network.returned_nodes)} / {formatCount(network.available_nodes)} users ·{' '}
              {formatCount(network.returned_edges)} / {formatCount(network.available_edges)} edges
              {coverage && ` · ${formatCount(coverage.represented_communities)} / ${formatCount(coverage.available_communities)} communities`}
              {coverage?.weight_coverage_ratio !== null && coverage?.weight_coverage_ratio !== undefined
                ? ` · ${(coverage.weight_coverage_ratio * 100).toFixed(1)}% of ${metric.toUpperCase()} weight`
                : ''}
            </p>
          )}

          {communityMap ? (
            <p className="mt-1 text-[11px] text-muted">
              One node per prominent community. Node area follows member count. A line appears only when the canonical monthly graph contains at least one user interaction across the two communities; width encodes logarithmic {metric.toUpperCase()} weight and opacity encodes contributing user pairs. Reciprocal directions share one line. Controls affect presentation only—not community detection.
            </p>
          ) : (
            <p className="mt-1 text-[11px] text-muted">
              Deterministic {network?.sampling_strategy === 'community_balanced' ? 'community-aware' : 'strongest-interaction'} preview. Node size is degree within the returned graph. Edge width and opacity encode {metricWeightLabel(metric).toLowerCase()}.
            </p>
          )}

          {communityMap && coverage?.cross_community_edges_reason && !crossEdgesAvailable && (
            <p className="mt-2 text-[11px] font-medium text-warning" role="status">
              Cross-community links are unavailable for this legacy run. Prominent nodes remain visible; no links were fabricated.
            </p>
          )}
          {graphData.droppedLinks > 0 && (
            <p className="mt-2 text-[11px] font-medium text-warning" role="status">
              {formatCount(graphData.droppedLinks)} malformed edge{graphData.droppedLinks === 1 ? '' : 's'} {graphData.droppedLinks === 1 ? 'was' : 'were'} omitted because an endpoint was missing from the API node set.
            </p>
          )}
        </div>

        {network && graphData.nodes.length > 0 && (
          <div className="control-panel network-graph-controls">
            <GraphButton label="Zoom in" onClick={() => graphRef.current?.zoom?.(1.3, prefersReducedMotion ? 0 : 300)} icon={ZoomIn} />
            <GraphButton label="Zoom out" onClick={() => graphRef.current?.zoom?.(0.75, prefersReducedMotion ? 0 : 300)} icon={ZoomOut} />
            <GraphButton label="Fit graph to view" onClick={() => graphRef.current?.zoomToFit?.(prefersReducedMotion ? 0 : 350, 36)} icon={Maximize2} />
            <GraphButton label={showLabels ? 'Hide node labels' : 'Show node labels'} onClick={() => setShowLabels((current) => !current)} icon={Tags} />
            {communityMap && (
              <GraphButton label={showIsolated ? 'Hide isolated communities' : 'Show isolated communities'} onClick={() => setShowIsolated((current) => !current)} icon={showIsolated ? EyeOff : Eye} />
            )}
            {onClearSelection && selectedCommunityId && (
              <GraphButton label="Clear community selection" onClick={onClearSelection} icon={X} />
            )}
            <GraphButton label={isFullscreen ? 'Exit fullscreen graph' : 'Open fullscreen graph'} onClick={() => void toggleFullscreen()} icon={isFullscreen ? Minimize2 : Maximize2} />
            <GraphButton
              label="Reset graph view"
              onClick={() => {
                if (!staticLayout) graphRef.current?.d3ReheatSimulation?.();
                graphRef.current?.zoomToFit?.(prefersReducedMotion ? 0 : 350, 36);
              }}
              icon={RotateCcw}
              last
            />
          </div>
        )}
      </div>

      {communityMap && network && graphData.nodes.length > 0 && (
        <div className="community-network-filters" aria-label="Community network presentation filters">
          <label>
            <span>Find community</span>
            <div className="community-network-search">
              <input
                type="search"
                value={communitySearch}
                placeholder="Example: C41"
                onChange={(event) => setCommunitySearch(event.target.value)}
                onKeyDown={(event) => { if (event.key === 'Enter') locateCommunity(); }}
              />
              <button type="button" onClick={locateCommunity} aria-label="Find community"><Search size={14} /></button>
            </div>
          </label>
          <label>
            <span>Minimum cross-community weight</span>
            <input
              type="number"
              min="0"
              step={metric === 'if' ? '1' : '0.01'}
              value={minimumWeight}
              onChange={(event) => setMinimumWeight(parseMinWeight(event.target.value))}
            />
          </label>
          <p>{formatCount(visibleGraphData.nodes.length)} nodes · {formatCount(visibleGraphData.links.length)} visual connections shown</p>
        </div>
      )}

      <div className="chart-container network-graph-container">
        <div
          className="network-graph-stage"
          style={{ height: graphHeight }}
          ref={stageRef}
          data-testid="network-graph-stage"
        >
          {!network || visibleGraphData.nodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center text-center" aria-live="polite">
              <div>
                <p className="font-semibold text-text-heading">No network nodes available</p>
                <p className="mt-2 text-sm text-muted">The selected run, metric, period, and presentation filters returned an empty graph.</p>
              </div>
            </div>
          ) : (
            <Suspense fallback={<LoadingState title="Preparing interactive graph" />}>
              <div style={{ display: 'none' }} data-testid="debug-stagewidth">{stageWidth}</div>
              <ForceGraph2D
                key={`${network.run_id}:${network.period ?? 'all-periods'}:${metric}:${view}:${network.sampling_strategy ?? 'none'}`}
                ref={graphRef}
                width={stageWidth}
                height={graphHeight}
                graphData={visibleGraphData}
                nodeColor={(node) => node.id === String(selectedCommunityId ?? highlightNodeId) ? 'hsl(42 95% 60%)' : node.color}
                nodeVal={(node) => node.id === String(selectedCommunityId ?? highlightNodeId) ? node.val * 1.35 : node.val}
                nodeRelSize={communityMap ? 1.15 : 5}
                nodeLabel={nodeTooltip}
                nodeCanvasObject={(node, context, globalScale) => {
                  const searched = normalizeCommunitySearch(node.id) === normalizeCommunitySearch(communitySearch);
                  const shouldLabel = showLabels
                    || node.id === String(selectedCommunityId ?? highlightNodeId)
                    || node.id === String(hoveredNodeId)
                    || searched
                    || (communityMap && largestCommunityIds.has(node.id));
                  if (communityMap) drawCommunityOverlay(
                    node,
                    context,
                    globalScale,
                    shouldLabel,
                    node.id === String(selectedCommunityId),
                    maxInternalWeight,
                  );
                  else if (shouldLabel) drawNodeLabel(node, context, globalScale);
                }}
                nodeCanvasObjectMode={() => 'after'}
                onNodeHover={(node) => setHoveredNodeId(node?.id ?? null)}
                onNodeClick={handleNodeClick}
                linkColor={(link) => {
                  const selected = String(selectedCommunityId);
                  const touchesSelection = selectedCommunityId && (linkEndpointId(link.source) === selected || linkEndpointId(link.target) === selected);
                  return touchesSelection
                    ? `rgba(56, 189, 248, ${Math.min(1, link.opacity + 0.2)})`
                    : `rgba(148, 163, 184, ${link.opacity})`;
                }}
                linkWidth={(link) => link.width}
                linkCurvature="curvature"
                linkDirectionalArrowLength={communityMap ? 0 : (visibleGraphData.links.length ? 3 : 0)}
                linkDirectionalArrowRelPos={0.8}
                linkCanvasObject={communityMap ? drawCommunityDirectionArrows : undefined}
                linkCanvasObjectMode={communityMap ? () => 'after' : undefined}
                linkLabel={(link) => linkTooltip(link, metric, communityMap)}
                backgroundColor="rgba(0,0,0,0)"
                d3AlphaDecay={staticLayout ? 1 : 0.035}
                d3VelocityDecay={staticLayout ? 1 : 0.38}
                warmupTicks={staticLayout ? 0 : 40}
                cooldownTicks={staticLayout ? 0 : 160}
                onEngineStop={() => graphRef.current?.zoomToFit?.(350, 36)}
                enableZoomInteraction
                enablePanInteraction
                enableNodeDrag={!staticLayout}
              />
            </Suspense>
          )}

          {network && visibleGraphData.links.length > 0 && (
            <div className="absolute bottom-3 left-3 z-10 rounded-lg border border-border bg-surface/90 px-3 py-2 text-[11px] text-muted">
              <span className="mr-2 inline-block h-0.5 w-8 align-middle bg-slate-400" />
              {communityMap ? `${metric.toUpperCase()} cross-community weight` : metricWeightLabel(metric)}
            </div>
          )}

          {communityChoices && (
            <div className="absolute right-3 top-3 z-20 w-64 rounded-xl border border-border bg-surface p-4 shadow-lg">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold text-text-heading">Choose a community</p>
                  <p className="mt-1 text-[11px] text-muted">Node {communityChoices.id} belongs to multiple returned communities.</p>
                </div>
                <button type="button" aria-label="Close community chooser" onClick={() => setCommunityChoices(null)} className="rounded p-1 text-muted hover:bg-surface-soft hover:text-text-heading"><X size={14} /></button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {communityChoices.communityIds.map((communityId) => (
                  <button type="button" key={communityId} onClick={() => { onSelectCommunity?.(communityId); setCommunityChoices(null); }} className="rounded-lg border border-border px-2.5 py-1.5 text-xs font-semibold text-primary hover:bg-primary/10">
                    {communityId}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function GraphButton({ label, onClick, icon: Icon, last = false }) {
  return (
    <button type="button" aria-label={label} title={label} onClick={onClick} className={`p-2 bg-surface hover:bg-surface-soft text-text transition-colors ${last ? '' : 'border-r border-border'}`}>
      <Icon size={15} />
    </button>
  );
}

function nodeTooltip(node) {
  if (node.nodeType === 'community') {
    return [
      `Community C${node.id}`,
      `Members: ${node.memberCount ?? 'unavailable'}`,
      `Internal edges: ${node.internalEdgeCount ?? 'unavailable'}`,
      `Internal weight: ${node.internalWeight ?? 'unavailable'}`,
      `Connected prominent communities: ${node.crossCommunityNeighborCount ?? 'unavailable'}`,
      `Inbound cross-community weight: ${node.inboundCrossCommunityWeight ?? 'unavailable'}`,
      `Outbound cross-community weight: ${node.outboundCrossCommunityWeight ?? 'unavailable'}`,
      'Click to open the community inspector.',
    ].join('\n');
  }
  return [
    `User ${node.id}`,
    `In-degree within returned graph: ${node.inDegree}`,
    `Out-degree within returned graph: ${node.outDegree}`,
    `Communities: ${node.communityIds.length ? node.communityIds.join(', ') : 'unassigned'}`,
  ].join('\n');
}

function linkTooltip(link, metric, communityMap) {
  if (!communityMap) return `${metric.toUpperCase()} weight: ${link.weight}${link.edgeCount > 1 ? ` · ${link.edgeCount} edges` : ''}`;
  const source = linkEndpointId(link.source);
  const target = linkEndpointId(link.target);
  const lines = [
    `Communities C${source} ↔ C${target}`,
    `Total ${metric.toUpperCase()} weight: ${formatTooltipNumber(link.weight)}`,
    `Distinct directed user pairs: ${formatCount(link.userPairCount)}`,
  ];
  if (link.forwardWeight > 0) lines.push(`C${source} → C${target}: ${formatTooltipNumber(link.forwardWeight)} (${formatCount(link.forwardUserPairCount)} pairs)`);
  if (link.reverseWeight > 0) lines.push(`C${target} → C${source}: ${formatTooltipNumber(link.reverseWeight)} (${formatCount(link.reverseUserPairCount)} pairs)`);
  return lines.join('\n');
}

function drawCommunityOverlay(node, context, globalScale, showLabel, selected, maxInternalWeight) {
  const radius = Math.sqrt(Math.max(1, node.val)) * 1.15;
  context.save();
  context.beginPath();
  context.arc(node.x, node.y, radius + (selected ? 4 : 2), 0, Math.PI * 2);
  const internalWeight = Math.max(0, Number(node.internalWeight) || 0);
  const normalizedWeight = Math.log1p(internalWeight) / Math.log1p(Math.max(1, maxInternalWeight));
  context.strokeStyle = selected
    ? 'rgba(250, 204, 21, 0.95)'
    : `rgba(226, 232, 240, ${0.2 + normalizedWeight * 0.62})`;
  context.lineWidth = Math.max(0.7, (selected ? 2.4 : 1.1) / globalScale);
  context.stroke();
  context.restore();
  if (showLabel) drawNodeLabel(node, context, globalScale);
}

function drawNodeLabel(node, context, globalScale) {
  const label = node.nodeType === 'community' ? `C${node.id}` : String(node.id);
  const fontSize = Math.max(3, 11 / globalScale);
  context.font = `600 ${fontSize}px sans-serif`;
  context.fillStyle = 'rgba(226, 232, 240, 0.94)';
  context.fillText(label, node.x + 6 / globalScale, node.y + 3 / globalScale);
}

function drawCommunityDirectionArrows(link, context, globalScale) {
  const source = link.source;
  const target = link.target;
  if (!source || !target || typeof source !== 'object' || typeof target !== 'object') return;
  if (![source.x, source.y, target.x, target.y].every(Number.isFinite)) return;
  if (link.forwardWeight > 0) drawArrow(context, source.x, source.y, target.x, target.y, 0.72, globalScale);
  if (link.reverseWeight > 0) drawArrow(context, target.x, target.y, source.x, source.y, 0.72, globalScale);
}

function drawArrow(context, x1, y1, x2, y2, position, globalScale) {
  const x = x1 + (x2 - x1) * position;
  const y = y1 + (y2 - y1) * position;
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const size = Math.max(2.5, 5 / globalScale);
  context.save();
  context.translate(x, y);
  context.rotate(angle);
  context.beginPath();
  context.moveTo(0, 0);
  context.lineTo(-size, size * 0.58);
  context.lineTo(-size, -size * 0.58);
  context.closePath();
  context.fillStyle = 'rgba(203, 213, 225, 0.8)';
  context.fill();
  context.restore();
}

function linkEndpointId(endpoint) {
  return typeof endpoint === 'object' && endpoint !== null ? String(endpoint.id) : String(endpoint);
}

function normalizeCommunitySearch(value) {
  return String(value ?? '').trim().replace(/^c/i, '');
}

function formatTooltipNumber(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 'unavailable';
  return Number.isInteger(numeric) ? numeric.toLocaleString() : numeric.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return undefined;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener?.('change', update);
    return () => media.removeEventListener?.('change', update);
  }, []);

  return reduced;
}

function windowHeight() {
  return typeof window === 'undefined' ? 720 : window.innerHeight;
}
