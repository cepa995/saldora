/**
 * Team member type definitions.
 */

export interface TeamMember {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: 'admin' | 'manager' | 'operator' | 'viewer';
  email_verified: boolean;
  created_at: string;
}
