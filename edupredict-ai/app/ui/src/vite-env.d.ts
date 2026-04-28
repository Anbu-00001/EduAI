/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE: string
  readonly VITE_JANPARICHAY_CLIENT_ID: string
  readonly VITE_JANPARICHAY_REDIRECT_URI: string
  readonly VITE_HASH_SALT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
