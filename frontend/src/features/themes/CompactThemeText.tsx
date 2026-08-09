interface CompactThemeLabelProps {
  text: string;
  className?: string;
}

interface ThemeKeywordChipProps {
  keyword: string;
  className?: string;
}

export function CompactThemeLabel({ text, className = '' }: CompactThemeLabelProps) {
  return (
    <span className={`line-clamp-3 break-words ${className}`.trim()} title={text}>
      {text}
    </span>
  );
}

export function ThemeKeywordChip({ keyword, className = '' }: ThemeKeywordChipProps) {
  return (
    <span
      className={`inline-block max-w-48 truncate rounded-full border border-border px-2 py-1 text-xs text-muted ${className}`.trim()}
      title={keyword}
    >
      {keyword}
    </span>
  );
}
