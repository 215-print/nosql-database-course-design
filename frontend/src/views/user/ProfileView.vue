<script setup lang="ts">
import { reactive, ref } from 'vue';
import { ElMessageBox } from 'element-plus';
import 'element-plus/es/components/message-box/style/css';
import AppIcon from '../../components/AppIcon.vue';
import PageHeader from '../../components/PageHeader.vue';
import {
  addUserPhone,
  changeUserPassword,
  removeUserPhone,
  updateUserAccount,
} from '../../api/packages';
import { useSession } from '../../composables/useSession';
import { errorText, maskPhone } from '../../utils/format';
const { user, saveProfile, logout } = useSession();
const editing = ref(false);
const saving = ref(false);
const error = ref('');
const success = ref('');
const passwordDialog = ref(false);
const passwordError = ref('');
const account = reactive({ username: user.value.username || '', name: user.value.name || '' });
const password = reactive({ current_password: '', new_password: '', confirm_password: '' });
const phones = () =>
  user.value.phone_numbers?.length ? user.value.phone_numbers : [user.value.phone];
function openPasswordDialog() {
  password.current_password = '';
  password.new_password = '';
  password.confirm_password = '';
  passwordError.value = '';
  passwordDialog.value = true;
}
function cancelEdit() {
  account.username = user.value.username;
  account.name = user.value.name;
  editing.value = false;
  error.value = '';
}
async function saveAccount() {
  if (saving.value) return;
  error.value = '';
  success.value = '';
  if (account.username.trim().length < 2 || !account.name.trim()) {
    error.value = '请填写有效的登录账号和用户名称';
    return;
  }
  saving.value = true;
  try {
    const payload = { username: account.username.trim(), name: account.name.trim() };
    const result = await updateUserAccount(user.value.id, payload);
    saveProfile({ ...user.value, ...(result.user || payload) });
    editing.value = false;
    success.value = '账户资料已保存';
  } catch (e) {
    error.value = errorText(e);
  } finally {
    saving.value = false;
  }
}
async function addPhone() {
  try {
    const { value } = await ElMessageBox.prompt('请输入要绑定的 11 位手机号', '绑定手机号', {
      inputPattern: /^1\d{10}$/,
      inputErrorMessage: '请输入有效的手机号',
      confirmButtonText: '绑定',
      cancelButtonText: '取消',
    });
    const res = await addUserPhone(user.value.id, value);
    if (res.user) saveProfile({ ...user.value, ...res.user });
    success.value = '手机号已绑定';
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') error.value = errorText(e);
  }
}
async function removePhone(phone: string) {
  try {
    await ElMessageBox.confirm(`解绑手机号 ${maskPhone(phone)}？`, '解绑手机号', {
      confirmButtonText: '解绑',
      cancelButtonText: '取消',
    });
    const res = await removeUserPhone(user.value.id, phone);
    if (res.user) saveProfile({ ...user.value, ...res.user });
    success.value = '手机号已解绑';
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') error.value = errorText(e);
  }
}
async function savePassword() {
  passwordError.value = '';
  if (
    !password.current_password ||
    password.new_password.length < 6 ||
    password.new_password !== password.confirm_password
  ) {
    passwordError.value = '请检查当前密码、新密码长度和两次确认内容';
    return;
  }
  saving.value = true;
  try {
    await changeUserPassword(user.value.id, {
      current_password: password.current_password,
      new_password: password.new_password,
    });
    passwordDialog.value = false;
    success.value = '密码已修改，请重新登录';
    setTimeout(logout, 900);
  } catch (e) {
    passwordError.value = errorText(e);
  } finally {
    saving.value = false;
  }
}
</script>
<template>
  <PageHeader title="个人中心" description="管理账户资料、绑定手机号和登录安全。" />
  <div class="two-column">
    <div class="grid gap-5">
      <section class="panel">
        <div class="panel-body">
          <div class="profile-summary">
            <span class="profile-avatar">{{
              (user.name || user.username || '同学').slice(0, 1)
            }}</span>
            <div class="min-w-0">
              <h2 class="break-all">{{ user.name || user.username }}</h2>
              <p>校园用户</p>
            </div>
          </div>
          <div class="detail-cell mt-5">
            <dt class="mb-2">
              绑定手机号 <el-button link type="primary" @click="addPhone">管理 / 添加</el-button>
            </dt>
            <dd v-for="phone in phones()" :key="phone" class="flex items-center gap-3 py-1">
              {{ maskPhone(phone)
              }}<el-button link type="danger" @click="removePhone(phone)">解绑</el-button>
            </dd>
          </div>
          <el-alert
            v-if="error"
            class="mt-4"
            :title="error"
            type="error"
            :closable="false"
          /><el-alert
            v-if="success"
            class="mt-4"
            :title="success"
            type="success"
            :closable="false"
          />
          <div class="mt-6 flex items-center justify-between">
            <h2 class="panel-title">账户资料</h2>
            <div v-if="!editing" class="flex gap-2">
              <el-button @click="editing = true"
                ><AppIcon name="pencil" :size="15" />修改资料</el-button
              ><el-button @click="openPasswordDialog"
                ><AppIcon name="lock-keyhole" :size="15" />修改密码</el-button
              >
            </div>
          </div>
          <div v-if="!editing" class="detail-grid mt-4">
            <div class="detail-cell">
              <dt>登录账号</dt>
              <dd>{{ user.username }}</dd>
            </div>
            <div class="detail-cell">
              <dt>用户名称</dt>
              <dd>{{ user.name }}</dd>
            </div>
          </div>
          <form v-else class="mt-4" @submit.prevent="saveAccount">
            <div class="form-grid">
              <label class="field"
                >登录账号<el-input
                  v-model="account.username"
                  minlength="2"
                  maxlength="30"
                  autocomplete="username" /></label
              ><label class="field"
                >用户名称<el-input v-model="account.name" maxlength="50" autocomplete="name"
              /></label>
            </div>
            <div class="form-actions justify-end">
              <el-button :disabled="saving" @click="cancelEdit">取消</el-button
              ><el-button type="primary" native-type="submit" :loading="saving">保存</el-button>
            </div>
          </form>
        </div>
      </section>
    </div>
    <aside class="grid gap-5">
      <div class="soft-note">
        <h3 class="flex items-center gap-2"><AppIcon name="shield-check" :size="19" />账户安全</h3>
        <p class="muted text-xs leading-7">请妥善保管登录密码，并及时更新绑定手机号。</p>
      </div>
      <section class="panel">
        <div class="panel-body">
          <h3 class="panel-title">离开工作区</h3>
          <p class="panel-description mb-4">在公共设备上使用后，请退出登录。</p>
          <el-button class="w-full" @click="logout"
            ><AppIcon name="log-out" :size="16" />退出登录</el-button
          >
        </div>
      </section>
    </aside>
  </div>
  <el-dialog
    v-model="passwordDialog"
    title="修改密码"
    width="min(520px, 92vw)"
    :close-on-click-modal="!saving"
    :close-on-press-escape="!saving"
    :show-close="!saving"
  >
    <p class="panel-description mb-5">修改密码后需要重新登录。</p>
    <el-alert
      v-if="passwordError"
      class="mb-4"
      :title="passwordError"
      type="error"
      :closable="false"
    />
    <form @submit.prevent="savePassword">
      <div class="grid gap-4">
        <label class="field"
          >当前密码<el-input
            v-model="password.current_password"
            type="password"
            show-password
            autocomplete="current-password"
            required
        /></label>
        <label class="field"
          >新密码<el-input
            v-model="password.new_password"
            type="password"
            show-password
            minlength="6"
            maxlength="72"
            autocomplete="new-password"
            required
        /></label>
        <label class="field"
          >确认新密码<el-input
            v-model="password.confirm_password"
            type="password"
            show-password
            autocomplete="new-password"
            required
        /></label>
      </div>
      <div class="form-actions justify-end">
        <el-button :disabled="saving" @click="passwordDialog = false">取消</el-button
        ><el-button type="primary" native-type="submit" :loading="saving"
          ><AppIcon name="lock-keyhole" :size="16" />保存新密码</el-button
        >
      </div>
    </form>
  </el-dialog>
</template>
