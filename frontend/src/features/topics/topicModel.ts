import type { MetricName, TopicRecord, TopicType } from '../../types/api';
import {
  displayArtifactValue,
  normalizedTextList,
  normalizeArtifactValue,
  type NormalizedArtifactValue,
} from '../../utils/artifactValues';
import { normalizeCommunityId } from '../../utils/communityIds';

export type TokenView = 'unigram' | 'bigram';
export type SemanticMetricView = MetricName | 'both';

export interface TopicViewModel {
  recordType: TopicType;
  ifCommunityId: string | null;
  wifCommunityId: string | null;
  jaccardScore: number | null;
  ifUnigramTopic: NormalizedArtifactValue;
  ifUnigramKeywords: string[];
  wifUnigramTopic: NormalizedArtifactValue;
  wifUnigramKeywords: string[];
  ifBigramTopic: NormalizedArtifactValue;
  ifBigramKeywords: string[];
  wifBigramTopic: NormalizedArtifactValue;
  wifBigramKeywords: string[];
  members: string[];
  ifMembers: string[];
  wifMembers: string[];
  commonMembers: string[];
  uncommonMembers: string[];
  rawRecord: TopicRecord;
}

export function adaptTopicRecord(
  record: TopicRecord,
  recordType: TopicType,
): TopicViewModel {
  return {
    recordType,
    ifCommunityId: normalizeCommunityId(record.absolute_community),
    wifCommunityId: normalizeCommunityId(record.weighted_community),
    jaccardScore:
      typeof record.jaccard_score === 'number' && Number.isFinite(record.jaccard_score)
        ? record.jaccard_score
        : null,
    ifUnigramTopic: normalizeArtifactValue(record.absolute_unigram_topic),
    ifUnigramKeywords: normalizedTextList(record.absolute_unigram_keywords),
    wifUnigramTopic: normalizeArtifactValue(record.weighted_unigram_topic),
    wifUnigramKeywords: normalizedTextList(record.weighted_unigram_keywords),
    ifBigramTopic: normalizeArtifactValue(record.absolute_bigram_topic),
    ifBigramKeywords: normalizedTextList(record.absolute_bigram_keywords),
    wifBigramTopic: normalizeArtifactValue(record.weighted_bigram_topic),
    wifBigramKeywords: normalizedTextList(record.weighted_bigram_keywords),
    members: normalizedTextList(record.members),
    ifMembers: normalizedTextList(record.absolute_members),
    wifMembers: normalizedTextList(record.weighted_members),
    commonMembers: normalizedTextList(record.common_members),
    uncommonMembers: normalizedTextList(record.uncommon_members),
    rawRecord: record,
  };
}

export function topicKeywords(
  topic: TopicViewModel,
  metric: MetricName,
  tokenView: TokenView,
): string[] {
  if (metric === 'if') {
    return tokenView === 'unigram' ? topic.ifUnigramKeywords : topic.ifBigramKeywords;
  }
  return tokenView === 'unigram' ? topic.wifUnigramKeywords : topic.wifBigramKeywords;
}

export function topicLabel(
  topic: TopicViewModel,
  metric: MetricName,
  tokenView: TokenView,
): string {
  const value = metric === 'if'
    ? tokenView === 'unigram'
      ? topic.ifUnigramTopic
      : topic.ifBigramTopic
    : tokenView === 'unigram'
      ? topic.wifUnigramTopic
      : topic.wifBigramTopic;
  return displayArtifactValue(value);
}

export function topicRecordKey(topic: TopicViewModel, index: number): string {
  return `${topic.recordType}:${topic.ifCommunityId ?? ''}:${topic.wifCommunityId ?? ''}:${index}`;
}
