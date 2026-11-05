import { ElMessage } from 'element-plus';
import 'element-plus/es/components/message/style/css';
import { computed, defineComponent, h, markRaw, ref } from 'vue';
import AppIcon from '../components/AppIcon.vue';

const messageIcons = {
  success: markRaw(defineComponent(() => () => h(AppIcon, { name: 'circle-check' }))),
  error: markRaw(defineComponent(() => () => h(AppIcon, { name: 'triangle-alert' }))),
};

// Retain message state for page rendering, and show every nonempty assignment,
// including repeated validation failures with identical text.
export function useMessageState(type: 'success' | 'error') {
  const state = ref('');
  return computed({
    get: () => state.value,
    set: (message: string) => {
      state.value = message;
      if (message)
        ElMessage({
          type,
          message,
          icon: messageIcons[type],
          showClose: true,
          duration: type === 'error' ? 5000 : 3500,
          grouping: true,
        });
    },
  });
}
