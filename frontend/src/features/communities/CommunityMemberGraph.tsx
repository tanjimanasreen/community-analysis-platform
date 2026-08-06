import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import type { NetworkResponse } from '../../types/api';
import { transformNetworkResponse } from '../networks/networkModel';
import { formatCount } from '../overview/overviewUtils';

const ForceGraph2D = lazy(() => import('react-force-graph-2d'));

interface CommunityMemberGraphProps {
  graph: NetworkResponse;
}

export default function CommunityMemberGraph({ graph }: CommunityMemberGraphProps) {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<any>(null);
  const [width, setWidth] = useState(320);
  const data = useMemo(() => transformNetworkResponse(graph, graph.community_id), [graph]);

  useEffect(() => {
    const target = stageRef.current;
    if (!target) return undefined;
    const update = (nextWidth: number) => setWidth(Math.max(240, Math.floor(nextWidth)));
    update(target.clientWidth || 320);
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(([entry]) => update(entry.contentRect.width));
    observer.observe(target);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => graphRef.current?.zoomToFit?.(250, 24), 120);
    return () => window.clearTimeout(timer);
  }, [data.nodes.length, data.links.length, width]);

  return (
    <section aria-label="Selected community member network">
      <p className="text-xs text-muted">
        {formatCount(graph.returned_nodes)} / {formatCount(graph.available_nodes)} users ·{' '}
        {formatCount(graph.returned_edges)} / {formatCount(graph.available_edges)} internal edges
      </p>
      <div ref={stageRef} className="community-member-graph" data-testid="community-member-graph">
        {data.nodes.length === 0 ? (
          <div className="community-member-graph__empty">No member graph nodes are available.</div>
        ) : (
          <Suspense fallback={<div className="community-member-graph__empty">Preparing member graph…</div>}>
            <ForceGraph2D
              ref={graphRef}
              width={width}
              height={280}
              graphData={data}
              nodeColor={(node: any) => node.color}
              nodeVal={(node: any) => node.val}
              nodeRelSize={4}
              nodeLabel={(node: any) => [
                `User ${node.id}`,
                `In-degree: ${node.inDegree}`,
                `Out-degree: ${node.outDegree}`,
              ].join('\n')}
              linkColor={(link: any) => `rgba(148, 163, 184, ${link.opacity})`}
              linkWidth={(link: any) => link.width}
              linkDirectionalArrowLength={2.5}
              linkDirectionalArrowRelPos={0.8}
              linkLabel={(link: any) => `Weight: ${link.weight}`}
              backgroundColor="rgba(0,0,0,0)"
              d3AlphaDecay={0.04}
              d3VelocityDecay={0.4}
              cooldownTicks={100}
              onEngineStop={() => graphRef.current?.zoomToFit?.(250, 24)}
            />
          </Suspense>
        )}
      </div>
      {graph.sampled && (
        <p className="mt-2 text-[11px] text-muted">This is the existing deterministic bounded community preview; the dedicated Network page exposes the same coverage metadata.</p>
      )}
    </section>
  );
}
