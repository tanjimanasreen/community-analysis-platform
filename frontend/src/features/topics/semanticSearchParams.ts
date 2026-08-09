import type { TopicType } from '../../types/api';
import type { SemanticMetricView, TokenView } from './topicModel';

export const TOPIC_TYPE_PARAM = 'topicType';
export const TOKEN_VIEW_PARAM = 'token';
export const SEMANTIC_METRIC_PARAM = 'semanticMetric';
export const SEMANTIC_COMMUNITY_PARAM = 'semanticCommunity';
export const THEME_MONTH_PARAM = 'themeMonth';
export const THEME_RANGE_START_PARAM = 'themeStart';
export const THEME_RANGE_END_PARAM = 'themeEnd';
export const EXACT_THEME_PARAM = 'exactTheme';
export const CANONICAL_THEME_PARAM = 'canonicalTheme';
export const THEME_PATH_PARAM = 'themePath';

export interface SemanticSearchState {
  topicType: TopicType;
  tokenView: TokenView;
  metricView: SemanticMetricView;
  communityId: string | null;
  month: string | null;
  timelineStart: string | null;
  timelineEnd: string | null;
  selectedTheme: string | null;
  canonicalThemeId: string | null;
  selectedPath: string | null;
}

export function resolveSemanticSearchParams(params: URLSearchParams): SemanticSearchState {
  const topicType = params.get(TOPIC_TYPE_PARAM) === 'partial' ? 'partial' : 'matched';
  const tokenCandidate = params.get(TOKEN_VIEW_PARAM);
  const tokenView: TokenView = tokenCandidate === 'bigram' || tokenCandidate === 'combined'
    ? tokenCandidate
    : 'unigram';
  const metricCandidate = params.get(SEMANTIC_METRIC_PARAM);
  const metricView: SemanticMetricView =
    metricCandidate === 'if' || metricCandidate === 'wif' || metricCandidate === 'general'
      ? metricCandidate
      : 'both';
  const community = params.get(SEMANTIC_COMMUNITY_PARAM)?.trim();
  const month = params.get(THEME_MONTH_PARAM)?.trim();
  const timelineStart = params.get(THEME_RANGE_START_PARAM)?.trim();
  const timelineEnd = params.get(THEME_RANGE_END_PARAM)?.trim();
  const selectedTheme = params.get(EXACT_THEME_PARAM)?.trim();
  const canonicalThemeId = params.get(CANONICAL_THEME_PARAM)?.trim();
  const selectedPath = params.get(THEME_PATH_PARAM)?.trim();
  return {
    topicType,
    tokenView,
    metricView,
    communityId: community || null,
    month: month || null,
    timelineStart: timelineStart || null,
    timelineEnd: timelineEnd || null,
    selectedTheme: selectedTheme || null,
    canonicalThemeId: canonicalThemeId || null,
    selectedPath: selectedPath || null,
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
  setOrDelete(next, THEME_RANGE_START_PARAM, patch.timelineStart);
  setOrDelete(next, THEME_RANGE_END_PARAM, patch.timelineEnd);
  setOrDelete(next, EXACT_THEME_PARAM, patch.selectedTheme);
  setOrDelete(next, CANONICAL_THEME_PARAM, patch.canonicalThemeId);
  setOrDelete(next, THEME_PATH_PARAM, patch.selectedPath);
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
