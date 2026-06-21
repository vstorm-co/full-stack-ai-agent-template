export type OrgRole = "owner" | "admin" | "member";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  avatar_url: string | null;
  is_personal: boolean;
  owner_id: string;
  stripe_customer_id: string | null;
  subscription_tier: string;
  seats_limit: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface OrganizationMember {
  id: string;
  organization_id: string;
  user_id: string;
  role: OrgRole;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  joined_at: string;
}

export interface OrganizationMemberList {
  items: OrganizationMember[];
  total: number;
}

export interface Invitation {
  id: string;
  organization_id: string;
  email: string;
  role: OrgRole;
  status: "pending" | "accepted" | "expired" | "revoked";
  token: string;
  expires_at: string | null;
  created_at: string;
}

export interface InvitationList {
  items: Invitation[];
  total: number;
}

export interface OrganizationList {
  items: Organization[];
  total: number;
}

export interface CreateOrganizationInput {
  name: string;
  slug?: string;
}

export interface InviteMemberInput {
  email: string;
  role: OrgRole;
}
