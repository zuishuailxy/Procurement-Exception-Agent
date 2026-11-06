import type { Context } from '@deepseek-ai/cordis'
import { installGuard } from './policy/guard.js'
import { catalogTool } from './tools/catalog.js'
import { orderLookup, supplierProfile, pricingQuote, freightCalc, contractSearch, ticketSimilar } from './tools/business.js'

export const name = '@pec/pec-tools'

export function apply(ctx: Context) {
  for (const tool of [catalogTool, orderLookup, supplierProfile, pricingQuote, freightCalc, contractSearch, ticketSimilar]) {
    ctx.tools.register(tool)
  }
  installGuard(ctx)
}
