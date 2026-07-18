import { stableThemeColor } from '../features/themes/themeModel';

interface ThemeLabelProps {
  names: string[];
  emptyLabel?: string;
}

export default function ThemeLabel({
  names,
  emptyLabel = 'Theme label unavailable',
}: ThemeLabelProps) {
  if (names.length === 0) return <span className="text-xs text-muted">{emptyLabel}</span>;
  return (
    <div className="flex flex-wrap gap-2" aria-label="Provider-generated theme labels">
      {names.map((name) => (
        <span
          key={name}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-panel-soft px-2.5 py-1 text-xs font-medium text-text-heading"
        >
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: stableThemeColor(name) }}
            aria-hidden="true"
          />
          {name}
        </span>
      ))}
    </div>
  );
}
