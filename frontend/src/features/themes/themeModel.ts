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
