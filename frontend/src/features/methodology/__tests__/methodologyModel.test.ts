import { describe, expect, it } from 'vitest';
import type { OverviewResponse, RunSummary } from '../../../types/api';
import { methodologyRunView, THESIS_BASELINE } from '../methodologyModel';

const run: RunSummary = { run_id: 'run-1', status: 'completed', platform: 'telegram', content_type: 'forward', date_start: '2019-01-01', date_end: '2019-01-31', year: 2019, month: 1, started_at: null, completed_at: null, artifact_count: 2 };
const overview: OverviewResponse = { run_id: 'run-1', platform: 'telegram', content_type: 'forward', date_start: null, date_end: null, total_users: null, total_messages: null, total_interactions: null, if_users: null, wif_users: null, if_messages: null, wif_messages: null, if_community_count: null, wif_community_count: null, matched_community_count: null, matched_percentage: null, persistent_community_count: null, top_themes: [], model_metadata: { theme_provider: 'ollama', theme_model: 'llama3' }, config_metadata: { louvain: { seed: 999 } } };

describe('methodology model', () => {
  it('preserves thesis defaults while displaying selected-run overrides separately', () => {
    expect(THESIS_BASELINE.louvain.seed).toBe(123);
    expect(THESIS_BASELINE.lda.num_topics).toBe(15);
    const view = methodologyRunView(run, null, overview, []);
    expect(view.configuration).toContainEqual(['louvain.seed', 999]);
    expect(view.models).toContainEqual(['theme_provider', 'ollama']);
    expect(view.models).not.toContainEqual(['theme_provider', 'openai']);
  });
});
