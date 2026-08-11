import { normalizeArtifactValue, type NormalizedArtifactValue } from '../../utils/artifactValues';
import { providerMetadataEntries } from './themeModel';

export interface ProviderMetadataItem {
  key: string;
  label: string;
  value: unknown;
  kind?: 'default' | 'currency' | 'digest';
}

export interface ProviderTimingSummary {
  key: string;
  label: string;
  sampleCount: number;
  p50Ms: number;
  p95Ms: number;
}

export interface ProviderMetadataViewModel {
  configuration: ProviderMetadataItem[];
  operational: ProviderMetadataItem[];
  timing: ProviderTimingSummary[];
  advanced: ProviderMetadataItem[];
  rawRunMetrics: Record<string, NormalizedArtifactValue> | null;
  promptPayloadOmitted: boolean;
  hasMetadata: boolean;
}

const CONFIGURATION_FIELDS: Array<[string, string]> = [
  ['configured_primary_provider', 'Primary provider'],
  ['configured_primary_model', 'Primary model'],
  ['configured_fallback_chain', 'Fallback chain'],
  ['prompt_version', 'Prompt version'],
  ['semantic_task_version', 'Semantic task version'],
  ['schema_version', 'Schema version'],
];

const OPERATIONAL_FIELDS: Array<[string, string, ProviderMetadataItem['kind']?]> = [
  ['logical_theme_requests', 'Theme requests'],
  ['calls', 'Provider calls'],
  ['outbound_requests', 'Outbound requests'],
  ['cache_hits', 'Cache hits'],
  ['cache_misses', 'Cache misses'],
  ['cache_writes', 'Cache writes'],
  ['cache_errors', 'Cache errors'],
  ['fallback_attempts', 'Fallback attempts'],
  ['total_prompt_tokens', 'Prompt tokens'],
  ['total_completion_tokens', 'Completion tokens'],
  ['total_cost', 'Estimated cost', 'currency'],
];

const TIMING_FIELDS: Array<[string, string]> = [
  ['latency_ms_list', 'Latency'],
  ['ttft_ms_list', 'Time to first token'],
  ['tpot_ms_list', 'Time per output token'],
];

const DIGEST_FIELDS = new Set(['provider_config_digest', 'generation_settings_digest']);
const PROMPT_PAYLOAD_KEY = 'prompts_and_responses';

export function buildProviderMetadataViewModel(
  providerMetadata: Record<string, unknown> | null | undefined,
  modelMetadata: Record<string, unknown> | null | undefined,
): ProviderMetadataViewModel {
  const merged = new Map(providerMetadataEntries(providerMetadata, modelMetadata));
  const runMetrics = asRecord(merged.get('run_metrics'));
  const configuration = CONFIGURATION_FIELDS.flatMap(([key, label]) => {
    if (!merged.has(key)) return [];
    return [{ key, label, value: merged.get(key) } satisfies ProviderMetadataItem];
  });

  const operational = OPERATIONAL_FIELDS.flatMap(([key, label, kind = 'default']) => {
    const value = runMetrics?.[key];
    if (value === undefined || value === null) return [];
    const numeric = asFiniteNumber(value);
    if (numeric === null) return [];
    return [{ key, label, value: numeric, kind } satisfies ProviderMetadataItem];
  });

  const timing = TIMING_FIELDS.flatMap(([key, label]) => {
    const samples = numericArray(runMetrics?.[key]);
    if (samples.length === 0) return [];
    return [{
      key,
      label,
      sampleCount: samples.length,
      p50Ms: percentile(samples, 0.5),
      p95Ms: percentile(samples, 0.95),
    } satisfies ProviderTimingSummary];
  });

  const consumed = new Set([
    ...CONFIGURATION_FIELDS.map(([key]) => key),
    'run_metrics',
  ]);
  const advanced = [...merged.entries()]
    .filter(([key]) => !consumed.has(key))
    .map(([key, value]) => ({
      key,
      label: humanizeKey(key),
      value,
      kind: DIGEST_FIELDS.has(key) ? 'digest' as const : 'default' as const,
    }));

  const promptPayloadOmitted = Boolean(runMetrics && PROMPT_PAYLOAD_KEY in runMetrics);
  const rawRunMetrics = runMetrics
    ? Object.fromEntries(
        Object.entries(runMetrics).filter(([key]) => key !== PROMPT_PAYLOAD_KEY),
      ) as Record<string, NormalizedArtifactValue>
    : null;

  return {
    configuration,
    operational,
    timing,
    advanced,
    rawRunMetrics,
    promptPayloadOmitted,
    hasMetadata: merged.size > 0,
  };
}

export function shortenDigest(value: unknown, edgeLength = 14): string {
  const text = String(value ?? '').trim();
  if (text.length <= edgeLength * 2 + 1) return text;
  return `${text.slice(0, edgeLength)}…${text.slice(-edgeLength)}`;
}

function asRecord(value: unknown): Record<string, NormalizedArtifactValue> | null {
  const normalized = normalizeArtifactValue(value);
  if (!normalized || Array.isArray(normalized) || typeof normalized !== 'object') return null;
  return normalized;
}

function numericArray(value: unknown): number[] {
  const normalized = normalizeArtifactValue(value);
  if (!Array.isArray(normalized)) return [];
  return normalized
    .map((item) => asFiniteNumber(item))
    .filter((item): item is number => item !== null)
    .sort((left, right) => left - right);
}

function asFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function percentile(sortedSamples: number[], fraction: number): number {
  if (sortedSamples.length === 1) return sortedSamples[0];
  const position = (sortedSamples.length - 1) * fraction;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sortedSamples[lower];
  const weight = position - lower;
  return sortedSamples[lower] + (sortedSamples[upper] - sortedSamples[lower]) * weight;
}

function humanizeKey(value: string): string {
  return value.replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}
