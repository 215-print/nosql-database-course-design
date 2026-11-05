<script setup lang="ts">
import AppIcon from './AppIcon.vue';
import type { icons } from '../assets/icons';
defineProps<{
  label: string;
  value: number | string;
  icon: keyof typeof icons;
  note?: string;
  tone?: 'brand' | 'warning';
}>();
</script>
<template>
  <article class="stat-card" :class="tone && `stat-${tone}`">
    <div class="stat-top">
      <span>{{ label }}</span
      ><AppIcon :name="icon" />
    </div>
    <strong>{{ value }}</strong>
    <p v-if="note">{{ note }}</p>
  </article>
</template>
