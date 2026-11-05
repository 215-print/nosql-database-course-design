<script setup lang="ts">
import { ref } from 'vue';
import AppIcon from './AppIcon.vue';
import { adminPickupPackage } from '../api/packages';
import type { PackageRecord } from '../types/api';
import { useMessageState } from '../composables/useMessageState';
import { errorText } from '../utils/format';

const pickupCode = ref('');
const pickingUp = ref(false);
const error = useMessageState('error');
const success = useMessageState('success');

async function submit() {
  if (pickingUp.value) return;
  const code = pickupCode.value.trim();
  if (!code) {
    error.value = '请输入取件码';
    return;
  }

  pickingUp.value = true;
  error.value = '';
  success.value = '';
  try {
    const picked = await adminPickupPackage({ pickup_code: code });
    pickupCode.value = '';
    success.value = `已完成代取：${picked.receiver_name || '包裹'}（${picked.tracking_number || picked.id}）`;
  } catch (e) {
    error.value = errorText(e);
  } finally {
    pickingUp.value = false;
  }
}
</script>

<template>
  <section class="panel mb-5">
    <div class="panel-header">
      <div>
        <h2 class="panel-title">输入取件码</h2>
        <p class="panel-description">输入用户提供的完整取件码，核验后办理包裹出库</p>
      </div>
      <AppIcon name="scan-line" class="muted" />
    </div>
    <form class="data-toolbar" @submit.prevent="submit">
      <label class="search-field">
        <span class="filter-label">取件码</span>
        <el-input
          v-model="pickupCode"
          autocomplete="off"
          placeholder="输入完整取件码，如 1-1-1234"
        >
          <template #prefix><AppIcon name="key-round" :size="16" /></template>
        </el-input>
      </label>
      <el-button type="primary" native-type="submit" :loading="pickingUp">
        确认取件
      </el-button>
    </form>
  </section>
</template>
