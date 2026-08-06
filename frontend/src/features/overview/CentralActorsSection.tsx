import { ArrowDownToLine, ArrowUpFromLine, LocateFixed } from 'lucide-react';
import ErrorState from '../../components/states/ErrorState';
import LoadingState from '../../components/states/LoadingState';
import type {
  CentralityActor,
  CentralityLeadersResponse,
  MetricName,
  NetworkResponse,
} from '../../types/api';
import { formatPeriod } from './overviewUtils';

interface CentralActorsSectionProps {
  leaders: CentralityLeadersResponse | undefined;
  selectedPeriod: string;
  metric: MetricName;
  network: NetworkResponse | undefined;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  onSelectPeriod: (period: string) => void;
  onInspectCommunity: (communityId: string) => void;
  onHighlightUser: (userId: string) => void;
}

export default function CentralActorsSection({
  leaders,
  selectedPeriod,
  metric,
  network,
  isLoading,
  error,
  onRetry,
  onSelectPeriod,
  onInspectCommunity,
  onHighlightUser,
}: CentralActorsSectionProps) {
  if (isLoading) return <LoadingState title="Loading central actors" />;
  if (error) {
    return <ErrorState error={error} title="Central actors could not be loaded" onRetry={onRetry} />;
  }
  if (!leaders || leaders.periods.length === 0) {
    return (
      <section className="panel overview-central-actors">
        <h2>Central actors over time</h2>
        <p className="text-sm text-muted">No monthly user-centrality artifact is available for this run.</p>
      </section>
    );
  }

  const selected = leaders.periods.find((item) => item.period === selectedPeriod)
    ?? leaders.periods.at(-1);
  const displayedUsers = new Set(
    network?.view === 'users' ? network.nodes.map((node) => String(node.id)) : [],
  );

  return (
    <section className="panel overview-central-actors">
      <div className="overview-section-heading">
        <div>
          <p className="overview-eyebrow">Directed centrality</p>
          <h2>Central actors over time</h2>
          <p>
            Top spreaders use in-degree centrality; top influencers use out-degree centrality.
            Community assignments are local to the selected month and metric partition.
          </p>
        </div>
      </div>

      <div className="overview-central-actors__cards">
        <ActorCard
          title="Top spreader"
          subtitle="Connected to content from the largest number of distinct authors."
          actor={selected?.spreader ?? null}
          period={selected?.period ?? selectedPeriod}
          metric={metric}
          icon={ArrowDownToLine}
          scoreLabel="In-degree centrality"
          inPreview={selected?.spreader ? displayedUsers.has(selected.spreader.user_id) : false}
          canHighlight={network?.view === 'users'}
          onInspectCommunity={onInspectCommunity}
          onHighlightUser={onHighlightUser}
        />
        <ActorCard
          title="Top influencer"
          subtitle="Authored content that reached the largest number of distinct spreaders."
          actor={selected?.influencer ?? null}
          period={selected?.period ?? selectedPeriod}
          metric={metric}
          icon={ArrowUpFromLine}
          scoreLabel="Out-degree centrality"
          inPreview={selected?.influencer ? displayedUsers.has(selected.influencer.user_id) : false}
          canHighlight={network?.view === 'users'}
          onInspectCommunity={onInspectCommunity}
          onHighlightUser={onHighlightUser}
        />
      </div>

      <div className="overview-central-actors__timeline-grid">
        <ActorTimeline
          title="Top spreader by month"
          periods={leaders.periods}
          role="spreader"
          selectedPeriod={selectedPeriod}
          onSelectPeriod={onSelectPeriod}
        />
        <ActorTimeline
          title="Top influencer by month"
          periods={leaders.periods}
          role="influencer"
          selectedPeriod={selectedPeriod}
          onSelectPeriod={onSelectPeriod}
        />
      </div>

      <p className="overview-central-actors__note">
        The API reads the existing monthly centrality output and does not recompute NetworkX metrics.
      </p>
    </section>
  );
}

function ActorCard({
  title,
  subtitle,
  actor,
  period,
  metric,
  icon: Icon,
  scoreLabel,
  inPreview,
  canHighlight,
  onInspectCommunity,
  onHighlightUser,
}: {
  title: string;
  subtitle: string;
  actor: CentralityActor | null;
  period: string;
  metric: MetricName;
  icon: typeof ArrowDownToLine;
  scoreLabel: string;
  inPreview: boolean;
  canHighlight: boolean;
  onInspectCommunity: (communityId: string) => void;
  onHighlightUser: (userId: string) => void;
}) {
  return (
    <article className="overview-central-actor-card">
      <div className="overview-central-actor-card__heading">
        <span><Icon size={17} /></span>
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
      </div>
      {actor ? (
        <>
          <strong
            className="overview-central-actor-card__user"
            title="Masked analytical user identifier"
          >
            {actor.display_user_id}
          </strong>
          <div className="overview-central-actor-card__facts">
            <span>{formatPeriod(period)} · {metric.toUpperCase()} · Monthly rank #1</span>
            <span>{scoreLabel}: {formatCentrality(actor.centrality)}</span>
          </div>
          <div className="overview-central-actor-card__actions">
            {actor.community_id ? (
              <button type="button" onClick={() => onInspectCommunity(actor.community_id!)}>
                Community {actor.community_id}
              </button>
            ) : (
              <span>Community unavailable</span>
            )}
            {canHighlight && inPreview ? (
              <button type="button" onClick={() => onHighlightUser(actor.user_id)}>
                <LocateFixed size={14} /> Highlight in graph
              </button>
            ) : canHighlight ? (
              <span>Not included in current graph preview</span>
            ) : (
              <span>Select the actor's community to inspect its member network.</span>
            )}
          </div>
        </>
      ) : (
        <p className="overview-unavailable">Unavailable for this month</p>
      )}
    </article>
  );
}

function ActorTimeline({
  title,
  periods,
  role,
  selectedPeriod,
  onSelectPeriod,
}: {
  title: string;
  periods: CentralityLeadersResponse['periods'];
  role: 'spreader' | 'influencer';
  selectedPeriod: string;
  onSelectPeriod: (period: string) => void;
}) {
  return (
    <div className="overview-central-actors__timeline">
      <h3>{title}</h3>
      <div className="overview-central-actors__timeline-list">
        {periods.map((period) => {
          const actor = period[role];
          return (
            <button
              type="button"
              key={period.period}
              className={period.period === selectedPeriod ? 'is-selected' : ''}
              onClick={() => onSelectPeriod(period.period)}
            >
              <span>{formatPeriod(period.period)}</span>
              <strong>{actor?.display_user_id ?? 'Unavailable'}</strong>
              <small>
                {actor ? `${formatCentrality(actor.centrality)} · ${actor.community_id ? `Community ${actor.community_id}` : 'Community unavailable'}` : 'No value'}
              </small>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function formatCentrality(value: number): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 6,
  }).format(value);
}
