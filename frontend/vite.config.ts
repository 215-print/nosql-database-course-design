import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';
import Components from 'unplugin-vue-components/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiPrefix = env.VITE_API_PREFIX || '/api';
  const isAdmin = mode === 'admin';

  return {
    base: env.VITE_BASE_PATH || '/',
    cacheDir: `node_modules/.vite-${mode}`,
    plugins: [
      vue(),
      tailwindcss(),
      Components({
        dts: 'src/types/components.d.ts',
        resolvers: [ElementPlusResolver({ importStyle: 'css' })],
      }),
    ],
    server: {
      host: '0.0.0.0',
      port: isAdmin ? 5174 : 5173,
      strictPort: true,
      proxy: {
        [apiPrefix]: {
          target: env.VITE_API_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
    preview: { host: '0.0.0.0', port: isAdmin ? 4174 : 4173 },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    },
  };
});
