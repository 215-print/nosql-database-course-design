import axios from 'axios';

export const isTrue = (value: unknown) =>
  value === true || value === 1 || value === 'true' || value === '1';
export function formatDate(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      });
}
export function formatAppointment(
  date?: string | null,
  slot?: string | null,
  legacyDateTime?: string | null
) {
  if (date && slot) {
    const parsed = new Date(`${date}T00:00:00`);
    const dateText = Number.isNaN(parsed.getTime())
      ? date
      : parsed.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
    return `${dateText} ${slot}`;
  }
  return formatDate(legacyDateTime);
}
export function maskPhone(phone?: string) {
  return phone?.length === 11 ? `${phone.slice(0, 3)}****${phone.slice(-4)}` : phone || '—';
}
export function formatDuration(seconds = 0) {
  const hours = Math.floor(Math.max(0, seconds) / 3600);
  return hours >= 24 ? `${Math.floor(hours / 24)} 天 ${hours % 24} 小时` : `${hours} 小时`;
}
export function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (Array.isArray(detail))
      return detail.map((item: { msg?: string }) => item.msg || String(item)).join('；');
    return String(
      detail || error.response?.data?.message || error.message || '操作失败，请稍后重试'
    );
  }
  return error instanceof Error ? error.message : '操作失败，请稍后重试';
}
export function normalizeList<T>(result: unknown, key: string): T[] {
  if (Array.isArray(result)) return result as T[];
  if (!result || typeof result !== 'object') return [];
  const root = result as Record<string, unknown>;
  if (Array.isArray(root[key])) return root[key] as T[];
  if (Array.isArray(root.data)) return root.data as T[];
  if (
    root.data &&
    typeof root.data === 'object' &&
    Array.isArray((root.data as Record<string, unknown>)[key])
  )
    return (root.data as Record<string, unknown>)[key] as T[];
  return [];
}
