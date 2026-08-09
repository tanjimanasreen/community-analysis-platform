import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { TransitionsResponse } from '../../types/api';
import ArtifactUnavailableState from '../states/ArtifactUnavailableState';
import ErrorState from '../states/ErrorState';
import LoadingState from '../states/LoadingState';
import { formatCount } from '../../features/overview/overviewUtils';
import {
  buildContinuityModel,
  type ContinuityLink,
  type ContinuityNode,
  type ContinuityPath,
} from '../../features/evolution/continuityModel';

interface CommunityContinuityTimelineProps {
  transitions?: TransitionsResponse | null;
  hasArtifact?: boolean;
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  onInteraction?: () => void;
  search?: string;
  maxPaths?: number;
}

type ActiveDetail =
  | { kind: 'node'; node: ContinuityNode }
  | { kind: 'link'; link: ContinuityLink }
  | null;

interface PositionedNode extends ContinuityNode {
  x: number;
  y: number;
  radius: number;
}

interface PositionedPath {
  path: ContinuityPath;
  top: number;
  height: number;
  nodes: PositionedNode[];
  nodeByKey: Map<string, PositionedNode>;
}

const SVG_WIDTH = 1040;
const HEADER_HEIGHT = 62;
const PATH_GAP = 14;
const LEFT_GUTTER = 180;
const RIGHT_GUTTER = 58;
const EMPTY_TRANSITIONS: TransitionsResponse['records'] = [];

