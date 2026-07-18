import { describe, expect, it } from 'vitest';
import { adaptThemeRecord, providerMetadataEntries, themeFrequencies } from '../themeModel';

const baseRecord = {
  month: '03',
  absolute_community: 1,
  absolute_unigram_topic: null,
  absolute_unigram_keywords: null,
  weighted_community: '2',
  weighted_unigram_topic: null,
  weighted_unigram_keywords: null,
  absolute_bigram_topic: null,
  absolute_bigram_keywords: null,
  weighted_bigram_topic: null,
  weighted_bigram_keywords: null,
  members: null,
  general_theme_gpt: { Policy: ['alpha'] },
  general_theme_names: ['Policy'],
  absolute_theme_gpt: { Civic: ['vote'] },
  absolute_theme_names: ['Civic'],
  weighted_theme_gpt: { Law: ['court'] },
  weighted_theme_names: ['Law'],
  all_keywords: ['alpha'],
  absolute_keywords: ['vote'],
  weighted_keywords: ['court'],
};

describe('theme adapters', () => {
  it('keeps provider labels downstream from keyword evidence', () => {
    const theme = adaptThemeRecord(baseRecord, { configured_primary_provider: 'ollama' });
    expect(theme.ifCommunityId).toBe('1');
    expect(theme.wifCommunityId).toBe('2');
    expect(theme.generalThemes).toEqual(['Policy']);
    expect(theme.generalKeywords).toEqual(['alpha']);
    expect(theme.providerMetadata).toEqual({ configured_primary_provider: 'ollama' });
  });

  it('builds complete frequencies only when all records are present', () => {
    const complete = themeFrequencies({
      run_id: 'run-1', records: [baseRecord, baseRecord], total: 2, limit: 500, offset: 0, provider_metadata: null,
    });
    expect(complete?.[0]).toMatchObject({ name: 'Policy', count: 2, percentage: 100 });
    expect(themeFrequencies({
      run_id: 'run-1', records: [baseRecord], total: 2, limit: 1, offset: 0, provider_metadata: null,
    })).toBeNull();
  });

  it('shows non-OpenAI provider metadata without assumptions', () => {
    expect(providerMetadataEntries(
      { configured_primary_provider: 'ollama', configured_primary_model: 'llama3' },
      { similarity_model: 'model-x' },
    )).toContainEqual(['configured_primary_provider', 'ollama']);
  });
});
