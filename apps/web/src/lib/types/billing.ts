/**
 * TypeScript interfaces for billing and subscription data.
 */

export interface SubscriptionInfo {
  plan: 'free' | 'starter' | 'pro' | 'agency';
  plan_limit: number | null;
  monthly_usage: number;
  organization_name: string;
  features: string[];
  subscription_status: string | null;
}
