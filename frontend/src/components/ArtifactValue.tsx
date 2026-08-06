import type { ReactNode } from 'react';
import {
  displayArtifactValue,
  normalizeArtifactValue,
  type NormalizedArtifactValue,
} from '../utils/artifactValues';

interface ArtifactValueProps {
  value: unknown;
  compact?: boolean;
  maxItems?: number;
  depth?: number;
}

const MAX_EXPANDED_ITEMS = 50;

export default function ArtifactValue({
  value,
  compact = false,
  maxItems = compact ? 4 : 12,
  depth = 0,
}: ArtifactValueProps) {
  const normalized = normalizeArtifactValue(value);
  return (
    <div className={`artifact-value ${compact ? 'artifact-value--compact' : ''}`}>
      {renderNormalizedValue(normalized, { compact, maxItems, depth })}
    </div>
  );
}

function renderNormalizedValue(
  value: NormalizedArtifactValue,
  options: Required<Pick<ArtifactValueProps, 'compact' | 'maxItems' | 'depth'>>,
): ReactNode {
  if (value === null) return <span className="artifact-value--unavailable">Unavailable</span>;
  if (typeof value === 'number' || typeof value === 'boolean') {
    return <span>{displayArtifactValue(value)}</span>;
  }
  if (typeof value === 'string') return renderText(value, options.compact);

  if (options.depth >= 4) {
    return <code className="artifact-value__code">{displayArtifactValue(value)}</code>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="artifact-value--unavailable">—</span>;
    const visible = value.slice(0, options.maxItems);
    return (
      <div className="artifact-value__list" aria-label={`${value.length} values`}>
        {visible.map((item, index) => (
          <div className="artifact-value__chip" key={`${index}-${displayArtifactValue(item)}`}>
            {renderNormalizedValue(item, { ...options, compact: true, depth: options.depth + 1 })}
          </div>
        ))}
        {value.length > visible.length && (
          <details className="artifact-value__more">
            <summary>+{value.length - visible.length} more</summary>
            <div className="artifact-value__expanded-list">
              {value.slice(visible.length, visible.length + MAX_EXPANDED_ITEMS).map((item, index) => (
                <div key={index}>
                  {renderNormalizedValue(item, { ...options, compact: false, depth: options.depth + 1 })}
                </div>
              ))}
              {value.length > visible.length + MAX_EXPANDED_ITEMS && (
                <p className="artifact-value--unavailable">
                  {value.length - visible.length - MAX_EXPANDED_ITEMS} additional values are omitted from the dashboard.
                </p>
              )}
            </div>
          </details>
        )}
      </div>
    );
  }

  const entries = Object.entries(value);
  if (entries.length === 0) return <span className="artifact-value--unavailable">—</span>;
  const visibleEntries = entries.slice(0, options.maxItems);
  const renderEntry = ([key, item]: [string, NormalizedArtifactValue]) => (
    <div className="artifact-value__object-row" key={key}>
      <dt>{humanizeKey(key)}</dt>
      <dd>{renderNormalizedValue(item, { ...options, depth: options.depth + 1 })}</dd>
    </div>
  );

  if (options.compact) {
    return (
      <div className="artifact-value__object-preview">
        {visibleEntries.map(([key, item]) => (
          <div className="artifact-value__pair" key={key}>
            <span className="artifact-value__key">{humanizeKey(key)}:</span>{' '}
            {renderNormalizedValue(item, { ...options, compact: true, depth: options.depth + 1 })}
          </div>
        ))}
        {entries.length > visibleEntries.length && (
          <span className="artifact-value--unavailable">+{entries.length - visibleEntries.length} fields</span>
        )}
      </div>
    );
  }

  return (
    <div>
      <dl className="artifact-value__object">{visibleEntries.map(renderEntry)}</dl>
      {entries.length > visibleEntries.length && (
        <details className="artifact-value__more artifact-value__object-more">
          <summary>+{entries.length - visibleEntries.length} more fields</summary>
          <dl className="artifact-value__object">
            {entries
              .slice(visibleEntries.length, visibleEntries.length + MAX_EXPANDED_ITEMS)
              .map(renderEntry)}
          </dl>
          {entries.length > visibleEntries.length + MAX_EXPANDED_ITEMS && (
            <p className="artifact-value--unavailable">
              {entries.length - visibleEntries.length - MAX_EXPANDED_ITEMS} additional fields are omitted from the dashboard.
            </p>
          )}
        </details>
      )}
    </div>
  );
}

function renderText(value: string, compact: boolean): ReactNode {
  const text = value.trim();
  if (!text) return <span className="artifact-value--unavailable">—</span>;
  const multiline = text.includes('\n');
  const long = text.length > (compact ? 96 : 240);
  if (!multiline && !long) return <span className="artifact-value__text">{text}</span>;
  const previewLength = compact ? 96 : 180;
  return (
    <details className="artifact-value__long-text">
      <summary>{text.slice(0, previewLength)}{text.length > previewLength ? '…' : ''}</summary>
      <pre>{text}</pre>
    </details>
  );
}

function humanizeKey(value: string): string {
  return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}
