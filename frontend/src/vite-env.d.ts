/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EXCHANGE_APP_API_URL?: string
  readonly VITE_LOGISTICS_APP_API_URL?: string
  readonly VITE_PROVISIONING_SUPERVISOR_API_URL?: string
  readonly VITE_MAPPER_API_URL?: string
  readonly VITE_ALLOCATOR_API_URL?: string
  readonly VITE_DEPLOYER_API_URL?: string
  readonly DEV: boolean
  readonly PROD: boolean
  readonly MODE: string
  readonly BASE_URL: string
  readonly SSR: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
