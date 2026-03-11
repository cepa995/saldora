/**
 * Organization-scoped path utilities.
 *
 * Provides a hook to build URLs prefixed with the current
 * organization slug, e.g. "/kompanija/dashboard".
 */

import { useAuth } from "@/contexts/AuthContext";

/**
 * Hook that returns a function to build org-scoped paths.
 *
 * Falls back to the raw path if no slug is available.
 */
export function useOrgPath() {
  const { user } = useAuth();
  const slug = user?.orgSlug;

  return (path: string): string => {
    if (!slug) return path;
    return `/${slug}${path}`;
  };
}
