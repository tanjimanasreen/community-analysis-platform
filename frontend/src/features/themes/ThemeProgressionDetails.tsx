import { Link } from 'react-router-dom';
import { Network } from 'lucide-react';
import type { ThemeProgressionPath } from './themeProgressionModel';
import { periodLabel } from './themeTrendModel';

interface Props {
  path: ThemeProgressionPath | null;
  networkHref: (metric: 'if' | 'wif', communityId: string, period: string) => string;
}

export default function ThemeProgressionDetails({ path, networkHref }: Props) {
  if (!path) return null;
  return (
    <aside className="mt-5 rounded-xl border border-border bg-bg/20 p-4">
      <h3 className="text-sm font-bold text-text-heading">Selected path evidence</h3>
      <p className="mt-1 text-xs text-muted">Saved transition themes and joined monthly LDA keywords. No browser-side matching or similarity is computed.</p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[720px] text-left text-xs">
          <thead><tr className="border-b border-border text-muted"><th className="p-2">Month</th><th className="p-2">Community IDs</th><th className="p-2">Exact saved themes</th><th className="p-2">LDA keywords</th><th className="p-2">Next transition</th></tr></thead>
          <tbody>
            {path.nodes.map((node, index) => {
              const link = path.links[index];
              return (
                <tr key={node.key} className="border-b border-border/50 align-top">
                  <td className="p-2 font-semibold text-text-heading">{periodLabel(node.period)}</td>
                  <td className="p-2 text-muted">
                    <p>Path ID: {node.communityId}</p>
                    <p>IF: {node.absoluteCommunityId ?? 'unavailable'} · WIF: {node.weightedCommunityId ?? 'unavailable'}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {node.absoluteCommunityId && <Link className="inline-flex items-center gap-1 text-primary hover:underline" to={networkHref('if', node.absoluteCommunityId, node.period)}><Network size={12} />IF network</Link>}
                      {node.weightedCommunityId && <Link className="inline-flex items-center gap-1 text-primary hover:underline" to={networkHref('wif', node.weightedCommunityId, node.period)}><Network size={12} />WIF network</Link>}
                    </div>
                  </td>
                  <td className="p-2 text-text-heading">{node.labels.join(' · ') || 'Unavailable'}</td>
                  <td className="p-2 text-muted">{node.keywords.slice(0, 12).join(', ') || 'Unavailable'}</td>
                  <td className="p-2 text-muted">{link ? `Jaccard ${link.jaccard.toFixed(3)} · retained ${link.retainedCount ?? 'unavailable'} · ${link.startCount ?? '?'} → ${link.endCount ?? '?'}` : 'Path end'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </aside>
  );
}
