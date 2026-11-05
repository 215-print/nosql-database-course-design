<script setup lang="ts">
import { useMessageState } from '../composables/useMessageState';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandMark from '../components/BrandMark.vue';
import parcelArtwork from '../assets/login-parcel.svg';
import { loginAdmin, loginUser } from '../api/auth';
import { errorText } from '../utils/format';
import '../style/login.css';

const router = useRouter();
const isAdmin = import.meta.env.MODE === 'admin';
const username = ref('');
const password = ref('');
const passwordVisible = ref(false);
const loading = ref(false);
const error = useMessageState('error');
async function login() {
  if (loading.value) return;
  error.value = '';
  if (!username.value.trim() || !password.value) {
    error.value = '请输入账号和密码';
    return;
  }
  loading.value = true;
  try {
    const result = await (isAdmin ? loginAdmin : loginUser)({
      username: username.value.trim(),
      password: password.value,
    });
    if (!result?.token) throw new Error('登录响应中没有会话 Token');
    localStorage.setItem('token', result.token);
    localStorage.setItem('role', isAdmin ? '管理员' : '用户');
    localStorage.setItem('user', JSON.stringify(result.admin || result.user || result.data || {}));
    await router.replace(isAdmin ? '/admin' : '/user');
  } catch (e) {
    error.value = errorText(e);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-frame">
      <section class="login-brand-panel" aria-label="校园驿站">
        <div class="login-brand-top">
          <BrandMark dark subtitle="校园生活，轻松收寄" /><span class="login-edition"
            >CAMPUS / PARCEL</span
          >
        </div>
        <img class="login-artwork" :src="parcelArtwork" alt="" aria-hidden="true" />
        <div class="login-brand-copy">
          <p class="login-brand-kicker">A LITTLE CLOSER, EVERY DAY</p>
          <h2>
            {{ isAdmin ? '每一份托付，' : '每一份期待，' }}<br /><span>{{
              isAdmin ? '都井然有序。' : '都值得好好抵达。'
            }}</span>
          </h2>
          <p class="login-brand-description">
            {{
              isAdmin
                ? '从入库到领取，让驿站日常有条不紊。'
                : '从一份快递开始，连接校园里的日常与远方。'
            }}
          </p>
        </div>
        <div class="login-brand-bottom">
          <span>校园快递驿站</span><span>DELIVERING EVERYDAY MOMENTS</span>
        </div>
      </section>
      <section class="login-form-panel" aria-labelledby="login-title">
        <div class="login-panel-top">
          <span class="login-role">{{ isAdmin ? '运营管理' : '用户服务' }}</span
          ><span>校园驿站 · {{ isAdmin ? '管理员入口' : '账户登录' }}</span>
        </div>
        <div class="login-form-content">
          <p class="login-welcome">WELCOME BACK</p>
          <h1 id="login-title">{{ isAdmin ? '登录驿站工作台' : '欢迎回来' }}</h1>
          <p class="login-form-description">
            {{
              isAdmin
                ? '登录运营工作台，有序处理每一份托付。'
                : '登录校园驿站，接住生活里的小期待。'
            }}
          </p>
          <form class="login-form" novalidate @submit.prevent="login">
            <label class="login-field" for="login-username"
              ><span>登录账号</span
              ><el-input
                id="login-username"
                v-model="username"
                name="username"
                :disabled="loading"
                autocomplete="username"
                placeholder="请输入你的账号"
                required
                ><template #prefix><AppIcon name="user-round" :size="17" /></template></el-input
            ></label>
            <label class="login-field" for="login-password"
              ><span>登录密码</span
              ><el-input
                id="login-password"
                v-model="password"
                name="password"
                :disabled="loading"
                :type="passwordVisible ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入登录密码"
                required
                ><template #prefix><AppIcon name="lock-keyhole" :size="17" /></template
                ><template #suffix
                  ><el-button
                    class="login-password-toggle"
                    text
                    native-type="button"
                    :disabled="loading"
                    :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
                    :aria-pressed="passwordVisible"
                    @click="passwordVisible = !passwordVisible"
                    ><AppIcon
                      :name="passwordVisible ? 'eye-off' : 'eye'"
                      :size="17" /></el-button></template></el-input
            ></label>
            <el-button class="login-submit" type="primary" native-type="submit" :loading="loading"
              ><span>{{ loading ? '正在登录…' : isAdmin ? '进入工作台' : '登录' }}</span
              ><AppIcon v-if="!loading" name="arrow-right" :size="17"
            /></el-button>
          </form>
          <p v-if="!isAdmin" class="login-register">
            还没有驿站账号？<router-link to="/register"
              >创建账号<AppIcon name="move-up-right" :size="12"
            /></router-link>
          </p>
        </div>
        <p class="login-panel-bottom">
          <AppIcon name="shield-check" :size="14" />仅供本人及授权工作人员访问
        </p>
      </section>
    </div>
    <footer class="login-footer">
      <span>校园快递驿站 · 让每一份快递，安心到达</span><span>CAMPUS PARCEL STATION</span>
    </footer>
  </main>
</template>
