<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import PageHeader from '../../components/PageHeader.vue';
import EmptyState from '../../components/EmptyState.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import {
  getRetainedPackages,
  getStatistics,
  getUserPackageRank,
  getWaitingRank,
} from '../../api/operations';
import type {
  PackageRecord,
  PackageStatistics,
  RetainedPackages,
  UserPackageRank,
} from '../../types/api';
import { errorText, formatDate, formatDuration } from '../../utils/format';
import { useMessageState } from '../../composables/useMessageState';

const loading = ref(false);
const error = useMessageState('error');
const minHours = ref(72);
const page = ref(1);
const statistics = ref<PackageStatistics>();
const waitingRank = ref<PackageRecord[]>([]);
const userRank = ref<UserPackageRank[]>([]);
const retained = ref<RetainedPackages>({ packages: [], total: 0, overdue_hours: 168 });
const overdueDays = computed(() => Math.ceil((retained.value.overdue_hours || 168) / 24));
const states = [
  { key: 'waiting', title: '待取件' },
  { key: 'picked', title: '已取件' },
  { key: 'waiting_shipment', title: '待揽收' },
  { key: 'abnormal', title: '异常件（含标记）' },
  { key: 'total', title: '全部包裹' },
] as const;
async function load() {
  if (loading.value) return;
  loading.value = true;
  error.value = '';
  try {
    const [stats, waiting, users, overdue] = await Promise.all([
      getStatistics(),
      getWaitingRank(),
      getUserPackageRank(),
      getRetainedPackages(minHours.value, (page.value - 1) * 20),
    ]);
    statistics.value = stats;
    waitingRank.value = waiting;
    userRank.value = users;
    retained.value = overdue;
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}
function search() {
  page.value = 1;
  void load();
}
onMounted(load);
</script>

<template>
  <PageHeader title="统计与滞留" description="查看包裹状态、滞留情况和用户包裹数量排行。">
    <el-button :loading="loading" @click="load">刷新数据</el-button>
  </PageHeader>
  <el-alert v-if="error" :title="error" type="error" :closable="false" class="mb-5" />
  <section class="panel mb-5">
    <div class="panel-header">
      <h2 class="panel-title">包裹状态统计</h2>
      <span class="muted text-xs">异常标记可能与其他状态重叠</span>
    </div>
    <div class="panel-body grid grid-cols-2 gap-5 md:grid-cols-3">
      <div v-for="state in states" :key="state.key">
        <p class="muted text-xs">{{ state.title }}</p>
        <strong class="text-2xl">{{ loading ? '—' : (statistics?.[state.key] ?? '—') }}</strong>
      </div>
    </div>
  </section>
  <section class="panel mb-5">
    <div class="panel-header flex-wrap gap-4">
      <div>
        <h2 class="panel-title">滞留包裹查询</h2>
        <p class="panel-description">
          收件且仍待取件；用户端对入库超过 {{ overdueDays }} 天的包裹自动显示逾期提醒。
        </p>
      </div>
      <form class="flex flex-wrap items-center gap-3" @submit.prevent="search">
        <label for="retained-hours">滞留至少（小时）</label
        ><el-input-number
          id="retained-hours"
          v-model="minHours"
          :min="0"
          :max="87600"
          :precision="0"
          :disabled="loading"
        /><el-button native-type="submit" type="primary" :loading="loading">查询</el-button>
      </form>
    </div>
    <div v-if="loading" class="panel-body"><el-skeleton :rows="4" animated /></div>
    <template v-else>
      <article v-for="item in retained.packages" :key="item.id" class="record-row">
        <div class="min-w-0">
          <strong>{{ item.receiver_name }} · {{ item.phone }}</strong>
          <p class="break-all">
            {{ item.company }} · {{ item.tracking_number || item.package_code }}
          </p>
          <p>入库 {{ formatDate(item.created_at) }}</p>
        </div>
        <div class="shrink-0 text-right">
          <strong class="text-sm">{{ formatDuration(item.waiting_seconds) }}</strong>
          <p><StatusBadge :status="item.status" :abnormal="item.abnormal" /></p>
        </div>
      </article>
      <EmptyState
        v-if="!retained.packages.length"
        :title="error ? '数据加载失败' : '没有符合条件的滞留包裹'"
        description="可调整滞留时长后重新查询。"
      />
      <div class="table-footer">
        <span>共 {{ retained.total }} 件</span
        ><el-pagination
          v-model:current-page="page"
          :page-size="20"
          :total="retained.total"
          layout="prev, pager, next"
          :disabled="loading"
          @current-change="load"
        />
      </div>
    </template>
  </section>
  <div class="two-column">
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">滞留时长前 10 名</h2>
          <p class="panel-description">按入库时间从早到晚排列的待取收件</p>
        </div>
      </div>
      <article v-for="(item, index) in waitingRank" :key="item.id" class="record-row">
        <div class="min-w-0">
          <strong>{{ index + 1 }}. {{ item.receiver_name }}</strong>
          <p class="break-all">{{ item.tracking_number || item.package_code }}</p>
        </div>
        <span class="shrink-0 text-sm">{{ formatDuration(item.waiting_seconds) }}</span>
      </article>
      <EmptyState
        v-if="!waitingRank.length && !loading"
        title="暂无待取包裹"
        description="收件入库后将在这里显示。"
      />
    </section>
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">用户包裹数量前 10 名</h2>
          <p class="panel-description">按手机号统计现存包裹，包含收件和寄件，删除后扣减</p>
        </div>
      </div>
      <article v-for="(item, index) in userRank" :key="item.phone" class="record-row">
        <div>
          <strong>{{ index + 1 }}. {{ item.name }}</strong>
          <p>{{ item.phone }}</p>
        </div>
        <span class="shrink-0 text-sm">{{ item.package_count }} 件</span>
      </article>
      <EmptyState
        v-if="!userRank.length && !loading"
        title="暂无包裹数据"
        description="登记包裹后自动统计。"
      />
    </section>
  </div>
</template>
