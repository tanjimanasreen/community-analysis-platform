import type { NetworkView, SamplingStrategy } from '../../types/api';

interface NetworkViewToggleProps {
  view: NetworkView;
  sampling: SamplingStrategy;
  selectedCommunityId: string | null;
  onViewChange: (view: NetworkView) => void;
  onSamplingChange: (sampling: SamplingStrategy) => void;
  onClearCommunity: () => void;
}

export default function NetworkViewToggle({
  view,
  sampling,
  selectedCommunityId,
  onViewChange,
  onSamplingChange,
  onClearCommunity,
}: NetworkViewToggleProps) {
  return (
    <div className="overview-network-viewbar" aria-label="Network view controls">
      <div className="overview-network-viewbar__modes" role="group" aria-label="Network view">
        <button
          type="button"
          className={view === 'communities' ? 'is-selected' : ''}
          aria-pressed={view === 'communities'}
          onClick={() => onViewChange('communities')}
        >
          Community map
        </button>
        <button
          type="button"
          className={view === 'users' ? 'is-selected' : ''}
          aria-pressed={view === 'users'}
          onClick={() => onViewChange('users')}
        >
          User sample
        </button>
      </div>

      {view === 'users' && (
        <label className="overview-network-viewbar__sampling">
          Sampling
          <select
            value={sampling}
            onChange={(event) => onSamplingChange(event.target.value as SamplingStrategy)}
          >
            <option value="community_balanced">Community-aware</option>
            <option value="strongest_edges">Strongest interactions</option>
            <option value="full_graph">Full network graph (Pre-calculated)</option>
          </select>
        </label>
      )}

      {selectedCommunityId && (
        <div className="overview-network-viewbar__drilldown" role="status">
          Inspecting Community {selectedCommunityId}
          <button type="button" onClick={onClearCommunity}>Show all users</button>
        </div>
      )}
    </div>
  );
}
