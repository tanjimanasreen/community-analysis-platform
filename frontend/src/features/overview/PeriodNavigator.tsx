import { useEffect } from 'react';
import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react';
import { formatPeriod } from './overviewUtils';

interface PeriodNavigatorProps {
  periods: string[];
  selectedPeriod: string;
  onChange: (period: string) => void;
  isPlaying: boolean;
  onPlayingChange: (playing: boolean) => void;
}

export default function PeriodNavigator({
  periods,
  selectedPeriod,
  onChange,
  isPlaying,
  onPlayingChange,
}: PeriodNavigatorProps) {
  const index = periods.indexOf(selectedPeriod);
  const canGoPrevious = index > 0;
  const canGoNext = index >= 0 && index < periods.length - 1;

  useEffect(() => {
    if (!isPlaying || !canGoNext) {
      if (isPlaying && !canGoNext) onPlayingChange(false);
      return undefined;
    }
    const timer = window.setTimeout(() => onChange(periods[index + 1]), 5000);
    return () => window.clearTimeout(timer);
  }, [canGoNext, index, isPlaying, onChange, onPlayingChange, periods]);

  useEffect(() => {
    if (!isPlaying) return undefined;
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    const pauseForReducedMotion = () => {
      if (media?.matches) onPlayingChange(false);
    };
    const pauseWhenHidden = () => {
      if (document.hidden) onPlayingChange(false);
    };
    pauseForReducedMotion();
    media?.addEventListener?.('change', pauseForReducedMotion);
    document.addEventListener('visibilitychange', pauseWhenHidden);
    return () => {
      media?.removeEventListener?.('change', pauseForReducedMotion);
      document.removeEventListener('visibilitychange', pauseWhenHidden);
    };
  }, [isPlaying, onPlayingChange]);

  if (periods.length === 0) return null;

  return (
    <section className="overview-period-nav" aria-label="Overview period">
      <div className="overview-period-nav__heading">
        <div>
          <p className="overview-eyebrow">Monthly snapshot</p>
          <h2>{formatPeriod(selectedPeriod)}</h2>
        </div>
        <div className="overview-period-nav__actions">
          <button
            type="button"
            className="overview-icon-button"
            aria-label="Show previous month"
            title="Previous month"
            disabled={!canGoPrevious}
            onClick={() => canGoPrevious && onChange(periods[index - 1])}
          >
            <ChevronLeft size={17} />
          </button>
          <button
            type="button"
            className="overview-icon-button"
            aria-label="Show next month"
            title="Next month"
            disabled={!canGoNext}
            onClick={() => canGoNext && onChange(periods[index + 1])}
          >
            <ChevronRight size={17} />
          </button>
          <button
            type="button"
            className="overview-play-button"
            aria-pressed={isPlaying}
            onClick={() => onPlayingChange(!isPlaying)}
            disabled={periods.length < 2 || (!canGoNext && !isPlaying)}
          >
            {isPlaying ? <Pause size={15} /> : <Play size={15} />}
            {isPlaying ? 'Pause' : 'Play months'}
          </button>
        </div>
      </div>

      <div className="overview-period-nav__desktop" role="tablist" aria-label="Available months">
        {periods.map((period) => (
          <button
            type="button"
            role="tab"
            aria-selected={period === selectedPeriod}
            className={period === selectedPeriod ? 'is-selected' : ''}
            key={period}
            onClick={() => onChange(period)}
          >
            {formatPeriod(period)}
          </button>
        ))}
      </div>

      <label className="overview-period-nav__mobile">
        <span>Month</span>
        <select value={selectedPeriod} onChange={(event) => onChange(event.target.value)}>
          {periods.map((period) => (
            <option key={period} value={period}>{formatPeriod(period)}</option>
          ))}
        </select>
      </label>
    </section>
  );
}
