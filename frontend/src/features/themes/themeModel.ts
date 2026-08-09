import type { ThemeRecord, ThemesResponse } from '../../types/api';
import { normalizedTextList } from '../../utils/artifactValues';
import { normalizeCommunityId } from '../../utils/communityIds';

export interface ThemeViewModel {
  month: string | null;
  ifCommunityId: string | null;
  wifCommunityId: string | null;
  generalThemes: string[];
  ifThemes: string[];
  wifThemes: string[];
  generalKeywords: string[];
  ifKeywords: string[];
  wifKeywords: string[];
  providerMetadata: Record<string, unknown> | null;
  rawRecord: ThemeRecord;
}

export interface ThemeFrequency {
  name: string;
  count: number;
  percentage: number;
  color: string;
}

export interface SelectedMonthTheme {
  name: string;
  communityCount: number;
  percentage: number;
  keywords: string[];
  color: string;
}

export interface SelectedMonthThemeSummary {
  incomplete: boolean;
  themes: SelectedMonthTheme[];
  totalThemedCommunityPairs: number;
  excludedRecordsWithoutCommunityPair: number;
  returnedRecords: number;
  totalRecords: number;
}

export function adaptThemeRecord(
  record: ThemeRecord,
  providerMetadata: Record<string, unknown> | null = null,
): ThemeViewModel {
  return {
    month: record.month,
    ifCommunityId: normalizeCommunityId(record.absolute_community),
    wifCommunityId: normalizeCommunityId(record.weighted_community),
    generalThemes: themeNames(record.general_theme_names, record.general_theme_gpt),
    ifThemes: themeNames(record.absolute_theme_names, record.absolute_theme_gpt),
    wifThemes: themeNames(record.weighted_theme_names, record.weighted_theme_gpt),
    generalKeywords: keywords(record.all_keywords, record.general_theme_gpt),
    ifKeywords: keywords(record.absolute_keywords, record.absolute_theme_gpt),
    wifKeywords: keywords(record.weighted_keywords, record.weighted_theme_gpt),
    providerMetadata,
    rawRecord: record,
  };
}

function themeNames(names: unknown, providerOutput: unknown): string[] {
  const explicit = normalizedTextList(names);
  return explicit.length > 0 ? explicit : normalizedTextList(providerOutput, 'keys');
}

function keywords(explicitKeywords: unknown, providerOutput: unknown): string[] {
  const explicit = normalizedTextList(explicitKeywords);
  return explicit.length > 0
    ? explicit
    : normalizedTextList(providerOutput, 'values');
}

export function availableThemeMonths(records: ThemeRecord[]): string[] {
  return [...new Set(records.map((record) => record.month).filter((month): month is string => Boolean(month)))]
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));
}

