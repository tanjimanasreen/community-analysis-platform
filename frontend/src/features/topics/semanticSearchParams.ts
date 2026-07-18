import type { TopicType } from '../../types/api';
import type { SemanticMetricView, TokenView } from './topicModel';

export const TOPIC_TYPE_PARAM = 'topicType';
export const TOKEN_VIEW_PARAM = 'token';
export const SEMANTIC_METRIC_PARAM = 'semanticMetric';
export const SEMANTIC_COMMUNITY_PARAM = 'semanticCommunity';
export const THEME_MONTH_PARAM = 'themeMonth';

export interface SemanticSearchState {
  topicType: TopicType;
  tokenView: TokenView;
  metricView: SemanticMetricView;
  communityId: string | null;
  month: string | null;
}

export function resolveSemanticSearchParams(params: URLSearchParams): SemanticSearchState {
  const topicType = params.get(TOPIC_TYPE_PARAM) === 'partial' ? 'partial' : 'matched';
  const tokenView = params.get(TOKEN_VIEW_PARAM) === 'bigram' ? 'bigram' : 'unigram';
  const metricCandidate = params.get(SEMANTIC_METRIC_PARAM);
  const metricView: SemanticMetricView =
    metricCandidate === 'if' || metricCandidate === 'wif' ? metricCandidate : 'both';
  const community = params.get(SEMANTIC_COMMUNITY_PARAM)?.trim();
  const month = params.get(THEME_MONTH_PARAM)?.trim();
  return {
    topicType,
    tokenView,
    metricView,
    communityId: community || null,
    month: month || null,
  };
}

export function updateSemanticSearchParams(
  current: URLSearchParams,
  patch: Partial<SemanticSearchState>,
): URLSearchParams {
  const next = new URLSearchParams(current);
  setOrDelete(next, TOPIC_TYPE_PARAM, patch.topicType);
  setOrDelete(next, TOKEN_VIEW_PARAM, patch.tokenView);
  setOrDelete(next, SEMANTIC_METRIC_PARAM, patch.metricView);
  setOrDelete(next, SEMANTIC_COMMUNITY_PARAM, patch.communityId);
  setOrDelete(next, THEME_MONTH_PARAM, patch.month);
  return next;
}

function setOrDelete(
  params: URLSearchParams,
  key: string,
  value: string | null | undefined,
): void {
  if (value === undefined) return;
  if (value === null || value === '') params.delete(key);
  else params.set(key, value);
}
