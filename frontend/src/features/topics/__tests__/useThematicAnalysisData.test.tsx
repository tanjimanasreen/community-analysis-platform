import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useQuery, type UseQueryOptions } from '@tanstack/react-query';
import { getOverview } from '../../../api/overview';
import { getClusteredThemeEvidence, getClusteredThemeTimeline, getThemes, getTopics } from '../../../api/topics';
import { useDashboardContext } from '../../../hooks/useDashboardContext';
import { useThematicAnalysisData } from '../useThematicAnalysisData';

vi.mock('@tanstack/react-query', () => ({ useQuery: vi.fn() }));
vi.mock('../../../api/overview', () => ({ getOverview: vi.fn() }));
vi.mock('../../../api/topics', () => ({
  getClusteredThemeEvidence: vi.fn(),
  getClusteredThemeTimeline: vi.fn(),
  getThemes: vi.fn(),
  getTopics: vi.fn(),
}));
vi.mock('../../../hooks/useDashboardContext', () => ({ useDashboardContext: vi.fn() }));

describe('useThematicAnalysisData', () => {
  const queries: Array<Record<string, unknown>> = [];

  beforeEach(() => {
    queries.length = 0;
    vi.clearAllMocks();
    vi.mocked(useDashboardContext).mockReturnValue({
      selectedRunId: 'run-1',
      selectedRun: { status: 'completed' },
      verification: { ok: true },
    } as ReturnType<typeof useDashboardContext>);
    vi.mocked(useQuery).mockImplementation((options: UseQueryOptions<unknown, unknown>) => {
      queries.push(options as unknown as Record<string, unknown>);
      return { data: undefined, error: null, isPending: false, refetch: vi.fn() } as never;
    });
  });

  it('uses saved clustered-theme APIs and never requests continuity or similarity data', async () => {
    const { result } = renderHook(() => useThematicAnalysisData({
      communityId: '12',
      month: '2017-03',
      canonicalThemeId: 'ct_policy',
      timelineStart: '2017-01',
      timelineEnd: '2017-04',
      topicOffset: 0,
      topicLimit: 10,
      themeOffset: 0,
      themeLimit: 8,
    }));

    const keys = queries.map((query) => query.queryKey as unknown[]);
    expect(keys.map((key) => key[0])).toEqual([
      'thematic-overview',
      'thematic-topics',
      'thematic-themes',
      'thematic-theme-timeline',
      'thematic-cluster-evidence',
    ]);
    expect(keys.some((key) => String(key[0]).includes('transition'))).toBe(false);
    expect(keys.some((key) => String(key[0]).includes('similarity'))).toBe(false);
    expect(result.current).not.toHaveProperty('transitionsQuery');
    expect(result.current).not.toHaveProperty('similarityQuery');

    const signal = new AbortController().signal;
    for (const key of ['thematic-topics', 'thematic-themes', 'thematic-theme-timeline', 'thematic-cluster-evidence']) {
      const query = queries.find((candidate) => (candidate.queryKey as unknown[])[0] === key);
      await (query?.queryFn as (context: { signal: AbortSignal }) => unknown)({ signal });
    }

    expect(getTopics).toHaveBeenCalledWith(
      'run-1',
      expect.objectContaining({ type: 'matched', period: '2017-03', community_id: '12' }),
      signal,
    );
    expect(vi.mocked(getTopics).mock.calls[0][1]).not.toHaveProperty('canonical_theme_id');
    expect(getThemes).toHaveBeenCalledWith(
      'run-1',
      expect.objectContaining({ period: '2017-03', community_id: '12' }),
      signal,
    );
    expect(vi.mocked(getThemes).mock.calls[0][1]).not.toHaveProperty('canonical_theme_id');
    expect(vi.mocked(getThemes).mock.calls[0][1]).not.toHaveProperty('exact_theme');
    expect(getClusteredThemeTimeline).toHaveBeenCalledWith('run-1', expect.objectContaining({ period_start: '2017-01', period_end: '2017-04', scope: 'matched' }), signal);
    expect(getClusteredThemeEvidence).toHaveBeenCalledWith(
      'run-1',
      expect.objectContaining({ period: '2017-03', canonical_theme_id: 'ct_policy' }),
      signal,
    );
    expect(vi.mocked(getClusteredThemeEvidence).mock.calls[0][1]).not.toHaveProperty('community_id');
    expect(getOverview).not.toHaveBeenCalled();
  });
});
