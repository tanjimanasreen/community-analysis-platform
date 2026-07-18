export type NormalizedArtifactValue =
  | null
  | string
  | number
  | boolean
  | NormalizedArtifactValue[]
  | { [key: string]: NormalizedArtifactValue };

function shouldParseJsonString(value: string): boolean {
  const trimmed = value.trim();
  return (
    trimmed.startsWith('[') ||
    trimmed.startsWith('{') ||
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    trimmed === 'null' ||
    trimmed === 'true' ||
    trimmed === 'false'
  );
}

/**
 * Normalizes API artifact values without executing serialized content.
 * Only unambiguous JSON strings are parsed. Python literals and any other
 * non-JSON serialization remain visible as their original text.
 */
export function normalizeArtifactValue(value: unknown): NormalizedArtifactValue {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'boolean') return value;

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return '';
    if (!shouldParseJsonString(trimmed)) return value;
    try {
      return normalizeArtifactValue(JSON.parse(trimmed));
    } catch {
      return value;
    }
  }

  if (Array.isArray(value)) {
    return value.map((item) => normalizeArtifactValue(item));
  }

  if (typeof value === 'object') {
    const normalized: Record<string, NormalizedArtifactValue> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      normalized[key] = normalizeArtifactValue(item);
    }
    return normalized;
  }

  return String(value);
}

export function normalizedTextList(
  value: unknown,
  objectMode: 'keys' | 'values' = 'keys',
): string[] {
  const normalized = normalizeArtifactValue(value);
  const result: string[] = [];

  const visit = (item: NormalizedArtifactValue): void => {
    if (item === null) return;
    if (typeof item === 'string') {
      const text = item.trim();
      if (text) result.push(text);
      return;
    }
    if (typeof item === 'number' || typeof item === 'boolean') {
      result.push(String(item));
      return;
    }
    if (Array.isArray(item)) {
      item.forEach(visit);
      return;
    }
    if (objectMode === 'keys') {
      Object.keys(item).forEach((key) => {
        if (key.trim()) result.push(key.trim());
      });
    } else {
      Object.values(item).forEach(visit);
    }
  };

  visit(normalized);
  return [...new Set(result)];
}

export function displayArtifactValue(value: unknown): string {
  const normalized = normalizeArtifactValue(value);
  if (normalized === null) return 'Unavailable';
  if (typeof normalized === 'string') return normalized || '—';
  if (typeof normalized === 'number') {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(normalized);
  }
  if (typeof normalized === 'boolean') return normalized ? 'Yes' : 'No';
  if (Array.isArray(normalized)) {
    return normalized.length > 0
      ? normalized.map((item) => displayArtifactValue(item)).join(', ')
      : '—';
  }
  return JSON.stringify(normalized, null, 2);
}
