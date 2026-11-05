/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly MODE: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_APP_VERSION: string;
  readonly VITE_APP_MODE: 'user' | 'admin';
  readonly VITE_APP_TITLE: string;
  readonly VITE_API_PREFIX: string;
  readonly VITE_API_TARGET: string;
  readonly VITE_BASE_PATH: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
