<script setup lang="ts">
import { Icon } from '@iconify/vue/offline';
import { icons } from '../assets/icons';
withDefaults(defineProps<{ name: keyof typeof icons; size?: number }>(), { size: 20 });
</script>
<template>
  <Icon :icon="icons[name]" :width="size" :height="size" aria-hidden="true" class="app-icon" />
</template>
