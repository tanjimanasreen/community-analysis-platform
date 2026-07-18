import { describe, expect, it } from 'vitest';
import type { TransitionRecord } from '../../../types/api';
import { buildTransitionSankeyModel, transitionsCsv } from '../transitionModel';

const transition = (score: number, start = 1, end = 2): TransitionRecord => ({
  start_month: '03', end_month: '04', start_month_community: start,
  end_month_community: end, jaccard_score: score, common_members: ['u1'],
  uncommon_members: null, start_month_members: ['u1'], total_start_month_members: 1,
  end_month_members: ['u1'], total_end_month_members: 1, start_month_absolute_theme: null,
  end_month_absolute_theme: null, start_month_weighted_theme: null,
  end_month_weighted_theme: null, start_month_general_theme: null, end_month_general_theme: null,
});

describe('transition model', () => {
  it('builds month/community Sankey nodes and caps links by strongest Jaccard', () => {
    const model = buildTransitionSankeyModel([transition(0.2), transition(0.8, 3, 4)], 1);
    expect(model.totalLinks).toBe(2);
    expect(model.displayedLinks).toBe(1);
    expect(model.links[0].jaccard).toBe(0.8);
    expect(model.nodes.map((node) => node.name)).toEqual(['03:3', '04:4']);
  });

  it('exports only canonical visible transition fields', () => {
    const csv = transitionsCsv([transition(0.6)]);
    expect(csv).toContain('jaccard_score');
    expect(csv).toContain('0.6');
    expect(csv).not.toContain('reappearing');
  });
});
