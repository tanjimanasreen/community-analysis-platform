import { describe, expect, it } from 'vitest';
import { resolveSemanticSearchParams, updateSemanticSearchParams } from '../semanticSearchParams';

describe('semantic search parameters', () => {
  it('uses canonical defaults for invalid values', () => {
    expect(resolveSemanticSearchParams(new URLSearchParams('topicType=x&token=x&semanticMetric=x'))).toEqual({
      topicType: 'matched', tokenView: 'unigram', metricView: 'both', communityId: null, month: null,
    });
  });

  it('updates semantic controls without removing run and metric state', () => {
    const params = updateSemanticSearchParams(
      new URLSearchParams('run=run-1&metric=if'),
      { topicType: 'partial', tokenView: 'bigram', metricView: 'wif', communityId: '12', month: '03' },
    );
    expect(params.get('run')).toBe('run-1');
    expect(params.get('metric')).toBe('if');
    expect(params.get('topicType')).toBe('partial');
    expect(params.get('semanticCommunity')).toBe('12');
  });
});
