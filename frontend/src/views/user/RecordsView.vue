<script setup lang="ts">
import { useMessageState } from '../../composables/useMessageState';
import { onMounted, ref } from 'vue';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import EmptyState from '../../components/EmptyState.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import { getUserPickupRecords } from '../../api/packages';
import { useSession } from '../../composables/useSession';
import { errorText, formatDate } from '../../utils/format';
import type { PickupRecord } from '../../types/api';
const { user } = useSession();
const records = ref<PickupRecord[]>([]);
const loading = ref(true);
const error = useMessageState('error');
async function load() {
  loading.value = true;
  error.value = '';
  try {
    if (!user.value.id) throw new Error('未获取到用户信息，请重新登录');
    records.value = (await getUserPickupRecords(user.value.id)).data || [];
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>
<template>
  <PageHeader title="取件记录" description="每一次安心领取，都有迹可循。"
    ><el-button :loading="loading" @click="load"
      ><AppIcon name="refresh-cw" :size="16" />刷新记录</el-button
    ></PageHeader
  >

  <section class="panel">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">历史取件</h2>
        <p class="panel-description">
          {{ loading || error ? '正在同步历史记录' : `共 ${records.length} 条已完成的取件记录` }}
        </p>
      </div>
      <AppIcon name="history" class="muted" />
    </div>
    <div v-if="loading" class="panel-body"><el-skeleton :rows="6" animated /></div>
    <template v-else-if="records.length && !error"
      ><article
        v-for="(record, index) in records"
        :key="record.id || record.package_id || index"
        class="record-row"
      >
        <div class="flex min-w-0 items-start gap-3">
          <span class="row-icon"><AppIcon name="check-check" /></span>
          <div class="min-w-0">
            <strong>{{ record.company || record.package?.company || '快递' }}</strong>
            <p class="font-mono">
              运单号 {{ record.tracking_number || record.package?.tracking_number || '—' }}
            </p>
            <p>
              入库时间：{{
                formatDate(
                  record.inbound_at || record.package?.inbound_at || record.package?.created_at
                )
              }}
            </p>
            <p>
              出库时间：{{
                formatDate(record.picked_at || record.pickup_time || record.created_at)
              }}
            </p>
          </div>
        </div>
        <div class="shrink-0 text-right">
          <StatusBadge :status="record.current_status || '已取件'" />
          <p v-if="record.package_deleted" class="muted text-xs">包裹记录已删除，取件历史保留</p>
        </div>
      </article></template
    ><EmptyState
      v-else
      :title="error ? '暂时无法加载取件记录' : '还没有取件记录'"
      :description="error ? '请刷新后重试。' : '成功领取快递后，记录会自动显示在这里。'"
      ><el-button v-if="!error" plain type="primary" @click="$router.push('/user')"
        >查看我的快递</el-button
      ></EmptyState
    >
  </section>
</template>
