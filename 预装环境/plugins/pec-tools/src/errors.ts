export type ToolErrorCode =
  | 'NOT_FOUND' | 'INVALID_ARGUMENT' | 'POLICY_DENIED'
  | 'UPSTREAM_TIMEOUT' | 'NOT_IMPLEMENTED'

export class ToolError extends Error {
  constructor(readonly code: ToolErrorCode, message: string, readonly detail?: unknown) {
    super(message)
  }
}
