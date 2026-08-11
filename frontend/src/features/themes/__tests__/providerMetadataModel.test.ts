import { describe, expect, it } from 'vitest';
import { buildProviderMetadataViewModel, shortenDigest } from '../providerMetadataModel';

describe('providerMetadataModel', () => {
  it('partitions configuration, operational metrics, timing summaries, and advanced provenance', () => {
    const samples = Array.from({ length: 100 }, (_, index) => index + 1);
    const model = buildProviderMetadataViewModel({
      configured_primary_provider: 'openai:gpt-5-nano',
      configured_primary_model: 'gpt-5-nano',
      configured_fallback_chain: 'llm7:gpt-oss:20b',
      prompt_version: 'v1',
      semantic_task_version: '1.2.0',
      schema_version: '1.0',
      provider_config_digest: 'a'.repeat(64),
      generation_settings_digest: 'b'.repeat(64),
      extra_future_field: { enabled: true },
      run_metrics: {
        logical_theme_requests: 281,
        calls: 281,
        outbound_requests: 281,
        cache_hits: 456,
        cache_misses: 281,
        cache_writes: 281,
        cache_errors: 0,
        fallback_attempts: 0,
        total_prompt_tokens: 12345,
        total_completion_tokens: 6789,
        total_cost: 1.2345,
        latency_ms_list: samples,
        ttft_ms_list: samples.map((value) => value * 2),
        tpot_ms_list: samples.map((value) => value / 2),
        prompts_and_responses: [{ system_prompt: 'do not render me' }],
      },
    }, null);

    expect(model.configuration.map((item) => item.key)).toEqual([
      'configured_primary_provider',
      'configured_primary_model',
      'configured_fallback_chain',
      'prompt_version',
      'semantic_task_version',
      'schema_version',
    ]);
    expect(model.operational.find((item) => item.key === 'cache_hits')?.value).toBe(456);
    expect(model.timing.find((item) => item.key === 'latency_ms_list')).toMatchObject({
      sampleCount: 100,
      p50Ms: 50.5,
      p95Ms: 95.05,
    });
    expect(model.advanced.map((item) => item.key)).toEqual([
      'provider_config_digest',
      'generation_settings_digest',
      'extra_future_field',
    ]);
    expect(model.promptPayloadOmitted).toBe(true);
    expect(model.rawRunMetrics).not.toHaveProperty('prompts_and_responses');
    expect(model.rawRunMetrics?.latency_ms_list).toHaveLength(100);
  });

  it('ignores malformed timing samples and does not fabricate unavailable summaries', () => {
    const model = buildProviderMetadataViewModel({
      run_metrics: {
        calls: '2',
        latency_ms_list: [100, '200', null, 'bad', Number.NaN],
        ttft_ms_list: [],
        tpot_ms_list: 'not-an-array',
      },
    }, null);

    expect(model.operational.find((item) => item.key === 'calls')?.value).toBe(2);
    expect(model.timing).toHaveLength(1);
    expect(model.timing[0]).toMatchObject({ sampleCount: 2, p50Ms: 150, p95Ms: 195 });
  });

  it('falls back to model metadata without overwriting provider metadata', () => {
    const model = buildProviderMetadataViewModel(
      { configured_primary_model: 'provider-model' },
      { configured_primary_model: 'overview-model', schema_version: '2.0' },
    );

    expect(model.configuration.find((item) => item.key === 'configured_primary_model')?.value).toBe('provider-model');
    expect(model.configuration.find((item) => item.key === 'schema_version')?.value).toBe('2.0');
  });

  it('shortens long digests without changing short values', () => {
    const digest = '0123456789abcdef'.repeat(4);
    expect(shortenDigest(digest)).toBe('0123456789abcd…23456789abcdef');
    expect(shortenDigest('short')).toBe('short');
  });
});
