<script setup lang="ts">
import AppIcon from './AppIcon.vue';
defineProps<{ dark?: boolean; subtitle?: string }>();
</script>
<template>
  <div class="brand" :class="{ 'brand-dark': dark }">
    <span class="brand-symbol"><AppIcon name="package" :size="25" /></span>
    <div>
      <strong>校园快递驿站</strong><small>{{ subtitle || '让每一份快递，安心到达' }}</small>
    </div>
  </div>
</template>
