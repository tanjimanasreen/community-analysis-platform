import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import type { MetricName, NetworkResponse } from '../../types/api';
import { formatCount } from '../../features/overview/overviewUtils';
import {
  buildCommunityLandscapeModel,
  type CommunityLandscapeItem,
} from '../../features/networks/communityLandscapeModel';

interface CommunityLandscapeProps {
  network: NetworkResponse;
  metric: MetricName;
  onSelectCommunity?: (communityId: string) => void;
  onInteraction?: () => void;
}

interface LandscapeStyle extends CSSProperties {
  '--community-diameter': string;
  '--community-fill': string;
  '--community-border-width': string;
}

export default function CommunityLandscape({
  network,
  metric,
  onSelectCommunity,
  onInteraction,
}: CommunityLandscapeProps) {
  const model = useMemo(() => buildCommunityLandscapeModel(network), [network]);
  const [activeId, setActiveId] = useState<string | null>(model.items[0]?.id ?? null);
  const activeItem = model.items.find((item) => item.id === activeId) ?? model.items[0] ?? null;

  useEffect(() => {
    if (!model.items.some((item) => item.id === activeId)) {
      setActiveId(model.items[0]?.id ?? null);
    }
  }, [activeId, model.items]);

  const activate = (item: CommunityLandscapeItem) => {
    setActiveId(item.id);
    onInteraction?.();
  };

  return (
    <div className="community-landscape" data-testid="community-landscape">
      <div className="community-landscape__grid" role="list" aria-label="Published prominent communities">
        {model.items.map((item) => {
          const style: LandscapeStyle = {
            '--community-diameter': `${item.diameter.toFixed(1)}px`,
            '--community-fill': communityFill(metric, item.weightIntensity),
            '--community-border-width': `${item.borderWidth.toFixed(1)}px`,
          };
          const details = communityDetails(item, metric);
          return (
            <div className="community-landscape__item" role="listitem" key={item.id}>
              <button
                type="button"
                className={`community-landscape__bubble ${activeItem?.id === item.id ? 'is-active' : ''}`}
                style={style}
                aria-label={`${item.label}. ${details}. Open its user subgraph.`}
                title={`${item.label}\n${details}\nClick to inspect the user subgraph.`}
                onFocus={() => activate(item)}
                onMouseEnter={() => setActiveId(item.id)}
                onPointerDown={onInteraction}
                onClick={() => {
                  activate(item);
                  onSelectCommunity?.(item.id);
                }}
              >
                <strong>{item.label}</strong>
                <span>{item.memberCount === null ? 'Members unavailable' : `${formatCount(item.memberCount)} members`}</span>
              </button>
            </div>
          );
        })}
      </div>

      <div className="community-landscape__legend" aria-label="Community Landscape legend">
        <span><i className="community-landscape__legend-size" aria-hidden="true" /> Relative area: members</span>
        <span><i className="community-landscape__legend-fill" aria-hidden="true" /> Fill intensity: total {metric.toUpperCase()} weight</span>
        <span><i className="community-landscape__legend-border" aria-hidden="true" /> Border width: internal edges</span>
      </div>

      {activeItem && (
        <div className="community-landscape__details" aria-live="polite">
          <div>
            <span>Selected community</span>
            <strong>{activeItem.label}</strong>
          </div>
          <div>
            <span>Members</span>
            <strong>{displayValue(activeItem.memberCount)}</strong>
          </div>
          <div>
            <span>Internal edges</span>
            <strong>{displayValue(activeItem.internalEdgeCount)}</strong>
          </div>
          <div>
            <span>Total {metric.toUpperCase()} weight</span>
            <strong>{displayValue(activeItem.internalWeight)}</strong>
          </div>
          <p>Activate the community to open its bounded month- and metric-local user subgraph.</p>
        </div>
      )}
    </div>
  );
}

function communityFill(metric: MetricName, intensity: number): string {
  const alpha = 0.18 + intensity * 0.68;
  return metric === 'if'
    ? `rgba(59, 130, 246, ${alpha.toFixed(3)})`
    : `rgba(139, 92, 246, ${alpha.toFixed(3)})`;
}

function communityDetails(item: CommunityLandscapeItem, metric: MetricName): string {
  return [
    `Members: ${displayValue(item.memberCount)}`,
    `Internal edges: ${displayValue(item.internalEdgeCount)}`,
    `Total ${metric.toUpperCase()} weight: ${displayValue(item.internalWeight)}`,
  ].join('. ');
}

function displayValue(value: number | null): string {
  return value === null ? 'Unavailable' : formatCount(value);
}
