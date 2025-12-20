// Member type definitions

export interface Member {
  id: string;
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  region?: string;
  membershipType?: string;
  status: 'active' | 'inactive' | 'pending';
  createdAt: string;
  updatedAt: string;
}

export interface MemberFormData {
  username: string;
  email: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  region?: string;
  membershipType?: string;
  tempPassword?: string;
  groups?: string;
}

export interface MemberListProps {
  members: Member[];
  onEdit: (member: Member) => void;
  onDelete: (memberId: string) => void;
}

export interface MemberCardProps {
  member: Member;
  onSelect?: (member: Member) => void;
}