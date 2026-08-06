import { describe, expect, it } from 'vitest';
import type { TransitionRecord } from '../../../types/api';
import { buildContinuityModel, normalizeTransitionMonth } from '../continuityModel';

function transition({
  startMonth = '01',
  endMonth = '02',
  start = 1,
  end = 2,
  retained = ['u1', 'u2'],
  startMembers = 4,
  endMembers = 5,
  jaccard = 0.6,
}: Partial<{
  startMonth: string;
  endMonth: string;
  start: number;
  end: number;
  retained: unknown;
  startMembers: number | null;
  endMembers: number | null;
  jaccard: number;
}> = {}): TransitionRecord {
  return {
    start_month: startMonth,
    end_month: endMonth,
    start_month_community: start,
    end_month_community: end,
    jaccard_score: jaccard,
    common_members: retained,
    uncommon_members: null,
    start_month_members: null,
    total_start_month_members: startMembers,
    end_month_members: null,
    total_end_month_members: endMembers,
    start_month_absolute_theme: null,
    end_month_absolute_theme: null,
    start_month_weighted_theme: null,
    end_month_weighted_theme: null,
    start_month_general_theme: null,
    end_month_general_theme: null,
  };
}

describe('continuity model', () => {
  it('groups a four-month chain into one persistent path and ranks duration before retention', () => {
    const model = buildContinuityModel([
      transition({ startMonth: '01', endMonth: '02', start: 1, end: 2, retained: ['a', 'b'] }),
      transition({ startMonth: '02', endMonth: '03', start: 2, end: 3, retained: ['a'] }),
      transition({ startMonth: '03', endMonth: '04', start: 3, end: 4, retained: ['a'] }),
      transition({ startMonth: '01', endMonth: '02', start: 10, end: 11, retained: ['x', 'y', 'z', 'w'] }),
    ]);
    expect(model.totalPaths).toBe(2);
    expect(model.paths[0].duration).toBe(4);
    expect(model.paths[0].nodes.map((node) => node.communityId)).toEqual(['1', '2', '3', '4']);
    expect(model.paths[0].totalRetainedMembers).toBe(4);
    expect(model.months.map((month) => month.label)).toEqual(['January', 'February', 'March', 'April']);
  });

  it('uses canonical common members only and leaves missing retained counts unavailable', () => {
    const model = buildContinuityModel([
      transition({ retained: null, jaccard: 0.9 }),
    ]);
    expect(model.paths[0].links[0].retainedCount).toBeNull();
    expect(model.paths[0].links[0].jaccard).toBe(0.9);
    expect(model.paths[0].retainedCountAvailable).toBe(false);
  });

  it('marks conflicting member totals rather than reconciling them silently', () => {
    const model = buildContinuityModel([
      transition({ startMonth: '01', endMonth: '02', start: 1, end: 2, endMembers: 5 }),
      transition({ startMonth: '02', endMonth: '03', start: 2, end: 3, startMembers: 7 }),
    ]);
    const conflicted = model.paths[0].nodes.find((node) => node.communityId === '2');
    expect(conflicted?.memberCountInconsistent).toBe(true);
    expect(conflicted?.memberCount).toBeNull();
    expect(conflicted?.memberCountValues).toEqual([5, 7]);
  });

  it('normalizes numeric, named, and year-month values into chronological labels', () => {
    expect(normalizeTransitionMonth('02')).toMatchObject({ key: '02', label: 'February', order: 2 });
    expect(normalizeTransitionMonth('Mar')).toMatchObject({ key: '03', label: 'March', order: 3 });
    expect(normalizeTransitionMonth('2017-04')).toMatchObject({ key: '2017-04', label: 'April 2017' });
  });
});
