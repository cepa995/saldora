/**
 * Paddle.js initialization and checkout helper.
 *
 * Matches the @paddle/paddle-js npm package behavior exactly:
 * - Loads the Paddle v2 script from CDN
 * - Uses window.PaddleBillingV1 (NOT window.Paddle) — this is what
 *   the official npm package does internally
 * - Calls Environment.set + Initialize on the correct instance
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

const PADDLE_CDN_URL = 'https://cdn.paddle.com/paddle/v2/paddle.js';
const PADDLE_INSTANCE_KEY = 'PaddleBillingV1';

let paddleInstance: any = null;
let loadPromise: Promise<any> | null = null;

declare global {
  interface Window {
    Paddle?: any;
    PaddleBillingV1?: any;
  }
}

/**
 * Load Paddle.js script from CDN and return the billing instance.
 * Uses window.PaddleBillingV1 (matching the official npm package).
 */
function loadPaddleScript(): Promise<any> {
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    if (typeof window === 'undefined') {
      resolve(null);
      return;
    }

    // Already loaded — return existing instance
    if (window[PADDLE_INSTANCE_KEY]) {
      resolve(window[PADDLE_INSTANCE_KEY]);
      return;
    }

    // Find existing script or inject new one
    let script = document.querySelector(
      `script[src="${PADDLE_CDN_URL}"]`,
    ) as HTMLScriptElement | null;

    if (!script) {
      script = document.createElement('script');
      script.src = PADDLE_CDN_URL;
      script.async = true;
      (document.head || document.body).appendChild(script);
    }

    script.addEventListener('load', () => {
      if (window[PADDLE_INSTANCE_KEY]) {
        resolve(window[PADDLE_INSTANCE_KEY]);
      } else {
        reject(new Error('Paddle.js not available after load'));
      }
    });

    script.addEventListener('error', () => {
      reject(new Error('Failed to load Paddle.js'));
    });
  });

  return loadPromise;
}

/**
 * Initialize Paddle.js with client-side token and environment.
 *
 * Loads the script from CDN, sets sandbox environment if needed,
 * and calls Paddle.Initialize(). Safe to call multiple times.
 */
export async function initPaddle(
  clientToken: string,
  environment: string,
): Promise<any> {
  if (paddleInstance) return paddleInstance;

  try {
    const paddle = await loadPaddleScript();
    if (!paddle) return null;

    if (environment === 'sandbox' && paddle.Environment) {
      paddle.Environment.set('sandbox');
    }

    if (paddle.Initialized) {
      paddle.Update({ token: clientToken });
    } else {
      paddle.Initialize({ token: clientToken });
    }

    paddleInstance = paddle;
    return paddle;
  } catch (error) {
    console.error('Failed to initialize Paddle:', error);
    return null;
  }
}

/**
 * Get the current Paddle instance, or null if not initialized.
 */
export function getPaddle(): any {
  return paddleInstance;
}

/**
 * Open the Paddle Checkout overlay.
 */
export function openCheckout(config: {
  priceId: string;
  customerEmail?: string;
  customerId?: string;
  customData?: Record<string, string>;
  successUrl?: string;
}): void {
  if (!paddleInstance) {
    console.error('Paddle not initialized');
    return;
  }

  paddleInstance.Checkout.open({
    items: [{ priceId: config.priceId, quantity: 1 }],
    customer: config.customerEmail
      ? { email: config.customerEmail }
      : undefined,
    customData: config.customData,
    settings: {
      displayMode: 'overlay',
      theme: 'light',
      locale: 'hr',
      ...(config.successUrl && { successUrl: config.successUrl }),
    },
  });
}
