<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import AppIcon from '../components/AppIcon.vue';
import BrandMark from '../components/BrandMark.vue';
import { adminNavigation } from '../router/navigation';
import { useSession } from '../composables/useSession';
const route = useRoute();
const drawerOpen = ref(false);
const { user, logout, syncProfile } = useSession();
syncProfile();
watch(
  () => route.path,
  () => {
    drawerOpen.value = false;
  }
);
</script>
<template>
  <a class="skip-link" href="#main-content">跳转到主要内容</a>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <BrandMark dark subtitle="驿站运营管理台" />
      <p class="nav-caption">工作空间</p>
      <nav aria-label="管理导航" class="side-nav">
        <router-link
          v-for="item in adminNavigation"
          :key="item.path"
          :to="item.path"
          class="side-link"
          :class="{ selected: route.path === item.path }"
          ><AppIcon :name="item.icon" />{{ item.title
          }}<AppIcon
            v-if="route.path === item.path"
            name="chevron-right"
            :size="16"
            class="ml-auto"
        /></router-link>
      </nav>
      <div class="sidebar-footer">
        <AppIcon name="shield-check" />
        <div>
          <strong>管理员工作区</strong>
          <p>校园快递驿站</p>
        </div>
      </div>
    </aside>
    <div class="admin-main">
      <header class="admin-topbar">
        <div class="flex min-w-0 items-center gap-3">
          <el-button class="mobile-menu" aria-label="打开管理导航" @click="drawerOpen = true"
            ><AppIcon name="menu" /></el-button
          ><span class="topbar-context">驿站运营</span
          ><AppIcon name="chevron-right" :size="14" class="muted" /><span class="truncate">{{
            route.meta.title
          }}</span>
        </div>
        <div class="flex shrink-0 items-center gap-3">
          <span class="avatar small"><AppIcon name="user-round" :size="17" /></span
          ><span class="hidden text-sm sm:inline">{{ user.name || user.username || '管理员' }}</span
          ><el-button text aria-label="退出登录" @click="logout"
            ><AppIcon name="log-out" :size="18" /><span class="hidden sm:inline"
              >退出</span
            ></el-button
          >
        </div>
      </header>
      <main id="main-content" class="admin-content" tabindex="-1"><router-view /></main>
    </div>
    <el-drawer v-model="drawerOpen" title="驿站工作空间" direction="ltr" size="min(320px, 88vw)"
      ><nav class="drawer-nav" aria-label="管理导航">
        <router-link
          v-for="item in adminNavigation"
          :key="item.path"
          :to="item.path"
          :class="{ selected: route.path === item.path }"
          ><AppIcon :name="item.icon" />{{ item.title }}</router-link
        >
      </nav></el-drawer
    >
  </div>
</template>
