interface ImportMetaEnv {
  /** Absolute API origin for deployments where the web app is not proxied to the API. */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
