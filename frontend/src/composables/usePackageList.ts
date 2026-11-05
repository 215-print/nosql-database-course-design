import axios from 'axios';
import { ElMessageBox } from 'element-plus';
import 'element-plus/es/components/message-box/style/css';
import { computed, ref, watch, type Ref } from 'vue';
import {
  deletePackage,
  getPackageByTrackingNumber,
  getPackages,
  getPackagesByPhone,
  updatePackage,
} from '../api/packages';
import type { PackageRecord, PackageStatus } from '../types/api';
import { errorText, isTrue } from '../utils/format';
import { useMessageState } from './useMessageState';

export type PackageScope = 'all' | 'waiting' | 'abnormal';
export function usePackageList(scope: Readonly<Ref<PackageScope>>) {
  const packages = ref<PackageRecord[]>([]);
  const loading = ref(false);
  const searching = ref(false);
  const busyId = ref('');
  const error = useMessageState('error');
  const success = useMessageState('success');
  const keyword = ref('');
  const status = ref<PackageStatus | '全部'>('全部');
  const result = ref<PackageRecord[] | null>(null);
  const searched = ref(false);
  const page = ref(1);
  const pageSize = 10;
  let generation = 0;
  const isAbnormal = (p: PackageRecord) => isTrue(p.abnormal) || p.status === '异常';
  const filtered = computed(() => {
    const query = keyword.value.trim().toLowerCase();
    return (result.value ?? packages.value).filter((p) => {
      if (scope.value === 'abnormal' && !isAbnormal(p)) return false;
      if (
        scope.value === 'all' &&
        status.value !== '全部' &&
        !(status.value === '异常' ? isAbnormal(p) : p.status === status.value)
      )
        return false;
      if (result.value !== null || !query) return true;
      const phones = [p.phone, p.receiver_phone, p.sender_phone].map((v) => String(v || ''));
      if (scope.value === 'waiting' && /^\d{4}$/.test(query))
        return phones.some((v) => v.endsWith(query));
      return [
        p.tracking_number,
        p.receiver_name,
        ...(scope.value === 'waiting' ? [] : [p.company]),
        ...phones,
      ].some((v) =>
        String(v || '')
          .toLowerCase()
          .includes(query)
      );
    });
  });
  const visible = computed(() =>
    filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize)
  );
  watch(keyword, () => {
    generation++;
    result.value = null;
    searched.value = false;
    page.value = 1;
    success.value = '';
    error.value = '';
  });
  watch(status, () => {
    page.value = 1;
  });
  watch(
    () => filtered.value.length,
    (length) => {
      page.value = Math.min(page.value, Math.max(1, Math.ceil(length / pageSize)));
    }
  );
  async function load(clear = true) {
    if (scope.value === 'waiting') {
      if (keyword.value.trim()) await search();
      else {
        packages.value = [];
        result.value = null;
        if (clear) error.value = '';
      }
      return;
    }
    loading.value = true;
    if (clear) {
      error.value = '';
      success.value = '';
    }
    try {
      packages.value = await getPackages();
      if (clear && result.value !== null) await search();
    } catch (e) {
      error.value = errorText(e);
    } finally {
      loading.value = false;
    }
  }
  function reset() {
    keyword.value = '';
    status.value = '全部';
    result.value = null;
    searched.value = false;
    error.value = '';
    success.value = '';
    page.value = 1;
    generation++;
  }
  async function search() {
    error.value = '';
    success.value = '';
    const value = keyword.value.trim();
    if (!value) {
      error.value = '请输入查询内容';
      return;
    }
    searched.value = true;
    page.value = 1;
    if (scope.value === 'waiting') {
      searching.value = true;
      try {
        if (/^\d{4}$|^1\d{10}$/.test(value)) {
          const response = await getPackagesByPhone(value);
          result.value = response.filter((item) => item.direction === '收件');
        } else {
          const item = await getPackageByTrackingNumber(value);
          result.value = item.direction === '收件' ? [item] : [];
        }
      } catch (e) {
        if (axios.isAxiosError(e) && e.response?.status === 404) {
          result.value = [];
        } else {
          error.value = errorText(e);
          result.value = [];
        }
      } finally {
        searching.value = false;
      }
    }
  }
  async function act(item: PackageRecord, action: 'abnormal' | 'delete') {
    if (busyId.value) return;
    const next = !isAbnormal(item);
    try {
      await ElMessageBox.confirm(
        action === 'delete'
          ? `确认删除运单 ${item.tracking_number || item.package_code}？此操作不可撤销。`
          : `确认${next ? '标记该快递为异常件' : '取消该快递的异常标记'}？`,
        action === 'delete' ? '删除快递记录' : '更新异常状态',
        { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' }
      );
    } catch {
      return;
    }
    busyId.value = item.id;
    error.value = '';
    success.value = '';
    try {
      if (action === 'delete') await deletePackage(item.id);
      else
        await updatePackage(item.id, {
          abnormal: next,
          ...(!next && item.status === '异常'
            ? {
                status:
                  item.direction === '收件'
                    ? ('待取件' as const)
                    : ('待揽收' as const),
              }
            : {}),
        });
      if (action === 'delete') {
        await load();
        if (error.value) throw new Error(`快递已删除，但列表刷新失败：${error.value}`);
        packages.value = packages.value.filter((p) => p.id !== item.id);
        if (result.value) result.value = result.value.filter((p) => p.id !== item.id);
      } else {
        await load(false);
        if (result.value)
          result.value = result.value.map((p) =>
            p.id === item.id
              ? packages.value.find((v) => v.id === p.id) || { ...p, abnormal: next }
              : p
          );
      }
      success.value =
        action === 'delete' ? '快递记录已删除' : next ? '已标记为异常件' : '已取消异常标记';
    } catch (e) {
      error.value = errorText(e);
    } finally {
      busyId.value = '';
    }
  }
  watch(
    scope,
    async () => {
      reset();
      if (scope.value !== 'waiting') await load();
    },
    { immediate: true }
  );
  return {
    loading,
    searching,
    busyId,
    error,
    success,
    keyword,
    status,
    searched,
    page,
    pageSize,
    filtered,
    visible,
    load,
    reset,
    search,
    act,
    isAbnormal,
  };
}
