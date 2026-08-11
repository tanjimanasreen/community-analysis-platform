import type { MetricName, ThemeRecord, TopicRecord } from '../../types/api';
import { communityIdsMatch } from '../../utils/communityIds';

export function themeNamesForCommunity(
  records: ThemeRecord[],
  metric: MetricName,
  communityId: string,
): string[] {
  const values = new Set<string>();
  for (const record of records) {
    const recordCommunity = metric === 'if' ? record.absolute_community : record.weighted_community;
    if (!communityIdsMatch(recordCommunity, communityId)) continue;
    const names = metric === 'if' ? record.absolute_theme_names : record.weighted_theme_names;
    for (const name of stringValues(names)) values.add(name);
    if (values.size === 0) {
      for (const name of stringValues(record.general_theme_names)) values.add(name);
    }
  }
  return [...values];
}

export function topicKeywordsForCommunity(
  records: Array<TopicRecord | ThemeRecord>,
  metric: MetricName,
  communityId: string,
): string[] {
  const values = new Set<string>();
  for (const record of records) {
    const recordCommunity = metric === 'if' ? record.absolute_community : record.weighted_community;
    if (!communityIdsMatch(recordCommunity, communityId)) continue;
    const unigram = metric === 'if' ? record.absolute_unigram_keywords : record.weighted_unigram_keywords;
    const bigram = metric === 'if' ? record.absolute_bigram_keywords : record.weighted_bigram_keywords;
    for (const keyword of [...stringValues(unigram), ...stringValues(bigram)]) values.add(keyword);
  }
  return [...values];
}

export function stringValues(value: unknown): string[] {
  if (typeof value === 'string') return value.trim() ? [value.trim()] : [];
  if (Array.isArray(value)) {
    return value.flatMap((item) => stringValues(item));
  }
  if (value && typeof value === 'object') {
    return Object.keys(value as Record<string, unknown>).filter(Boolean);
  }
  return [];
}