export default function CommunityContinuityTimeline({
  transitions,
  hasArtifact = true,
  isLoading = false,
  error,
  onRetry,
  onInteraction,
  search = '',
  maxPaths = 5,
}: CommunityContinuityTimelineProps) {
  const records = transitions?.records ?? EMPTY_TRANSITIONS;
  const model = useMemo(() => buildContinuityModel(records, maxPaths), [records, maxPaths]);
  const [active, setActive] = useState<ActiveDetail>(null);
  useEffect(() => setActive(null), [transitions?.run_id, records]);
  const layout = useMemo(() => layoutTimeline(model.paths, model.months.map((month) => month.key)), [model.paths, model.months]);
  const maxRetained = Math.max(0, ...model.paths.flatMap((path) => path.links.map((link) => link.retainedCount ?? 0)));
  const svgHeight = layout.length === 0
    ? 220
    : layout[layout.length - 1].top + layout[layout.length - 1].height + 20;

  if (isLoading) return <LoadingState title="Loading community continuity" />;
  if (!hasArtifact) {
    return (
      <ArtifactUnavailableState
        artifactName="Community transitions"
        message="The selected run does not list the community transition artifact."
        action={<Link className="text-primary hover:underline" to={`/methodology${search}`}>Why this artifact is optional</Link>}
      />
    );
  }
  if (error) return <ErrorState error={error} title="Community continuity could not be loaded" onRetry={onRetry} />;

  const incomplete = Boolean(transitions && transitions.total > records.length);
  if (incomplete) {
    return (
      <section className="panel overview-continuity-panel">
        <TimelineHeading />
        <div className="overview-insight-safe-cap" role="status">
          <p className="font-semibold text-text-heading">Complete continuity summary unavailable</p>
          <p>
            The API returned {formatCount(records.length)} of {formatCount(transitions?.total ?? 0)} transition records.
            Persistent paths are not ranked from a partial graph.
          </p>
          <Link className="text-primary hover:underline" to={`/evolution${search}`}>Open Community Evolution</Link>
        </div>
      </section>
    );
  }
  if (records.length === 0) {
    return (
      <section className="panel overview-continuity-panel">
        <TimelineHeading />
        <div className="overview-insight-empty">
          <div>
            <p className="font-semibold text-text-heading">No transition records available</p>
            <p className="mt-2 text-sm text-muted">The artifact exists but contains no transitions for this run.</p>
          </div>
        </div>
      </section>
    );
  }

  const interact = () => onInteraction?.();

  return (
    <section className="panel overview-continuity-panel">
      <TimelineHeading />
      <div className="community-continuity__legend" aria-label="Community continuity legend">
        <span><i className="community-continuity__legend-width" aria-hidden="true" /> Link width: retained members</span>
        <span><i className="community-continuity__legend-jaccard" aria-hidden="true" /> Link intensity: Jaccard similarity</span>
        <span><i className="community-continuity__legend-node" aria-hidden="true" /> Node size: community members</span>
      </div>
      <div className="community-continuity__scroll" onPointerDown={interact}>
        <svg
          className="community-continuity__svg"
          viewBox={`0 0 ${SVG_WIDTH} ${svgHeight}`}
          role="group"
          aria-label={`Community continuity timeline showing ${model.displayedPaths} of ${model.totalPaths} persistent paths`}
        >
          <g aria-hidden="true">
            {model.months.map((month, index) => {
              const x = monthX(index, model.months.length);
              return (
                <g key={month.key}>
                  <text className="community-continuity__month" x={x} y={28} textAnchor="middle">{month.label}</text>
                  <line className="community-continuity__month-line" x1={x} x2={x} y1={42} y2={svgHeight - 12} />
                </g>
              );
            })}
          </g>

          {layout.map((positionedPath, pathIndex) => (
            <g key={positionedPath.path.id}>
              <rect
                className="community-continuity__row"
                x={6}
                y={positionedPath.top}
                width={SVG_WIDTH - 12}
                height={positionedPath.height}
                rx={14}
              />
              <text className="community-continuity__path-label" x={24} y={positionedPath.top + positionedPath.height / 2 - 2}>
                Path {pathIndex + 1}
              </text>
              <text className="community-continuity__path-meta" x={24} y={positionedPath.top + positionedPath.height / 2 + 16}>
                {positionedPath.path.duration} months · {positionedPath.path.retainedCountAvailable
                  ? `${formatCount(positionedPath.path.totalRetainedMembers)} retained`
                  : 'retained unavailable'}
              </text>

              {positionedPath.path.links.map((link) => {
                const source = positionedPath.nodeByKey.get(link.sourceKey);
                const target = positionedPath.nodeByKey.get(link.targetKey);
                if (!source || !target) return null;
                const strokeWidth = retainedWidth(link.retainedCount, maxRetained);
                const label = linkAccessibleLabel(link);
                return (
                  <path
                    key={link.key}
                    className="community-continuity__link"
                    d={linkPath(source, target)}
                    fill="none"
                    stroke={jaccardColor(link.jaccard)}
                    strokeWidth={strokeWidth}
                    strokeDasharray={link.retainedCount === null ? '5 5' : undefined}
                    tabIndex={0}
                    role="img"
                    aria-label={label}
                    onFocus={() => { setActive({ kind: 'link', link }); interact(); }}
                    onMouseEnter={() => setActive({ kind: 'link', link })}
                  >
                    <title>{label}</title>
                  </path>
                );
              })}

              {positionedPath.nodes.map((node) => {
                const label = nodeAccessibleLabel(node);
                return (
                  <g
                    key={node.key}
                    className="community-continuity__node"
                    tabIndex={0}
                    role="img"
                    aria-label={label}
                    onFocus={() => { setActive({ kind: 'node', node }); interact(); }}
                    onMouseEnter={() => setActive({ kind: 'node', node })}
                  >
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={node.radius}
                      className={node.memberCountInconsistent ? 'is-inconsistent' : ''}
                    />
                    <text x={node.x} y={node.y - node.radius - 8} textAnchor="middle" className="community-continuity__node-id">
                      C{node.communityId}
                    </text>
                    <text x={node.x} y={node.y + node.radius + 16} textAnchor="middle" className="community-continuity__node-members">
                      {node.memberCountInconsistent ? 'conflict' : node.memberCount === null ? 'n/a' : formatCount(node.memberCount)}
                    </text>
                    <title>{label}</title>
                  </g>
                );
              })}
            </g>
          ))}
        </svg>
      </div>

      <div className="community-continuity__details" aria-live="polite">
        {active ? <ActiveDetails active={active} /> : <p>Focus or hover a community or connection to inspect its canonical transition values.</p>}
      </div>

      <div className="community-continuity__footer">
        <span>{formatCount(model.displayedPaths)} of {formatCount(model.totalPaths)} persistent paths displayed</span>
        <Link className="text-primary hover:underline" to={`/evolution${search}`}>Open Community Evolution</Link>
      </div>

      <ul className="sr-only">
        {model.paths.map((path, index) => (
          <li key={path.id}>Path {index + 1}: {path.nodes.map(nodeAccessibleLabel).join('; ')}</li>
        ))}
      </ul>
    </section>
  );
}

function TimelineHeading() {
  return (
    <div>
      <h3 className="text-sm font-bold text-text-heading">Community Continuity Timeline</h3>
      <p className="mt-1 text-xs text-muted">
        Persistent paths are grouped from canonical transition records. Width shows retained members; intensity shows Jaccard similarity. Each community is denoted as C0(month)_(community_id).
      </p>
    </div>
  );
}

