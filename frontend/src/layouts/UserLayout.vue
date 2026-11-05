<script setup lang="ts">
import { useRoute } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandMark from '../components/BrandMark.vue';
import { userNavigation } from '../router/navigation';
import { useSession } from '../composables/useSession';
const route = useRoute();
const { user, logout, syncProfile } = useSession();
syncProfile();
</script>
<template>
  <a class="skip-link" href="#main-content">跳转到主要内容</a>
  <div class="user-shell">
    <header class="user-header">
      <div class="user-header-inner">
        <router-link to="/user" aria-label="校园快递驿站首页"
          ><BrandMark subtitle="校园生活，轻松收寄"
        /></router-link>
        <nav class="desktop-user-nav" aria-label="用户导航">
          <router-link
            v-for="item in userNavigation"
            :key="item.path"
            :to="item.path"
            :class="{ selected: route.path === item.path }"
            ><AppIcon :name="item.icon" :size="18" />{{ item.title }}</router-link
          >
        </nav>
        <div class="flex items-center gap-2">
          <router-link to="/user/profile" class="avatar" aria-label="个人中心">{{
            (user.name || user.username || '同学').slice(0, 1)
          }}</router-link
          ><el-button text aria-label="退出登录" @click="logout"
            ><AppIcon name="log-out" :size="18"
          /></el-button>
        </div>
      </div>
    </header>
    <main id="main-content" class="user-content" tabindex="-1"><router-view /></main>
    <footer class="user-footer">校园快递驿站 · 让每一份快递，安心到达</footer>
    <nav class="mobile-user-nav" aria-label="底部导航">
      <router-link
        v-for="item in userNavigation"
        :key="item.path"
        :to="item.path"
        :class="{ selected: route.path === item.path }"
        ><AppIcon :name="item.icon" :size="22" /><span>{{ item.title }}</span></router-link
      >
    </nav>
  </div>
</template>
