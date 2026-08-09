import type { EvolutionPath, PathMembershipRecord } from '../../../types/api';

interface Props { path: EvolutionPath; mobility: PathMembershipRecord[]; }

export default function EvolutionEvidence({ path, mobility }: Props) {
  const mobilityByStep = new Map(mobility.map((record) => [record.step_index, record]));
  return (
    <details className="panel p-5">
      <summary className="cursor-pointer text-sm font-bold text-text-heading">View analytical evidence</summary>
      <p className="mt-2 text-xs text-muted">Path/month IDs, exact structural scores, member-state counts, and raw evolution theme labels used by the dashboard.</p>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-[980px] text-left text-xs">
          <thead className="border-b border-border text-muted">
            <tr>
              <th className="px-3 py-3">Month</th><th className="px-3 py-3">Community</th><th className="px-3 py-3">Members</th>
              <th className="px-3 py-3">Jaccard</th><th className="px-3 py-3">Retained</th><th className="px-3 py-3">New</th>
              <th className="px-3 py-3">Reappeared</th><th className="px-3 py-3">Exited</th><th className="px-3 py-3">General theme</th>
            </tr>
          </thead>
          <tbody>
            {path.steps.map((step) => {
              const move = mobilityByStep.get(step.step_index);
              return (
                <tr key={step.community_key} className="border-b border-border/40 align-top">
                  <td className="px-3 py-3 text-text-heading">{step.month}</td>
                  <td className="px-3 py-3 font-mono text-text-heading">{step.community_key}</td>
                  <td className="px-3 py-3 text-muted">{step.member_count}</td>
                  <td className="px-3 py-3 text-muted">{step.jaccard_from_previous?.toFixed(3) ?? 'Path start'}</td>
                  <td className="px-3 py-3 text-muted">{move?.existing_count ?? '—'}</td>
                  <td className="px-3 py-3 text-muted">{move ? Math.max(0, move.new_count - move.reappearing_count) : '—'}</td>
                  <td className="px-3 py-3 text-muted">{move?.reappearing_count ?? '—'}</td>
                  <td className="px-3 py-3 text-muted">{move?.lost_count ?? '—'}</td>
                  <td className="max-w-sm px-3 py-3 text-muted">{step.general_theme || 'Unavailable'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
