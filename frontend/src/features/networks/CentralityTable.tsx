import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { TablePage } from '../../types/api';
import { pageRange } from '../../utils/pagination';

const ALLOWED_COLUMNS = [
  { key: 'month', label: 'Month' },
  { key: 'absolute', label: 'IF centrality' },
  { key: 'weighted', label: 'WIF centrality' },
] as const;

interface CentralityTableProps {
  response: TablePage | undefined;
  onPrevious: () => void;
  onNext: () => void;
}

export default function CentralityTable({ response, onPrevious, onNext }: CentralityTableProps) {
  const records = response?.records ?? [];
  const offset = response?.offset ?? 0;
  const limit = response?.limit ?? records.length;
  const total = response?.total ?? 0;

  return (
    <section className="bg-panel border border-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-border">
        <div>
          <h2 className="text-sm font-bold text-text-heading">Centrality artifact</h2>
          <p className="mt-1 text-[11px] text-muted">Allowlisted columns from the frozen user-centrality artifact contract.</p>
        </div>
        <span className="text-xs text-muted">{pageRange(offset, limit, total)}</span>
      </div>
      {records.length === 0 ? (
        <div className="p-8 text-center" aria-live="polite">
          <p className="font-semibold text-text-heading">No centrality records available</p>
          <p className="mt-2 text-sm text-muted">This page of the centrality artifact is empty.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border bg-panel-soft/40 text-muted">
                {ALLOWED_COLUMNS.map((column) => (
                  <th key={column.key} className="px-5 py-3 font-semibold">{column.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {records.map((record, index) => (
                <tr key={`${String(record.month ?? 'record')}-${index}`} className="border-b border-border/40">
                  {ALLOWED_COLUMNS.map((column) => (
                    <td key={column.key} className="max-w-md px-5 py-3 align-top text-muted">
                      <pre className="whitespace-pre-wrap break-words font-sans text-xs">
                        {displayValue(record[column.key])}
                      </pre>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-border">
        <button
          type="button"
          aria-label="Previous centrality page"
          disabled={offset <= 0}
          onClick={onPrevious}
          className="rounded-md border border-border p-1.5 text-muted hover:bg-panel-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft size={15} />
        </button>
        <button
          type="button"
          aria-label="Next centrality page"
          disabled={offset + limit >= total}
          onClick={onNext}
          className="rounded-md border border-border p-1.5 text-muted hover:bg-panel-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronRight size={15} />
        </button>
      </div>
    </section>
  );
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return 'Unavailable';
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}
