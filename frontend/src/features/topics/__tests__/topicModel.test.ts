import { describe, expect, it } from 'vitest';
import { adaptTopicRecord, topicKeywords, topicLabel } from '../topicModel';

const record = {
  absolute_community: 7,
  absolute_unigram_topic: 'topic-if',
  absolute_unigram_keywords: ['alpha', 'beta'],
  weighted_community: '9',
  weighted_unigram_topic: 'topic-wif',
  weighted_unigram_keywords: '["gamma"]',
  absolute_bigram_topic: 4,
  absolute_bigram_keywords: ['alpha beta'],
  weighted_bigram_topic: null,
  weighted_bigram_keywords: null,
  members: ['u1', 'u2'],
  absolute_members: ['u1'],
  weighted_members: ['u2'],
  jaccard_score: 0.5,
  common_members: ['u1'],
  uncommon_members: ['u2'],
};

describe('topic adapters', () => {
  it('keeps IF and WIF community IDs distinct and normalizes semantic fields', () => {
    const topic = adaptTopicRecord(record, 'matched');
    expect(topic.ifCommunityId).toBe('7');
    expect(topic.wifCommunityId).toBe('9');
    expect(topic.commonMembers).toEqual(['u1']);
    expect(topicKeywords(topic, 'if', 'bigram')).toEqual(['alpha beta']);
    expect(topicKeywords(topic, 'wif', 'unigram')).toEqual(['gamma']);
    expect(topicLabel(topic, 'if', 'bigram')).toBe('4');
  });

  it('labels partial records without inventing missing data', () => {
    const topic = adaptTopicRecord({ ...record, weighted_community: null }, 'partial');
    expect(topic.recordType).toBe('partial');
    expect(topic.wifCommunityId).toBeNull();
  });
});
