/**
 * Paddle.js initialization and checkout helper.
 *
 * Loads Paddle configuration from the API, initializes the Paddle
 * client with the correct environment and token, and provides
 * a helper to open the overlay checkout.
 */

declare global {
  interface Window {
    Paddle?: {
      Initialize: (config: {
        token: string;
        environment?: string;
      }) => void;
      Checkout: {
        open: (config: PaddleCheckoutConfig) => void;
      };
    };
  }
}

interface PaddleCheckoutConfig {
  items: Array<{ priceId: string; quantity: number }>;
  customer?: { email?: string; id?: string };
  customData?: Record<string, string>;
  settings?: {
    displayMode?: 'overlay' | 'inline';
    theme?: 'light' | 'dark';
    locale?: string;
    successUrl?: string;
  };
}

let initialized = false;

/**
 * Initialize Paddle.js with client-side token and environment.
 *
 * Safe to call multiple times — will only initialize once.
 */
export function initializePaddle(
  clientToken: string,
  environment: string,
): void {
  if (initialized || !window.Paddle) return;
  window.Paddle.Initialize({
    token: clientToken,
    environment: environment === 'sandbox' ? 'sandbox' : undefined,
  });
  initialized = true;
}

/**
 * Open the Paddle Checkout overlay.
 *
 * @param config Checkout configuration with price ID, customer info, and custom data.
 */
export function openCheckout(config: {
  priceId: string;
  customerEmail?: string;
  customerId?: string;
  customData?: Record<string, string>;
  successUrl?: string;
}): void {
  if (!window.Paddle) {
    console.error('Paddle.js not loaded');
    return;
  }

  const checkoutConfig: PaddleCheckoutConfig = {
    items: [{ priceId: config.priceId, quantity: 1 }],
    settings: {
      displayMode: 'overlay',
      theme: 'light',
      successUrl: config.successUrl,
    },
  };

  if (config.customerEmail || config.customerId) {
    checkoutConfig.customer = {};
    if (config.customerEmail) {
      checkoutConfig.customer.email = config.customerEmail;
    }
    if (config.customerId) {
      checkoutConfig.customer.id = config.customerId;
    }
  }

  if (config.customData) {
    checkoutConfig.customData = config.customData;
  }

  window.Paddle.Checkout.open(checkoutConfig);
}
