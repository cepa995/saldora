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
  paddle_customer_id: string | null;
}

export interface BillingConfig {
  paddle_environment: string;
  paddle_client_token: string;
  prices: Record<string, string | null>;
}

export interface CheckoutSettings {
  price_id: string;
  customer_email: string | null;
  customer_id: string | null;
  custom_data: Record<string, string>;
}
