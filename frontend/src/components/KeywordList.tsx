interface KeywordListProps {
  keywords: string[];
  emptyLabel?: string;
  limit?: number;
}

export default function KeywordList({
  keywords,
  emptyLabel = 'No keywords available',
  limit = 20,
}: KeywordListProps) {
  if (keywords.length === 0) {
    return <span className="text-xs text-muted">{emptyLabel}</span>;
  }

  const visible = keywords.slice(0, limit);
  return (
    <div className="flex flex-wrap gap-1.5" aria-label="Keyword evidence">
      {visible.map((keyword, index) => (
        <span
          key={`${keyword}-${index}`}
          className="rounded border border-border bg-panel-soft px-2 py-1 text-xs text-muted"
        >
          {keyword}
        </span>
      ))}
      {keywords.length > limit && (
        <span className="rounded border border-border bg-bg/30 px-2 py-1 text-xs text-muted">
          +{keywords.length - limit} more
        </span>
      )}
    </div>
  );
}
