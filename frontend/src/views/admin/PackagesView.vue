<script setup lang="ts">
import { computed, reactive, ref, toRef } from 'vue';
import { ElMessageBox } from 'element-plus';
import 'element-plus/es/components/message-box/style/css';
import { updatePackage } from '../../api/packages';
import type { PackageRecord, PackageUpdateInput } from '../../types/api';
import { errorText, isTrue } from '../../utils/format';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import EmptyState from '../../components/EmptyState.vue';
import PackageList from '../../components/PackageList.vue';
import { usePackageList, type PackageScope } from '../../composables/usePackageList';
const props = defineProps<{ scope: PackageScope }>();
const {
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
} = usePackageList(toRef(props, 'scope'));
const selected = ref<PackageRecord>();
const editOpen = ref(false);
const saving = ref(false);
const editError = ref('');
const editForm = reactive({ is_large: false, is_fragile: false, is_fresh: false });
function handleAction(item: PackageRecord, action: 'edit' | 'abnormal' | 'delete' | 'status') {
  if (action === 'status') {
    void changeStatus(item);
    return;
  }
  if (action !== 'edit') {
    void act(item, action);
    return;
  }
  selected.value = item;
  Object.assign(editForm, {
    is_large: isTrue(item.is_large),
    is_fragile: isTrue(item.is_fragile),
    is_fresh: isTrue(item.is_fresh),
  });
  editError.value = '';
  editOpen.value = true;
}
async function saveEdit() {
  if (saving.value || !selected.value) return;
  saving.value = true;
  editError.value = '';
  try {
    const data: PackageUpdateInput = { ...editForm };
    await updatePackage(selected.value.id, data);
    editOpen.value = false;
    await load();
    if (!error.value) success.value = '包裹属性已更新';
  } catch (e) {
    editError.value = errorText(e);
  } finally {
    saving.value = false;
  }
}
async function changeStatus(item: PackageRecord) {
  const next =
    item.status === '已取件' ? '待取件' : item.direction === '收件' ? '已取件' : '待揽收';
  try {
    if (next === '待取件')
      await ElMessageBox.confirm('重新入库后会生成新的取件码，确认继续？', '重新入库', {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
      });
    await updatePackage(item.id, { status: next });
    await load();
    success.value = next === '待取件' ? '包裹已重新入库' : '包裹状态已更新';
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') error.value = errorText(e);
  }
}
const title = computed(() =>
  props.scope === 'waiting' ? '包裹查询' : props.scope === 'abnormal' ? '异常件处理' : '快递管理'
);
const description = computed(() =>
  props.scope === 'waiting'
    ? '输入完整运单号、完整手机号或手机号后四位，查询快递及取件码。'
    : props.scope === 'abnormal'
      ? '查看最新录入的异常件并解除异常状态。'
      : '检索并维护驿站快递记录。'
);
</script>
<template>
  <PageHeader :title="title" :description="description"
    ><el-button :loading="loading" @click="load()"
      ><AppIcon name="refresh-cw" :size="16" />刷新</el-button
    ><el-button v-if="scope === 'all'" type="primary" @click="$router.push('/admin/intake')"
      ><AppIcon name="plus" :size="17" />快递入库</el-button
    ></PageHeader
  >
  <section class="panel">
    <form class="data-toolbar" @submit.prevent="search">
      <label class="search-field"
        ><span class="filter-label">查询内容</span
        ><el-input
          v-model="keyword"
          clearable
          :placeholder="
            scope === 'waiting'
              ? '完整运单号、完整手机号或手机号后四位'
              : '运单号、收件人、手机号或快递公司'
          "
          ><template #prefix><AppIcon name="search" :size="16" /></template></el-input
      ></label>
      <label v-if="scope === 'all'" class="w-32"
        ><span class="filter-label">快递状态</span
        ><el-select v-model="status"
          ><el-option
            v-for="item in ['全部', '待取件', '已取件', '待揽收', '异常']"
            :key="item"
            :label="item"
            :value="item" /></el-select
      ></label>
      <el-button type="primary" native-type="submit" :loading="searching" :disabled="loading"
        >查询</el-button
      ><el-button @click="reset">重置</el-button>
    </form>
    <div v-if="loading || searching" class="panel-body" aria-busy="true">
      <el-skeleton :rows="7" animated />
    </div>
    <EmptyState
      v-else-if="error && !filtered.length"
      title="暂时无法加载快递"
      description="请检查提示后重新查询，或刷新数据。"
      ><el-button @click="load()">重新加载</el-button></EmptyState
    >
    <PackageList
      v-else-if="filtered.length"
      :items="visible"
      :busy="!!busyId || saving"
      :scope="scope"
      @action="handleAction"
    />
    <EmptyState
      v-else
      :title="
        scope === 'waiting' && !searched
          ? '请输入条件查询快递'
          : scope === 'abnormal'
            ? '当前没有需要处理的异常快递。'
            : '没有匹配的快递'
      "
      :description="
        scope === 'waiting'
          ? '查询结果仅显示匹配的收件快递及有效取件码。'
          : '试试调整查询条件，或清空筛选。'
      "
    />
    <div v-if="filtered.length" class="table-footer">
      <span>共 {{ filtered.length }} 条记录 · 每页 {{ pageSize }} 条</span
      ><el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="filtered.length"
        :pager-count="5"
        layout="prev, pager, next"
      />
    </div>
  </section>
  <el-dialog
    v-model="editOpen"
    title="编辑包裹属性"
    width="min(520px, 92vw)"
    :close-on-click-modal="!saving"
    :close-on-press-escape="!saving"
    :show-close="!saving"
  >
    <div v-if="selected" class="grid gap-4">
      <div class="record-details">
        <div>
          <dt>包裹唯一 ID</dt>
          <dd class="break-all font-mono">{{ selected.id }}</dd>
        </div>
        <div>
          <dt>快递公司</dt>
          <dd>{{ selected.company || '—' }}</dd>
        </div>
        <div>
          <dt>运单号</dt>
          <dd>{{ selected.tracking_number || '—' }}</dd>
        </div>
        <div>
          <dt>收件人</dt>
          <dd>{{ selected.receiver_name }} · {{ selected.phone }}</dd>
        </div>
      </div>
      <el-alert v-if="editError" :title="editError" type="error" :closable="false" />
      <fieldset :disabled="saving" class="m-0 border-0 p-0">
        <div class="flex flex-wrap gap-4">
          <el-checkbox v-model="editForm.is_large">大件物品</el-checkbox
          ><el-checkbox v-model="editForm.is_fragile">易碎物品</el-checkbox
          ><el-checkbox v-model="editForm.is_fresh">生鲜冷冻</el-checkbox>
        </div>
        <div class="form-actions justify-end">
          <el-button @click="editOpen = false">取消</el-button
          ><el-button type="primary" :loading="saving" @click="saveEdit">保存修改</el-button>
        </div>
      </fieldset>
    </div>
  </el-dialog>
</template>
