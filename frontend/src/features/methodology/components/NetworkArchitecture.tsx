import { useId, useState, type KeyboardEvent, type ReactNode } from 'react';
import { ArrowDown, ArrowRight, MessageSquare, RadioTower, Repeat2, UserRound, UsersRound, type LucideIcon } from 'lucide-react';
import { NETWORK_MODELS } from '../methodologyContent';

type NetworkModelId = (typeof NETWORK_MODELS)[number]['id'];

export default function NetworkArchitecture() {
  const [activeModel, setActiveModel] = useState<NetworkModelId>('telegram');
  const tabsId = useId();
  const model = NETWORK_MODELS.find((item) => item.id === activeModel) ?? NETWORK_MODELS[0];

  const handleTabKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const lastIndex = NETWORK_MODELS.length - 1;
    const nextIndex = event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? lastIndex
        : event.key === 'ArrowRight'
          ? (index + 1) % NETWORK_MODELS.length
          : (index - 1 + NETWORK_MODELS.length) % NETWORK_MODELS.length;
    const next = NETWORK_MODELS[nextIndex];
    setActiveModel(next.id);
    window.requestAnimationFrame(() => document.getElementById(`${tabsId}-${next.id}-tab`)?.focus());
  };

  return (
    <div className="panel p-5 sm:p-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Platform interaction models</p>
        <h2 className="mt-1 text-lg font-bold text-text-heading">Network Architecture</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">Platform-specific relationships are modeled explicitly, then projected into the same monthly user-to-user analytical network.</p>
      </div>

      <div className="mt-5 overflow-x-auto pb-1">
        <div role="tablist" aria-label="Network architecture platform" className="inline-flex min-w-max rounded-xl border border-border bg-surface-soft/45 p-1">
          {NETWORK_MODELS.map((item, index) => {
            const selected = item.id === activeModel;
            return (
              <button
                key={item.id}
                id={`${tabsId}-${item.id}-tab`}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls={`${tabsId}-network-panel`}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActiveModel(item.id)}
                onKeyDown={(event: KeyboardEvent<HTMLButtonElement>) => handleTabKeyDown(event, index)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${selected ? 'bg-primary/10 text-primary' : 'text-muted hover:bg-bg/40 hover:text-text-heading'}`}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      <div
        id={`${tabsId}-network-panel`}
        role="tabpanel"
        aria-labelledby={`${tabsId}-${activeModel}-tab`}
        className="mt-4 rounded-2xl border border-border/70 bg-surface-soft/30 p-4 sm:p-5"
      >
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="text-sm font-bold text-text-heading">{model.label}</h3>
          <span className="text-xs font-semibold text-primary">Platform-specific graph</span>
        </div>
        <p className="mt-1 max-w-3xl text-xs leading-5 text-muted">{model.description}</p>

        <div className="mt-5">
          {activeModel === 'telegram' && <TelegramModel />}
          {activeModel === 'retweet_quote' && <RetweetQuoteModel />}
          {activeModel === 'reply' && <ReplyModel />}
        </div>

        <div className="my-5 flex items-center gap-3" aria-hidden="true">
          <span className="h-px flex-1 bg-border" />
          <ArrowDown className="text-primary" size={18} />
          <span className="h-px flex-1 bg-border" />
        </div>

        <CommonProjection />
      </div>
    </div>
  );
}

function TelegramModel() {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <RelationshipLane title="Original message">
        <Node icon={UserRound} label="User" />
        <Relation label="CREATED" />
        <Node icon={MessageSquare} label="Message" />
        <Relation label="SENT_TO" />
        <Node icon={RadioTower} label="Channel" />
      </RelationshipLane>
      <RelationshipLane title="Forwarded message">
        <Node icon={UserRound} label="Source" />
        <Relation label="PRODUCED / ORIGINATED" />
        <Node icon={Repeat2} label="Forwarded message" />
        <Relation label="FORWARDED_TO" />
        <Node icon={RadioTower} label="Destination" />
        <div className="col-span-full mt-2 rounded-lg border border-border/60 bg-bg/25 px-3 py-2 text-center text-[11px] text-muted">
          A forwarding user connects to the forwarded-message node through <strong className="text-text-heading">FORWARDED_BY</strong>.
        </div>
      </RelationshipLane>
    </div>
  );
}

function RetweetQuoteModel() {
  return (
    <RelationshipLane title="Amplification interaction">
      <Node icon={UserRound} label="Creator" />
      <Relation label="TWEETED" />
      <Node icon={Repeat2} label="Retweet / Quote" />
      <Relation label="RETWEETED_BY" />
      <Node icon={UserRound} label="Spreader" />
    </RelationshipLane>
  );
}

function ReplyModel() {
  return (
    <RelationshipLane title="Conversation interaction">
      <Node icon={UserRound} label="Target user" />
      <Relation label="REPLIED_TO" reverse />
      <Node icon={MessageSquare} label="Reply" />
      <Relation label="REPLIED_BY" />
      <Node icon={UserRound} label="Reply author" />
    </RelationshipLane>
  );
}

function RelationshipLane({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-border/60 bg-bg/20 p-3">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">{title}</p>
      <div className="grid grid-cols-1 items-center gap-2 sm:grid-cols-[minmax(72px,1fr)_auto_minmax(90px,1fr)_auto_minmax(72px,1fr)]">{children}</div>
    </div>
  );
}

function Node({ icon: Icon, label }: { icon: LucideIcon; label: string }) {
  return (
    <div className="flex min-h-20 flex-col items-center justify-center rounded-xl border border-primary/20 bg-primary/5 p-2 text-center">
      <Icon size={18} className="text-primary" aria-hidden="true" />
      <span className="mt-2 text-[11px] font-semibold leading-4 text-text-heading">{label}</span>
    </div>
  );
}

function Relation({ label, reverse = false }: { label: string; reverse?: boolean }) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-1 py-1 text-center sm:min-w-16 sm:py-0">
      <span className="max-w-28 break-words text-[9px] font-semibold leading-3 text-muted">{label}</span>
      <ArrowDown className="text-border sm:hidden" size={18} aria-hidden="true" />
      <ArrowRight className={`hidden text-border sm:block ${reverse ? 'rotate-180' : ''}`} size={18} aria-hidden="true" />
    </div>
  );
}

function CommonProjection() {
  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-primary">Common analytical projection</p>
          <p className="mt-1 text-xs text-muted">The platform relationships resolve to a monthly directed user interaction edge.</p>
        </div>
        <div className="flex items-center gap-2 self-start rounded-lg border border-border/70 bg-surface px-3 py-2 text-xs font-semibold text-text-heading">
          <UsersRound size={16} className="text-primary" aria-hidden="true" />
          Creator
          <ArrowRight size={16} className="text-primary" aria-hidden="true" />
          Spreader
        </div>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg border border-border/60 bg-bg/25 px-3 py-2 text-xs"><strong className="text-text-heading">IF</strong><span className="ml-2 text-muted">interaction volume · shared_post</span></div>
        <div className="rounded-lg border border-border/60 bg-bg/25 px-3 py-2 text-xs"><strong className="text-text-heading">WIF</strong><span className="ml-2 text-muted">interaction share · shared_post / total_post</span></div>
      </div>
    </div>
  );
}
