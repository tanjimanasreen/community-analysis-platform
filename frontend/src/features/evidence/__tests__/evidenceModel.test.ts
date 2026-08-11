import { describe, expect, it } from 'vitest';
import {
  EVIDENCE_GROUPS,
  EVIDENCE_VIEWS,
  adaptCentralityLeader,
  evidenceColumns,
  resolveEvidenceView,
} from '../evidenceModel';

describe('evidence model', () => {
  it('groups persisted evidence by thesis dimension and defaults safely', () => {
    expect(EVIDENCE_GROUPS.map((group) => group.label)).toEqual([
      'Structural · RQ1',
      'Semantic · RQ2',
      'Temporal · RQ3 / RQ4',
      'Run Outputs',
    ]);
    expect(resolveEvidenceView('themes')).toBe('themes');
    expect(resolveEvidenceView('unknown')).toBe('communities');
    expect(resolveEvidenceView(null)).toBe('communities');
    expect(EVIDENCE_VIEWS.transitions.usesMetric).toBe(false);
    expect(EVIDENCE_VIEWS.outputs.requiresPeriod).toBe(false);
  });

  it('uses constructive summary columns while preserving raw detail fields separately', () => {
    expect(evidenceColumns('communities').map((column) => column.key)).toContain('community_id');
    expect(evidenceColumns('centrality').map((column) => column.key)).toEqual([
      'period', 'top_spreader', 'spreader_centrality', 'top_influencer', 'influencer_centrality',
    ]);
    expect(evidenceColumns('outputs')).toEqual([]);
  });

  it('adapts persisted centrality leaders without inventing community-local rankings', () => {
    const record = adaptCentralityLeader({
      period: '2017-03',
      spreader: {
        user_id: 'spreader-1', display_user_id: 'sp••1', centrality: 0.12,
        community_id: '4', community_assignment_status: 'available',
      },
      influencer: {
        user_id: 'influencer-1', display_user_id: 'in••1', centrality: 0.32,
        community_id: '7', community_assignment_status: 'available',
      },
      average_in_degree_centrality: 0.02,
      average_out_degree_centrality: 0.03,
    }, 'Persisted monthly centrality; no request-time recomputation.');

    expect(record).toMatchObject({
      period: '2017-03',
      top_spreader: 'sp••1',
      spreader_community: '4',
      top_influencer: 'in••1',
      influencer_community: '7',
      average_in_degree_centrality: 0.02,
      average_out_degree_centrality: 0.03,
    });
    expect(record.methodology_note).toMatch(/no request-time recomputation/i);
  });
});
