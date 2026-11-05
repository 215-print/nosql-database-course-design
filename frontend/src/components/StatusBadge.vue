<script setup lang="ts">
import { computed } from 'vue';
import { isTrue } from '../utils/format';
const props = defineProps<{ status: string; abnormal?: unknown }>();
const label = computed(() => (isTrue(props.abnormal) ? '异常' : props.status));
const tone = computed(() =>
  label.value === '异常' || label.value === '黑名单'
    ? 'danger'
    : ['待取件', '待揽收'].includes(label.value)
      ? 'warning'
      : ['已取件', '正常'].includes(label.value)
        ? 'success'
        : 'neutral'
);
</script>
<template>
  <span class="status-badge" :class="`status-${tone}`"
    ><span aria-hidden="true"></span>{{ label }}</span
  >
</template>
