import type { KeyboardEvent } from 'react';
import type { ClusteredThemeTimelineResponse } from '../../types/api';
import { stableThemeColor } from './themeModel';
import { CompactThemeLabel } from './CompactThemeText';
import {
  buildAggregateThemeProgression,
  periodLabel,
  type MonthlyTopThemePoint,
  type ThemeProgressionStatus,
} from './themeTrendModel';

interface Props {
  response?: ClusteredThemeTimelineResponse | null;
  selectedPeriod?: string | null;
  selectedThemeId?: string | null;
  onSelectTheme: (period: string, themeId: string, name: string) => void;
  limit?: number;
}

const STATUS_LABELS: Record<ThemeProgressionStatus, string> = {
  new: 'New to monthly ranking',
  continued: 'Continued',
  exited: 'Exits monthly ranking after month',
  're-entered': 'Re-entered',
};

const MIN_CHART_WIDTH = 760;
const MONTH_COLUMN_WIDTH = 260;
const RANK_GUTTER_WIDTH = 90;
const RIGHT_PADDING = 24;
const CHART_TOP = 96;
const ROW_GAP = 86;
const BOTTOM_PADDING = 70;
const LABEL_CHARS_PER_LINE = 24;

export default function AggregateThemeProgression({
  response,
  selectedPeriod = null,
  selectedThemeId = null,
  onSelectTheme,
  limit = 5,
}: Props) {
  if (!response) return null;
  if (!response.complete) {
    return (
      <section className="panel p-5">
        <p role="status" className="text-sm text-muted">
          The selected timeline is incomplete, so aggregate progression is not shown.
        </p>
      </section>
    );
  }

  const progression = buildAggregateThemeProgression(response, limit);
  if (progression.rows.length === 0) {
    return (
      <section className="panel p-5">
        <h2 className="text-lg font-bold text-text-heading">Aggregate Theme Progression</h2>
        <p className="mt-4 text-sm text-muted">No ranked canonical themes are available in this timeline.</p>
      </section>
    );
  }

  const rankCount = Math.max(1, limit);
  const naturalWidth = RANK_GUTTER_WIDTH + progression.periods.length * MONTH_COLUMN_WIDTH + RIGHT_PADDING;
  const width = Math.max(MIN_CHART_WIDTH, naturalWidth);
  const extraWidth = Math.max(0, width - naturalWidth);
  const plotLeft = RANK_GUTTER_WIDTH + extraWidth / 2;
  const plotRight = plotLeft + progression.periods.length * MONTH_COLUMN_WIDTH;
  const height = CHART_TOP + (rankCount - 1) * ROW_GAP + BOTTOM_PADDING;
  const periodIndex = new Map(progression.periods.map((period, index) => [period, index]));
  const monthX = (index: number) => plotLeft + (index + 0.5) * MONTH_COLUMN_WIDTH;
  const pointPosition = (point: MonthlyTopThemePoint) => ({
    x: monthX(periodIndex.get(point.period) ?? 0),
    y: CHART_TOP + (point.rank - 1) * ROW_GAP,
  });

  return (
    <section className="panel min-w-0 p-5" aria-labelledby="aggregate-theme-progression-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="aggregate-theme-progression-heading" className="text-lg font-bold text-text-heading">
            Aggregate Theme Progression
          </h2>
          <p className="mt-1 max-w-4xl text-xs text-muted">
            Rank movement across all matched communities. Lines connect the same upstream canonical theme identity across adjacent months; they do not represent community persistence.
          </p>
        </div>
        <span className="rounded-full border border-border bg-bg/30 px-3 py-1 text-xs font-semibold text-muted">
          Up to {limit} themes per month
        </span>
      </div>

      <div className="mt-5 flex flex-wrap gap-3 text-xs text-muted" aria-label="Theme progression legend">
        <LegendMark label="New to monthly ranking" shape="filled" />
        <LegendMark label="Continued" shape="line" />
        <LegendMark label="Re-entered after a gap" shape="ring" />
        <LegendMark label="Exits monthly ranking" shape="dashed" />
      </div>

      <div className="mt-4 max-w-full overflow-x-auto pb-2" data-testid="aggregate-theme-progression-scroll">
        <svg
          role="img"
          aria-labelledby="aggregate-theme-chart-title aggregate-theme-chart-description"
          viewBox={`0 0 ${width} ${height}`}
          className="h-auto shrink-0"
          style={{ width: `${width}px`, maxWidth: 'none' }}
          data-testid="aggregate-theme-progression-chart"
        >
          <title id="aggregate-theme-chart-title">Monthly canonical-theme rank progression</title>
          <desc id="aggregate-theme-chart-description">
            Themes are positioned by monthly rank from one through {limit}. Only the same upstream canonical theme identity in adjacent months is connected. A month may contain fewer than {limit} ranked themes. The table below contains the same values and selection controls.
          </desc>

          {Array.from({ length: rankCount }, (_, index) => index + 1).map((rank) => {
            const y = CHART_TOP + (rank - 1) * ROW_GAP;
            return (
              <g key={rank}>
                <line x1={plotLeft} y1={y} x2={plotRight} y2={y} stroke="currentColor" opacity="0.12" />
                <text x={plotLeft - 16} y={y + 4} textAnchor="end" fill="currentColor" opacity="0.7" fontSize="12">Rank {rank}</text>
              </g>
            );
          })}

          {progression.periods.map((period, index) => {
            const x = monthX(index);
            return (
              <g key={period}>
                <line
                  x1={x}
                  y1={CHART_TOP - 28}
                  x2={x}
                  y2={CHART_TOP + ROW_GAP * (rankCount - 1) + 30}
                  stroke="currentColor"
                  opacity="0.08"
                />
                <text x={x} y={28} textAnchor="middle" fill="currentColor" opacity="0.75" fontSize="13" fontWeight="600">
                  {periodLabel(period)}
                </text>
              </g>
            );
          })}

          {progression.series.flatMap((series) => series.segments.map((segment, segmentIndex) => {
            if (segment.length < 2) return null;
            const points = segment.map((point) => {
              const position = pointPosition(point);
              return `${position.x},${position.y}`;
            }).join(' ');
            return (
              <polyline
                key={`${series.themeId}:${segmentIndex}`}
                points={points}
                fill="none"
                stroke={stableThemeColor(series.themeId)}
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                opacity="0.75"
              />
            );
          }))}

          {progression.rows.map((point) => {
            const { x, y } = pointPosition(point);
            const selected = selectedPeriod === point.period && selectedThemeId === point.themeId;
            const reEntered = point.statuses.includes('re-entered');
            const exits = point.statuses.includes('exited');
            const labelLines = wrapSvgLabel(point.name, LABEL_CHARS_PER_LINE);
            const firstLabelY = labelLines.length > 1 ? y - 30 : y - 17;
            const handleKeyDown = (event: KeyboardEvent<SVGGElement>) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelectTheme(point.period, point.themeId, point.name);
              }
            };
            return (
              <g
                key={`${point.period}:${point.themeId}`}
                role="button"
                tabIndex={0}
                aria-label={`${point.name}, ${periodLabel(point.period)}, rank ${point.rank}, ${point.communityCount} matched communities`}
                onClick={() => onSelectTheme(point.period, point.themeId, point.name)}
                onKeyDown={handleKeyDown}
                className="cursor-pointer"
                data-theme-id={point.themeId}
                data-period={point.period}
              >
                <title>{`${point.name} · ${periodLabel(point.period)} · Rank ${point.rank} · ${point.communityCount} matched communities · ${point.percentage.toFixed(1)}%`}</title>
                {exits && (
                  <circle cx={x} cy={y} r={selected ? 14 : 12} fill="none" stroke={stableThemeColor(point.themeId)} strokeWidth="2" strokeDasharray="3 3" opacity="0.8" />
                )}
                <circle
                  cx={x}
                  cy={y}
                  r={selected ? 9 : 7}
                  fill={reEntered ? 'transparent' : stableThemeColor(point.themeId)}
                  stroke={stableThemeColor(point.themeId)}
                  strokeWidth={reEntered || selected ? 3 : 1.5}
                />
                <text
                  x={x}
                  y={firstLabelY}
                  textAnchor="middle"
                  fill="currentColor"
                  fontSize="11"
                  fontWeight={selected ? '700' : '600'}
                  aria-hidden="true"
                >
                  {labelLines.map((line, index) => (
                    <tspan key={`${line}:${index}`} x={x} dy={index === 0 ? 0 : 12}>{line}</tspan>
                  ))}
                </text>
                <text x={x} y={y + 26} textAnchor="middle" fill="currentColor" opacity="0.65" fontSize="10" aria-hidden="true">
                  {point.communityCount} communities · {point.percentage.toFixed(1)}%
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[880px] text-left text-xs">
          <caption className="sr-only">Accessible values for aggregate theme progression</caption>
          <thead>
            <tr className="border-b border-border text-muted">
              <th className="p-2">Theme</th>
              <th className="p-2">Month</th>
              <th className="p-2">Rank</th>
              <th className="p-2">Matched communities</th>
              <th className="p-2">Percentage</th>
              <th className="p-2">Status</th>
              <th className="p-2">Prominent LDA keywords</th>
            </tr>
          </thead>
          <tbody>
            {progression.rows.map((point) => {
              const selected = selectedPeriod === point.period && selectedThemeId === point.themeId;
              return (
                <tr key={`${point.period}:${point.themeId}`} className={`border-b border-border/50 align-top ${selected ? 'bg-primary/5' : ''}`}>
                  <td className="p-2">
                    <button
                      type="button"
                      aria-pressed={selected}
                      onClick={() => onSelectTheme(point.period, point.themeId, point.name)}
                      className="max-w-xs text-left font-semibold text-primary hover:underline"
                    >
                      <CompactThemeLabel text={point.name} />
                    </button>
                  </td>
                  <td className="p-2 text-text-heading">{periodLabel(point.period)}</td>
                  <td className="p-2 text-text-heading">{point.rank}</td>
                  <td className="p-2 text-text-heading">{point.communityCount}</td>
                  <td className="p-2 text-text-heading">{point.percentage.toFixed(1)}%</td>
                  <td className="p-2 text-muted">{point.statuses.map((status) => STATUS_LABELS[status]).join(' · ')}</td>
                  <td className="max-w-sm p-2 text-muted"><span className="line-clamp-3 break-all" title={point.keywords.slice(0, 5).join(', ')}>{point.keywords.slice(0, 5).join(', ') || 'Unavailable'}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-muted">
        A gap in the monthly ranking breaks a line. If the same canonical theme returns later, it starts a new segment marked as re-entered. Semantic grouping is computed upstream from general theme labels, not in the browser.
      </p>
    </section>
  );
}

function LegendMark({ label, shape }: { label: string; shape: 'filled' | 'line' | 'ring' | 'dashed' }) {
  return (
    <span className="inline-flex items-center gap-2">
      {shape === 'line' ? (
        <span className="h-0.5 w-5 bg-primary" aria-hidden="true" />
      ) : (
        <span
          className={`h-3 w-3 rounded-full ${shape === 'filled' ? 'bg-primary' : ''} ${shape === 'ring' ? 'border-2 border-primary' : ''} ${shape === 'dashed' ? 'border-2 border-dashed border-primary' : ''}`}
          aria-hidden="true"
        />
      )}
      {label}
    </span>
  );
}

function wrapSvgLabel(value: string, maxCharsPerLine: number): string[] {
  const normalized = value.trim().replace(/\s+/g, ' ');
  if (normalized.length <= maxCharsPerLine) return [normalized];

  const words = normalized.split(' ');
  const lines: string[] = [];
  let current = '';
  let wordIndex = 0;

  while (wordIndex < words.length && lines.length < 2) {
    const word = words[wordIndex];
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxCharsPerLine) {
      current = candidate;
      wordIndex += 1;
      continue;
    }

    if (!current) {
      current = `${word.slice(0, Math.max(1, maxCharsPerLine - 1))}…`;
      wordIndex += 1;
    }
    lines.push(current);
    current = '';
  }

  if (lines.length < 2 && current) lines.push(current);
  const hasRemainingWords = wordIndex < words.length;
  if (hasRemainingWords && lines.length > 0) {
    const lastIndex = lines.length - 1;
    const line = lines[lastIndex].replace(/…$/, '');
    lines[lastIndex] = `${line.slice(0, Math.max(1, maxCharsPerLine - 1)).trimEnd()}…`;
  }

  return lines.slice(0, 2);
}
