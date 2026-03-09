/**
 * Billing API service functions.
 *
 * Typed wrapper around apiClient for billing, checkout, and Paddle config endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type {
  BillingConfig,
  CheckoutSettings,
  SubscriptionInfo,
} from '@/lib/types/billing';

/**
 * Fetch the current subscription info and usage for the organization.
 *
 * @returns Current plan, monthly usage, and plan limit.
 */
export async function fetchSubscription(): Promise<SubscriptionInfo> {
  return apiClient<SubscriptionInfo>('/api/v1/billing/subscription');
}

/**
 * Fetch public Paddle billing configuration (no auth required).
 *
 * @returns Paddle environment, client token, and price ID mapping.
 */
export async function fetchBillingConfig(): Promise<BillingConfig> {
  return apiClient<BillingConfig>('/api/v1/billing/config', {}, true);
}

/**
 * Generate checkout settings for a plan upgrade.
 *
 * @param tier - Target plan tier (starter, pro, agency).
 * @param interval - Billing interval (monthly or annual).
 * @returns Paddle checkout settings including price_id and customer info.
 */
export async function createCheckout(
  tier: string,
  interval: string,
): Promise<CheckoutSettings> {
  return apiClient<CheckoutSettings>('/api/v1/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({ tier, interval }),
  });
}

/**
 * Request subscription cancellation via Paddle.
 *
 * @returns Confirmation status.
 */
export async function cancelSubscription(): Promise<{ status: string }> {
  return apiClient<{ status: string }>('/api/v1/billing/cancel', {
    method: 'POST',
  });
}
