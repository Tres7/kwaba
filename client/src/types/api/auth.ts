export type AuthUser = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  phone?: string | null;
  avatar_url?: string | null;
  is_verified: boolean;
  is_active: boolean;
};

export type BackendAuthResponse  = {
  access: string;
  refresh: string;
  user: AuthUser;
};

