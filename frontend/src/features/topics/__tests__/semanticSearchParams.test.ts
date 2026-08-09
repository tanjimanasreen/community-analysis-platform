import { describe, expect, it } from 'vitest';
import { resolveSemanticSearchParams, updateSemanticSearchParams } from '../semanticSearchParams';

describe('semantic search parameters', () => {
  it('uses canonical defaults for invalid values', () => {
    expect(resolveSemanticSearchParams(new URLSearchParams('topicType=x&token=x&semanticMetric=x'))).toEqual({
      topicType: 'matched',
      tokenView: 'unigram',
      metricView: 'both',
      communityId: null,
      month: null,
      timelineStart: null,
      timelineEnd: null,
      selectedTheme: null,
      canonicalThemeId: null,
      selectedPath: null,
    });
  });

  it('updates thematic controls without removing run and structural metric state', () => {
    const params = updateSemanticSearchParams(
      new URLSearchParams('run=run-1&metric=if'),
      {
        topicType: 'partial',
        tokenView: 'combined',
        metricView: 'general',
        communityId: '12',
        month: '2017-03',
        timelineStart: '2017-01',
        timelineEnd: '2017-04',
        selectedTheme: 'Policy',
        canonicalThemeId: 'ct_policy',
        selectedPath: '2017-01:1>2017-02:2',
      },
    );
    expect(params.get('run')).toBe('run-1');
    expect(params.get('metric')).toBe('if');
    expect(params.get('topicType')).toBe('partial');
    expect(params.get('token')).toBe('combined');
    expect(params.get('semanticMetric')).toBe('general');
    expect(params.get('semanticCommunity')).toBe('12');
    expect(params.get('themeMonth')).toBe('2017-03');
    expect(params.get('themeStart')).toBe('2017-01');
    expect(params.get('themeEnd')).toBe('2017-04');
    expect(params.get('exactTheme')).toBe('Policy');
    expect(params.get('canonicalTheme')).toBe('ct_policy');
    expect(params.get('themePath')).toBe('2017-01:1>2017-02:2');
  });
});
