/**
 * TypeScript interfaces for billing and subscription data.
 */

export interface SubscriptionInfo {
  plan: 'free' | 'starter' | 'professional' | 'enterprise';
  plan_limit: number | null;
  monthly_usage: number;
  organization_name: string;
}
