<script setup lang="ts">
import { useMessageState } from '../../composables/useMessageState';
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElMessageBox } from 'element-plus';
import 'element-plus/es/components/message-box/style/css';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import EmptyState from '../../components/EmptyState.vue';
import StatusBadge from '../../components/StatusBadge.vue';
import {
  createCourier,
  getAdminCouriers,
  getAdminUsers,
  resetAdminUserPassword,
  setCourierBlacklist,
  setUserBlacklist,
  updateAdminUserAccount,
  updateCourier,
} from '../../api/packages';
import type { Courier, UserProfile } from '../../types/api';
import { errorText, isTrue, normalizeList } from '../../utils/format';

const tab = ref<'users' | 'couriers'>('users');
const users = ref<UserProfile[]>([]);
const couriers = ref<Courier[]>([]);
const loading = ref(true);
const saving = ref(false);
const busy = ref(false);
const keyword = ref('');
const error = useMessageState('error');
const success = useMessageState('success');
const dialogError = useMessageState('error');
const page = ref(1);
const dialog = ref<'courier' | 'courier-edit' | 'account' | 'password'>('courier');
const dialogOpen = ref(false);
const selected = ref<UserProfile | null>(null);
const account = reactive({ username: '', name: '', new_password: '' });
const courier = reactive({ name: '', phone: '' });
const filtered = computed(() => {
  const query = keyword.value.trim().toLowerCase();
  const source: (UserProfile | Courier)[] = tab.value === 'users' ? users.value : couriers.value;
  return source.filter(
    (p) =>
      !query ||
      [p.name, 'username' in p ? p.username : '', p.phone].some((v) =>
        String(v || '')
          .toLowerCase()
          .includes(query)
      )
  );
});
const visible = computed(() => filtered.value.slice((page.value - 1) * 10, page.value * 10));
function openRow(mode: 'account' | 'password', row: unknown) {
  open(mode, row as UserProfile);
}
function toggleRow(row: unknown) {
  void toggle(row as UserProfile | Courier);
}
watch([keyword, tab], () => {
  page.value = 1;
  error.value = '';
  success.value = '';
});
watch(
  () => filtered.value.length,
  (count) => {
    page.value = Math.min(page.value, Math.max(1, Math.ceil(count / 10)));
  }
);
async function load(clear = true) {
  loading.value = true;
  if (clear) {
    error.value = '';
    success.value = '';
  }
  try {
    const [a, b] = await Promise.all([getAdminUsers(), getAdminCouriers()]);
    users.value = normalizeList<UserProfile>(a, 'users');
    couriers.value = normalizeList<Courier>(b, 'couriers');
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}
function open(
  mode: 'courier' | 'courier-edit' | 'account' | 'password',
  person?: UserProfile | Courier
) {
  dialog.value = mode;
  dialogOpen.value = true;
  dialogError.value = '';
  selected.value = (person as UserProfile) || null;
  Object.assign(account, {
    username: person && 'username' in person ? person.username : '',
    name: person?.name || '',
    new_password: '',
  });
  Object.assign(courier, { name: '', phone: '' });
  if (mode === 'courier-edit' && person && !('username' in person)) {
    Object.assign(courier, { name: person.name, phone: person.phone });
  }
}
function handleDialogVisibility(value: boolean) {
  if (!value && !saving.value) dialogOpen.value = false;
}
async function submit() {
  if (saving.value) return;
  dialogError.value = '';
  error.value = '';
  success.value = '';
  if (dialog.value === 'courier' || dialog.value === 'courier-edit') {
    if (!courier.name.trim() || !/^1\d{10}$/.test(courier.phone.trim())) {
      dialogError.value = '请填写姓名和正确的 11 位手机号';
      return;
    }
  } else if (!selected.value?.id) {
    dialogError.value = '未获取到用户编号，请刷新后重试';
    return;
  } else if (
    dialog.value === 'account' &&
    (account.username.trim().length < 2 ||
      account.username.trim().length > 30 ||
      !account.name.trim() ||
      account.name.trim().length > 50)
  ) {
    dialogError.value = '账号须为 2～30 个字符，姓名须为 1～50 个字符';
    return;
  } else if (
    dialog.value === 'password' &&
    (account.new_password.length < 6 || account.new_password.length > 72)
  ) {
    dialogError.value = '密码须为 6～72 个字符';
    return;
  }
  if (dialog.value === 'password') {
    try {
      await ElMessageBox.confirm(
        `确认重置用户「${selected.value?.username || selected.value?.name}」的密码？`,
        '重置用户密码',
        { confirmButtonText: '确认重置', cancelButtonText: '取消' }
      );
    } catch {
      return;
    }
  }
  saving.value = true;
  try {
    if (dialog.value === 'courier')
      await createCourier({ name: courier.name.trim(), phone: courier.phone.trim() });
    else if (dialog.value === 'courier-edit')
      await updateCourier(selected.value!.id, {
        name: courier.name.trim(),
        phone: courier.phone.trim(),
      });
    else if (dialog.value === 'account')
      await updateAdminUserAccount(selected.value!.id, {
        username: account.username.trim(),
        name: account.name.trim(),
      });
    else await resetAdminUserPassword(selected.value!.id, { new_password: account.new_password });
    success.value =
      dialog.value === 'courier'
        ? '快递员登记成功'
        : dialog.value === 'courier-edit'
          ? '快递员资料已更新'
          : dialog.value === 'account'
            ? '用户资料已更新'
            : '用户密码已重置';
    dialogOpen.value = false;
    account.new_password = '';
    await load(false);
  } catch (e) {
    dialogError.value = errorText(e);
  } finally {
    saving.value = false;
  }
}
async function toggle(person: UserProfile | Courier) {
  if (busy.value) return;
  const next = !isTrue(person.blacklist);
  const isUser = tab.value === 'users';
  try {
    await ElMessageBox.confirm(
      `确认${next ? '将' : '解除'}「${person.name || person.phone}」${next ? '加入黑名单' : '的黑名单限制'}？`,
      next ? '加入黑名单' : '解除黑名单',
      { confirmButtonText: '确认', cancelButtonText: '取消' }
    );
  } catch {
    return;
  }
  busy.value = true;
  error.value = '';
  success.value = '';
  try {
    await (isUser ? setUserBlacklist(person.id, next) : setCourierBlacklist(person.id, next));
    success.value = next ? '已加入黑名单' : '已解除黑名单';
    await load(false);
  } catch (e) {
    error.value = errorText(e);
  } finally {
    busy.value = false;
  }
}
onMounted(() => load());
</script>

<template>
  <PageHeader title="人员管理" description="维护注册用户与快递员资料，管理账户使用状态。"
    ><el-button :loading="loading" @click="load()"
      ><AppIcon name="refresh-cw" :size="16" />刷新</el-button
    ><el-button type="primary" @click="open('courier')"
      ><AppIcon name="plus" :size="17" />登记快递员</el-button
    ></PageHeader
  >

  <section class="panel">
    <div class="panel-header">
      <el-radio-group v-model="tab" aria-label="人员类别"
        ><el-radio-button value="users">注册用户 {{ loading ? '…' : users.length }}</el-radio-button
        ><el-radio-button value="couriers"
          >快递员 {{ loading ? '…' : couriers.length }}</el-radio-button
        ></el-radio-group
      ><label class="w-full sm:w-72"
        ><span class="sr-only">搜索人员</span
        ><el-input
          v-model="keyword"
          clearable
          :placeholder="tab === 'users' ? '搜索姓名、账号或手机号' : '搜索姓名或手机号'"
          ><template #prefix><AppIcon name="search" :size="16" /></template></el-input
      ></label>
    </div>
    <div v-if="loading" class="panel-body" aria-busy="true"><el-skeleton :rows="7" animated /></div>
    <template v-else-if="filtered.length">
      <div class="table-scroll">
        <el-table :data="visible" row-key="id"
          ><el-table-column :label="tab === 'users' ? '用户信息' : '快递员信息'" min-width="200"
            ><template #default="{ row }"
              ><div class="flex items-center gap-3">
                <span class="avatar small">{{
                  (row.name || row.username || '人').slice(0, 1)
                }}</span>
                <div>
                  <strong>{{ row.name || row.username }}</strong>
                  <p v-if="tab === 'users'" class="muted mt-1 text-[11px]">{{ row.username }}</p>
                </div>
              </div></template
            ></el-table-column
          ><el-table-column prop="phone" label="手机号" min-width="145" /><el-table-column
            label="账户状态"
            min-width="120"
            ><template #default="{ row }"
              ><StatusBadge
                :status="isTrue(row.blacklist) ? '黑名单' : '正常'" /></template></el-table-column
          ><el-table-column label="操作" fixed="right" :width="tab === 'users' ? 280 : 210"
            ><template #default="{ row }"
              ><el-button
                v-if="tab === 'users'"
                link
                type="primary"
                @click="openRow('account', row)"
                >编辑资料</el-button
              ><el-button
                v-if="tab === 'users'"
                link
                type="primary"
                @click="openRow('password', row)"
                >重置密码</el-button
              ><el-button v-else link type="primary" @click="open('courier-edit', row as Courier)"
                >编辑资料</el-button
              ><el-button
                link
                :type="isTrue(row.blacklist) ? 'primary' : 'danger'"
                :disabled="busy"
                @click="toggleRow(row)"
                >{{ isTrue(row.blacklist) ? '解除黑名单' : '加入黑名单' }}</el-button
              ></template
            ></el-table-column
          ></el-table
        >
      </div>
      <div class="record-cards">
        <article v-for="person in visible" :key="person.id" class="record-card">
          <div class="flex items-center justify-between gap-3">
            <div class="flex min-w-0 items-center gap-3">
              <span class="avatar small shrink-0">{{ (person.name || '人').slice(0, 1) }}</span
              ><strong class="text-sm break-all">{{
                person.name || ('username' in person ? person.username : '快递员')
              }}</strong>
            </div>
            <StatusBadge :status="isTrue(person.blacklist) ? '黑名单' : '正常'" />
          </div>
          <dl class="record-details">
            <div v-if="'username' in person">
              <dt>登录账号</dt>
              <dd>{{ person.username }}</dd>
            </div>
            <div>
              <dt>手机号</dt>
              <dd>{{ person.phone }}</dd>
            </div>
          </dl>
          <div class="record-actions">
            <el-button v-if="tab === 'users'" @click="open('account', person)"
              ><AppIcon name="pencil" :size="15" />编辑资料</el-button
            ><el-button v-if="tab === 'users'" @click="open('password', person)"
              ><AppIcon name="key-round" :size="15" />重置密码</el-button
            ><el-button v-else @click="open('courier-edit', person)"
              ><AppIcon name="pencil" :size="15" />编辑资料</el-button
            ><el-button
              text
              :type="isTrue(person.blacklist) ? 'primary' : 'danger'"
              :disabled="busy"
              @click="toggle(person)"
              >{{ isTrue(person.blacklist) ? '解除黑名单' : '加入黑名单' }}</el-button
            >
          </div>
        </article>
      </div>
      <div class="table-footer">
        <span>共 {{ filtered.length }} 人</span
        ><el-pagination
          v-model:current-page="page"
          :page-size="10"
          :total="filtered.length"
          :pager-count="5"
          layout="prev, pager, next"
        />
      </div>
    </template>
    <EmptyState
      v-else
      :title="
        error
          ? '人员数据加载失败'
          : keyword
            ? '没有匹配的人员'
            : tab === 'users'
              ? '还没有注册用户'
              : '还没有登记快递员'
      "
      :description="
        error
          ? '请刷新后重试。'
          : keyword
            ? '请尝试其他姓名、账号或手机号。'
            : tab === 'couriers'
              ? '点击右上方的登记快递员按钮添加。'
              : '用户完成注册后将在这里显示。'
      "
    />
  </section>
  <el-dialog
    :model-value="dialogOpen"
    :title="
      dialog === 'courier'
        ? '登记快递员'
        : dialog === 'courier-edit'
          ? '编辑快递员资料'
          : dialog === 'account'
            ? '编辑用户资料'
            : '重置用户密码'
    "
    width="460px"
    :close-on-click-modal="!saving"
    :close-on-press-escape="!saving"
    :show-close="!saving"
    @update:model-value="handleDialogVisibility"
    @closed="account.new_password = ''"
  >
    <form class="grid gap-5" @submit.prevent="submit">
      <fieldset :disabled="saving" class="m-0 grid min-w-0 gap-5 border-0 p-0">
        <template v-if="dialog === 'courier' || dialog === 'courier-edit'"
          ><label class="field"
            >快递员姓名<el-input
              v-model="courier.name"
              maxlength="50"
              placeholder="输入姓名"
              required /></label
          ><label class="field"
            >手机号<el-input
              v-model="courier.phone"
              maxlength="11"
              inputmode="tel"
              placeholder="11 位手机号"
              required /></label
        ></template>
        <template v-else-if="dialog === 'account'"
          ><label class="field"
            >登录账号<el-input
              v-model="account.username"
              minlength="2"
              maxlength="30"
              required /></label
          ><label class="field"
            >用户名称<el-input v-model="account.name" maxlength="50" required /></label
        ></template>
        <template v-else
          ><p class="muted text-xs leading-6">
            为 {{ selected?.name || selected?.username }} 设置新的登录密码。
          </p>
          <label class="field"
            >新密码<el-input
              v-model="account.new_password"
              type="password"
              show-password
              minlength="6"
              maxlength="72"
              autocomplete="new-password"
              placeholder="6～72 个字符"
              required /></label
        ></template>
        <div class="form-actions mt-2 justify-end">
          <el-button :disabled="saving" @click="dialogOpen = false">取消</el-button
          ><el-button type="primary" native-type="submit" :loading="saving">{{
            dialog === 'password' ? '重置密码' : '保存'
          }}</el-button>
        </div>
      </fieldset>
    </form>
  </el-dialog>
</template>
