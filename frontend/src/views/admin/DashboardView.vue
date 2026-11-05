<script setup lang="ts">
import { useMessageState } from '../../composables/useMessageState';
import { computed, onMounted, ref } from 'vue';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import EmptyState from '../../components/EmptyState.vue';
import StatCard from '../../components/StatCard.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import { getPackages } from '../../api/packages';
import type { PackageRecord } from '../../types/api';
import { errorText, formatDate, isTrue } from '../../utils/format';

const packages = ref<PackageRecord[]>([]);
const loading = ref(true);
const error = useMessageState('error');
const statistics = computed(() => ({
  waiting: packages.value.filter((p) => p.direction === '收件' && p.status === '待取件').length,
  abnormal: packages.value.filter((p) => isTrue(p.abnormal) || p.status === '异常').length,
  total: packages.value.length,
  picked: packages.value.filter((p) => p.status === '已取件').length,
}));
const recent = computed(() =>
  [...packages.value]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 6)
);
async function load() {
  loading.value = true;
  error.value = '';
  try {
    packages.value = await getPackages();
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <PageHeader
    title="运营概览"
    description="从这里开始，安排好驿站的日常工作。"
    eyebrow="驿站工作空间"
  >
    <el-button :loading="loading" @click="load"
      ><AppIcon name="refresh-cw" :size="16" />刷新数据</el-button
    >
    <el-button type="primary" @click="$router.push('/admin/intake')"
      ><AppIcon name="plus" :size="17" />快递入库</el-button
    >
  </PageHeader>

  <div class="stats-grid" :aria-busy="loading">
    <StatCard
      label="待取件"
      :value="loading || error ? '—' : statistics.waiting"
      icon="clock-3"
      note="待用户领取的收件快递"
      tone="brand"
    />
    <StatCard
      label="异常快递"
      :value="loading || error ? '—' : statistics.abnormal"
      icon="triangle-alert"
      note="需要工作人员核对处理"
      tone="warning"
    />
    <StatCard
      label="快递总数"
      :value="loading || error ? '—' : statistics.total"
      icon="package"
      note="全部快递列表中的记录"
    />
    <StatCard
      label="已完成取件"
      :value="loading || error ? '—' : statistics.picked"
      icon="check-check"
      note="状态为已取件的快递"
    />
  </div>
  <div class="two-column">
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">最近入库</h2>
          <p class="panel-description">按录入时间排列的最近 6 条快递</p>
        </div>
        <router-link class="text-link" to="/admin/packages"
          >查看全部<AppIcon name="arrow-right" :size="15"
        /></router-link>
      </div>
      <div v-if="loading" class="panel-body"><el-skeleton :rows="7" animated /></div>
      <template v-else-if="recent.length && !error"
        ><article v-for="item in recent" :key="item.id" class="record-row">
          <div class="flex min-w-0 items-center gap-3">
            <span class="row-icon"><AppIcon name="package" /></span>
            <div class="min-w-0">
              <strong
                >{{ item.company || '快递' }}
                <span class="muted text-xs font-normal">· {{ item.receiver_name }}</span></strong
              >
              <p class="font-mono">{{ item.tracking_number || item.package_code }}</p>
            </div>
          </div>
          <div class="shrink-0 text-right">
            <StatusBadge :status="item.status" :abnormal="item.abnormal" />
            <p>{{ formatDate(item.created_at) }}</p>
          </div>
        </article></template
      >
      <EmptyState
        v-else
        :title="error ? '快递数据加载失败' : '还没有入库记录'"
        :description="error ? '请刷新数据后重试。' : '登记第一份快递，开始使用驿站工作台。'"
      />
    </section>
    <div class="grid gap-5">
      <section class="panel">
        <div class="panel-header"><h2 class="panel-title">常用工作</h2></div>
        <router-link class="action-tile" to="/admin/intake"
          ><span class="tile-icon"><AppIcon name="package-plus" /></span>
          <div>
            <strong>核验寄件码 / 登记快递</strong>
            <p>核对预约订单并收件入站</p>
          </div>
          <AppIcon name="chevron-right" :size="16"
        /></router-link>
        <router-link class="action-tile" to="/admin/waiting"
          ><span class="tile-icon"><AppIcon name="search" /></span>
          <div>
            <strong>查询待取件</strong>
            <p>通过单号或手机尾号定位</p>
          </div>
          <AppIcon name="chevron-right" :size="16"
        /></router-link>
        <router-link class="action-tile" to="/admin/abnormal"
          ><span class="tile-icon"><AppIcon name="triangle-alert" /></span>
          <div>
            <strong>处理异常快递</strong>
            <p>核对需要关注的快递</p>
          </div>
          <AppIcon name="chevron-right" :size="16"
        /></router-link>
      </section>
      <aside class="soft-note">
        <h3 class="flex items-center gap-2"><AppIcon name="shield-check" :size="18" />统计范围</h3>
        <p class="muted text-xs leading-6">
          统计根据当前返回的全部快递列表计算，刷新后同步最新状态。
        </p>
      </aside>
    </div>
  </div>
</template>
