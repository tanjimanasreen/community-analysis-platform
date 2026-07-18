export function clampPageOffset(offset: number, total: number, limit: number): number {
  const safeLimit = Math.max(1, Math.floor(limit));
  const safeTotal = Math.max(0, Math.floor(total));
  if (safeTotal === 0) return 0;
  const lastOffset = Math.floor((safeTotal - 1) / safeLimit) * safeLimit;
  return Math.min(Math.max(0, Math.floor(offset)), lastOffset);
}

export function nextPageOffset(offset: number, total: number, limit: number): number {
  return clampPageOffset(offset + Math.max(1, limit), total, limit);
}

export function previousPageOffset(offset: number, limit: number): number {
  return Math.max(0, offset - Math.max(1, limit));
}

export function pageRange(offset: number, limit: number, total: number): string {
  if (total <= 0) return '0 records';
  const start = Math.min(offset + 1, total);
  const end = Math.min(offset + limit, total);
  return `${start}–${end} of ${total}`;
}
