import type { Context } from '@deepseek-ai/cordis'

/** 示例：调用前统一做租户校验。候选人可扩展，不要削弱。 */
export function installGuard(ctx: Context, auditPath = './runs/audit.jsonl') {
  ctx.tools.guard((call, next) => {
    const tenant = ctx.session?.['tenantId'] as string | undefined
    const argTenant = (call.args as any)?.tenantId as string | undefined

    if (argTenant && tenant && argTenant !== tenant) {
      // 留痕：真实实现请写 audit.jsonl
      return { deny: 'POLICY_DENIED: 跨租户访问' }
    }
    return next()
  })
}