function ActiveDetails({ active }: { active: Exclude<ActiveDetail, null> }) {
  if (active.kind === 'node') {
    const { node } = active;
    return (
      <div>
        <strong>{node.monthLabel} · C{node.communityId}</strong>
        <span>
          {node.memberCountInconsistent
            ? `Conflicting published member totals: ${node.memberCountValues.join(', ')}`
            : `Members: ${node.memberCount === null ? 'unavailable' : formatCount(node.memberCount)}`}
        </span>
      </div>
    );
  }
  const { link } = active;
  return (
    <div>
      <strong>{link.startMonthLabel} C{link.startCommunityId} → {link.endMonthLabel} C{link.endCommunityId}</strong>
      <span>
        Retained: {link.retainedCount === null ? 'unavailable' : formatCount(link.retainedCount)} · Start: {displayCount(link.startMemberCount)} · End: {displayCount(link.endMemberCount)} · Jaccard: {link.jaccard.toFixed(3)}
      </span>
    </div>
  );
}

function layoutTimeline(paths: ContinuityPath[], monthKeys: string[]): PositionedPath[] {
  const maxMembers = Math.max(0, ...paths.flatMap((path) => path.nodes.map((node) => node.memberCount ?? 0)));
  let top = HEADER_HEIGHT;
  return paths.map((path) => {
    const groups = new Map<string, ContinuityNode[]>();
    for (const node of path.nodes) {
      const nodes = groups.get(node.monthKey) ?? [];
      nodes.push(node);
      groups.set(node.monthKey, nodes);
    }
    const maximumParallelNodes = Math.max(1, ...[...groups.values()].map((nodes) => nodes.length));
    const height = Math.max(96, 72 + (maximumParallelNodes - 1) * 50);
    const centerY = top + height / 2 + 5;
    const positionedNodes: PositionedNode[] = [];
    const nodeByKey = new Map<string, PositionedNode>();

    for (const [monthKey, nodes] of groups) {
      const monthIndex = Math.max(0, monthKeys.indexOf(monthKey));
      nodes.sort((left, right) => left.communityId.localeCompare(right.communityId, undefined, { numeric: true }));
      nodes.forEach((node, index) => {
        const offset = (index - (nodes.length - 1) / 2) * 48;
        const positioned = {
          ...node,
          x: monthX(monthIndex, monthKeys.length),
          y: centerY + offset,
          radius: memberRadius(node.memberCount, maxMembers),
        };
        positionedNodes.push(positioned);
        nodeByKey.set(node.key, positioned);
      });
    }

    const positionedPath = { path, top, height, nodes: positionedNodes, nodeByKey };
    top += height + PATH_GAP;
    return positionedPath;
  });
}

function monthX(index: number, count: number): number {
  if (count <= 1) return (LEFT_GUTTER + SVG_WIDTH - RIGHT_GUTTER) / 2;
  const width = SVG_WIDTH - LEFT_GUTTER - RIGHT_GUTTER;
  return LEFT_GUTTER + (index * width) / (count - 1);
}

function memberRadius(memberCount: number | null, maximum: number): number {
  if (memberCount === null || memberCount <= 0 || maximum <= 0) return 14;
  return 12 + 14 * Math.sqrt(memberCount / maximum);
}

function retainedWidth(retainedCount: number | null, maximum: number): number {
  if (retainedCount === null || retainedCount <= 0 || maximum <= 0) return 2.5;
  return 2.5 + 12 * Math.sqrt(retainedCount / maximum);
}

function linkPath(source: PositionedNode, target: PositionedNode): string {
  const startX = source.x + source.radius;
  const endX = target.x - target.radius;
  const bend = Math.max(30, (endX - startX) * 0.45);
  return `M ${startX} ${source.y} C ${startX + bend} ${source.y}, ${endX - bend} ${target.y}, ${endX} ${target.y}`;
}

function jaccardColor(jaccard: number): string {
  const normalized = Math.max(0, Math.min(1, jaccard));
  return `rgba(59, 130, 246, ${(0.22 + normalized * 0.76).toFixed(3)})`;
}

function nodeAccessibleLabel(node: ContinuityNode): string {
  const members = node.memberCountInconsistent
    ? `conflicting member totals ${node.memberCountValues.join(', ')}`
    : node.memberCount === null ? 'member total unavailable' : `${node.memberCount} members`;
  return `${node.monthLabel}, community ${node.communityId}, ${members}`;
}

function linkAccessibleLabel(link: ContinuityLink): string {
  return `${link.startMonthLabel} community ${link.startCommunityId} to ${link.endMonthLabel} community ${link.endCommunityId}. Retained members ${link.retainedCount ?? 'unavailable'}. Start members ${link.startMemberCount ?? 'unavailable'}. End members ${link.endMemberCount ?? 'unavailable'}. Jaccard ${link.jaccard.toFixed(3)}.`;
}

function displayCount(value: number | null): string {
  return value === null ? 'unavailable' : formatCount(value);
}
