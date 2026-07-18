import { describe, expect, it, vi } from 'vitest';
import {
  displayArtifactValue,
  normalizeArtifactValue,
  normalizedTextList,
} from '../artifactValues';

describe('artifact value normalization', () => {
  it('normalizes arrays, maps, scalars, and unambiguous JSON strings', () => {
    expect(normalizeArtifactValue('["alpha", {"beta": 2}]')).toEqual([
      'alpha',
      { beta: 2 },
    ]);
    expect(normalizeArtifactValue({ active: true, value: null })).toEqual({
      active: true,
      value: null,
    });
    expect(normalizedTextList({ Policy: ['alpha'] })).toEqual(['Policy']);
    expect(normalizedTextList({ Policy: ['alpha'] }, 'values')).toEqual(['alpha']);
  });

  it('preserves non-JSON serialized values without evaluating them', () => {
    const evalSpy = vi.spyOn(globalThis, 'eval');
    const pythonLiteral = "['alpha', 'beta']";
    expect(normalizeArtifactValue(pythonLiteral)).toBe(pythonLiteral);
    expect(displayArtifactValue(pythonLiteral)).toBe(pythonLiteral);
    expect(evalSpy).not.toHaveBeenCalled();
    evalSpy.mockRestore();
  });

  it('renders nulls and nested values safely', () => {
    expect(displayArtifactValue(null)).toBe('Unavailable');
    expect(displayArtifactValue(['alpha', 2, false])).toBe('alpha, 2, No');
  });
});