export function themeFrequencies(response: ThemesResponse): ThemeFrequency[] | null {
  if (response.total > response.records.length) return null;
  const counts = new Map<string, number>();
  for (const record of response.records) {
    const model = adaptThemeRecord(record, response.provider_metadata);
    const names = model.generalThemes.length > 0
      ? model.generalThemes
      : [...new Set([...model.ifThemes, ...model.wifThemes])];
    for (const name of names) {
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
  }
  const denominator = [...counts.values()].reduce((sum, count) => sum + count, 0);
  if (denominator === 0) return [];
  return [...counts.entries()]
    .map(([name, count]) => ({
      name,
      count,
      percentage: (count * 100) / denominator,
      color: stableThemeColor(name),
    }))
    .sort((left, right) => right.count - left.count || left.name.localeCompare(right.name));
}

export function selectedMonthThemeSummary(
  response: ThemesResponse | null | undefined,
  limit = 5,
): SelectedMonthThemeSummary {
  if (!response) {
    return {
      incomplete: false,
      themes: [],
      totalThemedCommunityPairs: 0,
      excludedRecordsWithoutCommunityPair: 0,
      returnedRecords: 0,
      totalRecords: 0,
    };
  }

  if (response.total > response.records.length) {
    return {
      incomplete: true,
      themes: [],
      totalThemedCommunityPairs: 0,
      excludedRecordsWithoutCommunityPair: 0,
      returnedRecords: response.records.length,
      totalRecords: response.total,
    };
  }

  const themeBuckets = new Map<string, {
    pairs: Set<string>;
    keywords: Map<string, { display: string; index: number; pairs: Set<string> }>;
  }>();
  const themedPairs = new Set<string>();
  let excludedRecordsWithoutCommunityPair = 0;
  let keywordIndex = 0;

  for (const record of response.records) {
    const model = adaptThemeRecord(record, response.provider_metadata);
    const pairKey = matchedCommunityPairKey(model.ifCommunityId, model.wifCommunityId);
    if (!pairKey) {
      excludedRecordsWithoutCommunityPair += 1;
      continue;
    }

    const entries = themeEvidenceEntries(model);
    if (entries.length === 0) continue;
    themedPairs.add(pairKey);

    for (const entry of entries) {
      const exactName = normalizeDisplayText(entry.name);
      if (!exactName) continue;
      const bucket = themeBuckets.get(exactName) ?? {
        pairs: new Set<string>(),
        keywords: new Map<string, { display: string; index: number; pairs: Set<string> }>(),
      };
      themeBuckets.set(exactName, bucket);
      bucket.pairs.add(pairKey);

      for (const keyword of entry.keywords) {
        const displayKeyword = normalizeDisplayText(keyword);
        if (!displayKeyword) continue;
        const key = displayKeyword.toLocaleLowerCase();
        const evidence = bucket.keywords.get(key) ?? {
          display: displayKeyword,
          index: keywordIndex++,
          pairs: new Set<string>(),
        };
        evidence.pairs.add(pairKey);
        bucket.keywords.set(key, evidence);
      }
    }
  }

  const denominator = themedPairs.size;
  const themes = [...themeBuckets.entries()]
    .map(([name, bucket]) => ({
      name,
      communityCount: bucket.pairs.size,
      percentage: denominator > 0 ? (bucket.pairs.size * 100) / denominator : 0,
      keywords: [...bucket.keywords.values()]
        .sort((left, right) => right.pairs.size - left.pairs.size || left.index - right.index || left.display.localeCompare(right.display))
        .slice(0, 3)
        .map((entry) => entry.display),
      color: stableThemeColor(name),
    }))
    .sort((left, right) => right.communityCount - left.communityCount || left.name.localeCompare(right.name));

  return {
    incomplete: false,
    themes: themes.slice(0, Math.max(0, limit)),
    totalThemedCommunityPairs: denominator,
    excludedRecordsWithoutCommunityPair,
    returnedRecords: response.records.length,
    totalRecords: response.total,
  };
}

function matchedCommunityPairKey(ifCommunityId: string | null, wifCommunityId: string | null): string | null {
  if (!ifCommunityId && !wifCommunityId) return null;
  return `if:${ifCommunityId ?? ''}|wif:${wifCommunityId ?? ''}`;
}

function themeEvidenceEntries(model: ThemeViewModel): Array<{ name: string; keywords: string[] }> {
  if (model.generalThemes.length > 0) {
    return [...new Set(model.generalThemes.map(normalizeDisplayText).filter(Boolean))]
      .map((name) => ({ name, keywords: model.generalKeywords }));
  }

  const fallback = new Map<string, { name: string; keywords: string[] }>();
  for (const name of model.ifThemes) {
    const normalized = normalizeDisplayText(name);
    if (!normalized) continue;
    const key = normalized;
    fallback.set(key, { name: normalized, keywords: model.ifKeywords });
  }
  for (const name of model.wifThemes) {
    const normalized = normalizeDisplayText(name);
    if (!normalized) continue;
    const key = normalized;
    const existing = fallback.get(key);
    fallback.set(key, {
      name: existing?.name ?? normalized,
      keywords: [...new Set([...(existing?.keywords ?? []), ...model.wifKeywords])],
    });
  }
  return [...fallback.values()];
}

function normalizeDisplayText(value: string): string {
  return value.trim().replace(/\s+/g, ' ');
}

export function stableThemeColor(name: string): string {
  let hash = 0;
  for (const character of name) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return `hsl(${hash % 360} 62% 58%)`;
}

export function providerMetadataEntries(
  providerMetadata: Record<string, unknown> | null | undefined,
  modelMetadata: Record<string, unknown> | null | undefined,
): Array<[string, unknown]> {
  const entries: Array<[string, unknown]> = [];
  for (const [key, value] of Object.entries(providerMetadata ?? {})) {
    entries.push([key, value]);
  }
  for (const [key, value] of Object.entries(modelMetadata ?? {})) {
    if (!entries.some(([existing]) => existing === key)) entries.push([key, value]);
  }
  return entries;
}
