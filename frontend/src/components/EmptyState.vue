<script setup lang="ts">
import AppIcon from './AppIcon.vue';
defineProps<{ title: string; description?: string }>();
</script>
<template>
  <div class="empty-state">
    <span class="empty-icon"><AppIcon name="inbox" :size="30" /></span>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <slot />
  </div>
</template>
