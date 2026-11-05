<script setup lang="ts">
import AppIcon from './AppIcon.vue';
import StatusBadge from './StatusBadge.vue';
import { formatDate, isTrue } from '../utils/format';
import type { PackageRecord } from '../types/api';
defineProps<{ items: PackageRecord[]; busy?: boolean; scope?: 'all' | 'waiting' | 'abnormal' }>();
const emit = defineEmits<{
  action: [item: PackageRecord, action: 'edit' | 'abnormal' | 'delete' | 'status'];
}>();
function emitAction(row: unknown, action: 'edit' | 'abnormal' | 'delete' | 'status') {
  emit('action', row as PackageRecord, action);
}
const attrs = (value: unknown) => {
  const p = value as PackageRecord;
  return (
    [
      isTrue(p.is_large) ? '大件物品' : '',
      isTrue(p.is_fragile) ? '易碎物品' : '',
      isTrue(p.is_fresh) ? '生鲜冷冻' : '',
      isTrue(p.is_valuable) ? '贵重物品' : '',
    ]
      .filter(Boolean)
      .join(' · ') || '普通件'
  );
};
</script>
<template>
  <div class="table-scroll">
    <el-table :data="items" row-key="id">
      <el-table-column label="快递信息" min-width="200"
        ><template #default="{ row }"
          ><strong>{{ row.company || '快递' }}</strong
          ><span class="muted ml-2 text-xs">{{ row.direction }}</span>
          <p class="muted mt-1 font-mono text-[11px] break-all">
            {{ row.tracking_number || row.package_code }}
          </p></template
        ></el-table-column
      >
      <el-table-column label="收件人信息" min-width="190"
        ><template #default="{ row }"
          ><strong>{{ row.receiver_name || '—' }}</strong
          ><p class="muted mt-1 text-xs">{{ row.receiver_phone || row.phone || '—' }}</p
          ><p v-if="row.receiver_address" class="muted mt-1 text-xs">{{ row.receiver_address }}</p></template
        ></el-table-column
      >
      <el-table-column label="状态" min-width="100"
        ><template #default="{ row }"
          ><StatusBadge :status="row.status" :abnormal="row.abnormal" /></template
      ></el-table-column>
      <el-table-column v-if="scope === 'waiting'" label="取件码" min-width="140"
        ><template #default="{ row }"
          ><span
            v-if="row.status === '待取件'"
            class="text-brand font-mono text-lg font-bold tracking-wide"
            >{{ row.pickup_code || '—' }}</span
          ><span v-else>—</span></template
        ></el-table-column
      >
      <el-table-column label="属性" min-width="125"
        ><template #default="{ row }"
          ><span class="muted text-xs">{{ attrs(row) }}</span></template
        ></el-table-column
      >
      <el-table-column label="录入时间" min-width="150"
        ><template #default="{ row }"
          ><span class="muted text-xs">{{ formatDate(row.created_at) }}</span></template
        ></el-table-column
      >
      <el-table-column label="入库时间" min-width="150"
        ><template #default="{ row }"
          ><span class="muted text-xs">{{
            formatDate(row.inbound_at || row.created_at)
          }}</span></template
        ></el-table-column
      >
      <el-table-column label="出库时间" min-width="150"
        ><template #default="{ row }"
          ><span class="muted text-xs">{{ formatDate(row.picked_at) }}</span></template
        ></el-table-column
      >
      <el-table-column
        v-if="scope !== 'waiting'"
        label="操作"
        fixed="right"
        :min-width="scope === 'abnormal' ? 100 : 260"
        ><template #default="{ row }"
          ><template v-if="scope === 'abnormal'"
            ><el-button link type="primary" :disabled="busy" @click="emitAction(row, 'abnormal')"
              >取消异常</el-button
            ></template
          ><template v-else
            ><el-button link type="primary" :disabled="busy" @click="emitAction(row, 'edit')"
              >编辑</el-button
            ><el-button
              v-if="row.status === '待取件' || row.status === '已取件'"
              link
              type="primary"
              :disabled="busy"
              @click="emitAction(row, 'status')"
              >{{ row.status === '已取件' ? '重新入库' : '确认出库' }}</el-button
            ><el-button link type="primary" :disabled="busy" @click="emitAction(row, 'abnormal')">{{
              row.abnormal || row.status === '异常' ? '取消异常' : '标记异常'
            }}</el-button
            ><el-button link type="danger" :disabled="busy" @click="emitAction(row, 'delete')"
              >删除</el-button
            ></template
          ></template
        ></el-table-column
      >
    </el-table>
  </div>
  <div class="record-cards">
    <article v-for="item in items" :key="item.id" class="record-card">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <strong class="text-sm">{{ item.company || '快递' }}</strong
          ><span class="muted ml-2 text-xs">{{ item.direction }}</span>
          <p class="muted mt-2 font-mono text-xs break-all">
            {{ item.tracking_number || item.package_code }}
          </p>
        </div>
        <StatusBadge :status="item.status" :abnormal="item.abnormal" />
      </div>
      <dl class="record-details">
        <div>
          <dt>收件人</dt>
          <dd>{{ item.receiver_name || '—' }}</dd>
        </div>
        <div>
          <dt>收件人电话</dt>
          <dd>{{ item.receiver_phone || item.phone || '—' }}</dd>
        </div>
        <div v-if="item.receiver_address">
          <dt>收件地址</dt>
          <dd>{{ item.receiver_address }}</dd>
        </div>
        <div>
          <dt>录入时间</dt>
          <dd>{{ formatDate(item.created_at) }}</dd>
        </div>
        <div v-if="scope === 'waiting' && item.status === '待取件'" class="pickup-code-detail">
          <dt>取件码</dt>
          <dd class="text-brand font-mono text-lg font-bold tracking-wide">
            {{ item.pickup_code || '—' }}
          </dd>
        </div>
        <div>
          <dt>包裹属性</dt>
          <dd>{{ attrs(item) }}</dd>
        </div>
        <div>
          <dt>入库时间</dt>
          <dd>{{ formatDate(item.inbound_at || item.created_at) }}</dd>
        </div>
        <div>
          <dt>出库时间</dt>
          <dd>{{ formatDate(item.picked_at) }}</dd>
        </div>
      </dl>
      <div v-if="scope !== 'waiting'" class="record-actions">
        <template v-if="scope === 'abnormal'"
          ><el-button :disabled="busy" @click="$emit('action', item, 'abnormal')"
            ><AppIcon name="triangle-alert" :size="15" />取消异常</el-button
          ></template
        ><template v-else
          ><el-button :disabled="busy" @click="$emit('action', item, 'edit')"
            ><AppIcon name="pencil" :size="15" />编辑</el-button
          ><el-button
            v-if="item.status === '待取件' || item.status === '已取件'"
            :disabled="busy"
            @click="$emit('action', item, 'status')"
            >{{ item.status === '已取件' ? '重新入库' : '确认出库' }}</el-button
          ><el-button :disabled="busy" @click="$emit('action', item, 'abnormal')">{{
            item.abnormal || item.status === '异常' ? '取消异常' : '标记异常'
          }}</el-button
          ><el-button :disabled="busy" text type="danger" @click="$emit('action', item, 'delete')"
            ><AppIcon name="trash-2" :size="15" />删除</el-button
          ></template
        >
      </div>
    </article>
  </div>
</template>
