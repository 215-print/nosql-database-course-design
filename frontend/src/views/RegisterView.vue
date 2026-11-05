<script setup lang="ts">
import { useMessageState } from '../composables/useMessageState';
import { onUnmounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandMark from '../components/BrandMark.vue';
import { registerUser } from '../api/auth';
import { errorText } from '../utils/format';
const router = useRouter();
const form = reactive({ username: '', name: '', phone: '', password: '', confirmPassword: '' });
const loading = ref(false);
const error = useMessageState('error');
const success = useMessageState('success');
let timer: number | undefined;
onUnmounted(() => window.clearTimeout(timer));
async function register() {
  if (loading.value || success.value) return;
  error.value = '';
  if (!form.username.trim() || !form.name.trim() || !form.phone.trim() || !form.password) {
    error.value = '请完整填写所有信息';
    return;
  }
  if (form.username.trim().length < 2 || form.username.trim().length > 30) {
    error.value = '登录账号须为 2～30 个字符';
    return;
  }
  if (!/^1\d{10}$/.test(form.phone.trim())) {
    error.value = '请输入正确的 11 位手机号码';
    return;
  }
  if (form.password.length < 6 || form.password.length > 72) {
    error.value = '密码长度应为 6～72 个字符';
    return;
  }
  if (form.password !== form.confirmPassword) {
    error.value = '两次输入的密码不一致';
    return;
  }
  loading.value = true;
  try {
    await registerUser({
      username: form.username.trim(),
      name: form.name.trim(),
      phone: form.phone.trim(),
      password: form.password,
    });
    success.value = '注册成功，即将返回登录页面';
    timer = window.setTimeout(() => {
      void router.replace('/login');
    }, 900);
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}
</script>
<template>
  <main class="register-shell">
    <section class="panel register-card">
      <router-link class="text-link mb-5" to="/login"
        ><AppIcon name="arrow-left" :size="16" />返回登录</router-link
      ><BrandMark subtitle="校园生活，轻松收寄" />
      <h1>创建你的驿站账号</h1>
      <p class="page-description mb-6">手机号用于关联收件快递，请填写本人常用号码。</p>
      <form @submit.prevent="register">
        <fieldset :disabled="loading || !!success" class="form-grid m-0 min-w-0 border-0 p-0">
          <label class="field"
            >登录账号<el-input
              v-model="form.username"
              minlength="2"
              maxlength="30"
              autocomplete="username"
              placeholder="2～30 个字符"
              required /></label
          ><label class="field"
            >用户姓名<el-input
              v-model="form.name"
              maxlength="50"
              autocomplete="name"
              placeholder="请输入姓名"
              required /></label
          ><label class="field field-full"
            >绑定手机号<el-input
              v-model="form.phone"
              inputmode="tel"
              autocomplete="tel"
              maxlength="11"
              placeholder="11 位手机号码"
              required
              ><template #prefix><AppIcon name="phone" :size="16" /></template></el-input></label
          ><label class="field"
            >设置密码<el-input
              v-model="form.password"
              type="password"
              show-password
              minlength="6"
              maxlength="72"
              autocomplete="new-password"
              placeholder="至少 6 位"
              required /></label
          ><label class="field"
            >确认密码<el-input
              v-model="form.confirmPassword"
              type="password"
              show-password
              autocomplete="new-password"
              placeholder="再次输入密码"
              required /></label
          ><el-button
            class="field-full mt-1 !min-h-12"
            type="primary"
            native-type="submit"
            :loading="loading"
            :disabled="!!success"
            >{{ success ? '注册成功' : '创建账号' }}<AppIcon name="arrow-right" :size="17"
          /></el-button>
        </fieldset>
      </form>
    </section>
  </main>
</template>
