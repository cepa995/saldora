/**
 * Billing API service functions.
 *
 * Typed wrapper around apiClient for billing endpoints.
 */

import { apiClient } from '@/lib/api-client';
import type { SubscriptionInfo } from '@/lib/types/billing';

/**
 * Fetch the current subscription info and usage for the organization.
 *
 * @returns Current plan, monthly usage, and plan limit.
 */
export async function fetchSubscription(): Promise<SubscriptionInfo> {
  return apiClient<SubscriptionInfo>('/api/v1/billing/subscription');
}
