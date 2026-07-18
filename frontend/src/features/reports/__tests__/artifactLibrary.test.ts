import { describe, expect, it } from 'vitest';
import type { ArtifactMetadata } from '../../../types/api';
import { filterArtifacts, hasInlineReport, isDownloadableArtifact } from '../artifactLibrary';

const artifact = (overrides: Partial<ArtifactMetadata>): ArtifactMetadata => ({
  key: 'network_data', path: 'data/network.csv', category: 'data', media_type: 'text/csv',
  schema_version: '1', sha256: 'a'.repeat(64), rows: 1, byte_size: 10, stage: 'network', ...overrides,
});

describe('artifact library', () => {
  it('filters real metadata and suppresses intermediate downloads', () => {
    const records = [artifact({}), artifact({ key: 'temp', path: 'intermediate/temp.csv', category: 'intermediate', stage: 'topic' })];
    expect(filterArtifacts(records, { query: 'network', category: '', stage: '', mediaType: '' })).toHaveLength(1);
    expect(isDownloadableArtifact(records[1])).toBe(false);
  });

  it('recognizes only manifest-listed HTML reports for inline opening', () => {
    expect(hasInlineReport([artifact({ key: 'report_html', path: 'reports/report.html', category: 'report', media_type: 'text/html' })])).toBe(true);
  });
});
