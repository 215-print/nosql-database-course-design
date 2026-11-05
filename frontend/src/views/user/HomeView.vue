<script setup lang="ts">
import { useMessageState } from '../../composables/useMessageState';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import EmptyState from '../../components/EmptyState.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import { getUserPackages, pickupPackage } from '../../api/packages';
import { useSession } from '../../composables/useSession';
import {
  errorText,
  formatAppointment,
  formatDate,
  formatDuration,
  isTrue,
  maskPhone,
} from '../../utils/format';
import type { PackageRecord } from '../../types/api';

const { user } = useSession();
const packages = ref<PackageRecord[]>([]);
const loading = ref(true);
const submittingId = ref('');
const error = useMessageState('error');
const success = useMessageState('success');
const pickupError = useMessageState('error');
const tab = ref<'waiting' | 'received' | 'shipments'>('waiting');
const received = computed(() => packages.value.filter((p) => p.direction === '收件'));
const waiting = computed(() => received.value.filter((p) => p.status === '待取件'));
const overdue = computed(() => waiting.value.filter((p) => p.overdue));
const overdueDays = computed(() => Math.ceil((overdue.value[0]?.overdue_hours || 168) / 24));
let timer: ReturnType<typeof setInterval> | undefined;
let generation = 0;
const shipments = computed(() => packages.value.filter((p) => p.direction === '寄件'));
const visible = computed(() =>
  [
    ...(tab.value === 'waiting'
      ? waiting.value
      : tab.value === 'received'
        ? received.value
        : shipments.value),
  ].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
);
async function load(silent = false) {
  if (silent && (loading.value || submittingId.value)) return;
  const current = ++generation;
  error.value = '';
  if (!silent) loading.value = true;
  try {
    if (!user.value.id) throw new Error('未获取到用户信息，请重新登录');
    const items = await getUserPackages(user.value.id);
    if (current !== generation) return;
    packages.value = items;
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}
async function pickup(item: PackageRecord) {
  if (submittingId.value) return;
  pickupError.value = '';
  success.value = '';
  if (isTrue(item.abnormal) || item.status === '异常') {
    pickupError.value = '请到快递站与快递员对接包裹详情';
    return;
  }
  if (item.direction !== '收件' || item.status !== '待取件') {
    pickupError.value = '该快递当前不可自主取件';
    return;
  }
  if (!item.pickup_code) {
    pickupError.value = '未获取到该快递的取件信息，请刷新后重试';
    return;
  }
  submittingId.value = item.id;
  generation++;
  try {
    await pickupPackage(item.pickup_code);
    success.value = '取件成功，快递状态已更新。';
    await load();
  } catch (e) {
    pickupError.value = errorText(e);
  } finally {
    submittingId.value = '';
  }
}
onMounted(() => {
  void load();
  timer = setInterval(() => load(true), 15000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <PageHeader
    :title="`你好，${user.name || user.username || '同学'}`"
    description="查收校园里的每一份期待。"
    eyebrow="我的驿站"
    ><el-button :loading="loading" @click="load()"
      ><AppIcon name="refresh-cw" :size="16" />刷新快递</el-button
    ></PageHeader
  >

  <el-alert
    v-if="overdue.length && !error"
    class="mb-5"
    type="warning"
    :closable="false"
    :title="`有 ${overdue.length} 件快递已逾期未取，请尽快领取`"
    :description="`收件入库超过 ${overdueDays} 天仍未领取时自动提醒，请尽快领取。`"
  />
  <div class="user-overview">
    <section class="pickup-hero">
      <div>
        <p class="hero-label">等待你领取的快递</p>
        <div class="hero-count">
          <strong>{{ loading || error ? '—' : waiting.length }}</strong
          ><span>件待取</span>
        </div>
        <p class="hero-note">
          {{
            !loading && !error && waiting.some((p) => isTrue(p.is_large))
              ? '有大件快递待领取，请提前做好搬运准备。'
              : '登录后可查看取件码及包裹属性。'
          }}
        </p>
      </div>
      <div class="hero-art" aria-hidden="true"><AppIcon name="package" :size="58" /></div>
    </section>
    <section class="service-entry">
      <AppIcon name="send" :size="28" class="text-brand" />
      <div>
        <h2>有快递要寄？</h2>
        <p>在线填写收寄信息，<br class="hidden md:block" />向驿站提交寄件申请。</p>
      </div>
      <router-link class="text-link" to="/user/shipment"
        ><span class="entry-label">填写寄件申请</span><AppIcon name="arrow-right" :size="18"
      /></router-link>
    </section>
  </div>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">我的快递</h2>
        <p class="panel-description">关联手机号 {{ maskPhone(user.phone) }}</p>
      </div>
      <router-link class="text-link" to="/user/records"
        >取件记录<AppIcon name="arrow-right" :size="15"
      /></router-link>
    </div>
    <div class="tabs-row" role="group" aria-label="快递分类">
      <button
        :class="{ selected: tab === 'waiting' }"
        :aria-pressed="tab === 'waiting'"
        @click="tab = 'waiting'"
      >
        待取件<small>{{ loading || error ? '—' : waiting.length }}</small></button
      ><button
        :class="{ selected: tab === 'received' }"
        :aria-pressed="tab === 'received'"
        @click="tab = 'received'"
      >
        全部收件<small>{{ loading || error ? '—' : received.length }}</small></button
      ><button
        :class="{ selected: tab === 'shipments' }"
        :aria-pressed="tab === 'shipments'"
        @click="tab = 'shipments'"
      >
        我的寄件<small>{{ loading || error ? '—' : shipments.length }}</small>
      </button>
    </div>
    <div v-if="loading" class="panel-body" aria-busy="true"><el-skeleton :rows="6" animated /></div>
    <EmptyState
      v-else-if="error"
      title="快递暂时没有加载成功"
      description="请稍后重试，或重新登录后查看。"
      ><el-button @click="load()">重新加载</el-button></EmptyState
    >
    <template v-else-if="visible.length"
      ><article v-for="item in visible" :key="item.id" class="record-row">
        <div class="flex min-w-0 items-start gap-3">
          <span class="row-icon"
            ><AppIcon :name="tab === 'shipments' ? 'truck' : 'package'"
          /></span>
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <strong>{{
                item.company || (item.direction === '寄件' ? '寄件申请' : '快递')
              }}</strong
              ><StatusBadge :status="item.status" :abnormal="item.abnormal" /><span
                v-if="isTrue(item.is_large)"
                class="muted text-[10px]"
                >大件物品</span
              ><span v-if="isTrue(item.is_fragile)" class="muted text-[10px]">易碎物品</span
              ><span v-if="isTrue(item.is_fresh)" class="muted text-[10px]">生鲜冷冻</span>
            </div>
            <p v-if="item.tracking_number" class="font-mono">运单号 {{ item.tracking_number }}</p>
            <p v-if="item.direction === '寄件'">
              {{ item.receiver_name }} · {{ item.receiver_address }}
            </p>
            <p v-if="item.direction === '收件'">
              入库时间：{{ formatDate(item.inbound_at || item.created_at) }}
            </p>
            <p v-if="item.direction === '寄件'">
              预约到站：{{
                formatAppointment(item.appointment_date, item.appointment_slot, item.appointment_at)
              }}
            </p>
            <p
              v-if="item.direction === '寄件' && item.shipment_code"
              class="bg-brand/5 text-brand mt-2 inline-flex rounded-md px-3 py-1 font-mono font-bold tracking-widest"
            >
              寄件码 {{ item.shipment_code }}
            </p>
            <p v-if="item.direction === '寄件' && item.status === '待揽收' && !item.shipment_code">
              已于 {{ formatDate(item.inbound_at || item.created_at) }} 收件入站，等待快递员揽收
            </p>
            <p v-if="item.direction === '收件' && item.status === '已取件'">
              出库时间：{{ formatDate(item.picked_at) }}
            </p>
            <p v-if="item.overdue" class="text-amber-700">
              逾期未取 · 已滞留 {{ formatDuration(item.waiting_seconds) }}
            </p>
            <p
              v-if="item.direction === '收件' && (isTrue(item.abnormal) || item.status === '异常')"
              class="mt-2 text-sm font-medium"
              style="color: var(--danger)"
            >
              请到快递站与快递员对接包裹详情
            </p>
            <p
              v-if="
                item.direction === '收件' &&
                item.status === '待取件' &&
                item.pickup_code &&
                !isTrue(item.abnormal)
              "
              class="bg-brand/5 text-brand mt-2 inline-flex rounded-lg px-3 py-2 font-mono text-xl font-bold tracking-widest md:text-2xl"
            >
              取件码 {{ item.pickup_code }}
            </p>
          </div>
        </div>
        <div
          v-if="item.direction === '收件' && item.status === '待取件' && !isTrue(item.abnormal)"
          class="flex shrink-0 flex-wrap gap-2"
        >
          <el-button
            plain
            type="primary"
            :loading="submittingId === item.id"
            :disabled="!!submittingId"
            @click="pickup(item)"
            >自主取件<AppIcon name="arrow-right" :size="15"
          /></el-button>
        </div></article
    ></template>
    <EmptyState
      v-else
      :title="
        tab === 'waiting'
          ? '暂时没有待取快递'
          : tab === 'shipments'
            ? '还没有寄件申请'
            : '暂时没有收件快递'
      "
      :description="
        tab === 'shipments'
          ? '填写收寄信息，即可向驿站提交申请。'
          : '快递入库后，会在这里显示最新状态。'
      "
      ><el-button
        v-if="tab === 'shipments'"
        type="primary"
        plain
        @click="$router.push('/user/shipment')"
        >填写寄件申请</el-button
      ></EmptyState
    >
  </section>
</template>
