import { useState, useCallback } from 'react';
import { memberService } from '../services/api';
import { ApiService } from '../../../services/apiService';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
    family_name?: string;
    phone_number?: string;
    'custom:member_id'?: string;
  };
  username?: string;
}

export interface MemberInfo {
  member_id?: string;
  voornaam?: string;
  achternaam?: string;
  name?: string;
  straat?: string;
  postcode?: string;
  woonplaats?: string;
  email?: string;
  phone?: string;
}

interface UseWebshopUserReturn {
  userName: string;
  memberInfo: MemberInfo | null;
  currentMemberId: string | null;
  loadUserInfo: () => Promise<void>;
}

export function useWebshopUser(user: User): UseWebshopUserReturn {
  const [userName, setUserName] = useState<string>('Gebruiker');
  const [memberInfo, setMemberInfo] = useState<MemberInfo | null>(null);
  const [currentMemberId, setCurrentMemberId] = useState<string | null>(null);

  const loadUserInfo = useCallback(async () => {
    try {
      if (user) {
        const email = user.attributes?.email || user.username;
        const memberId = user.attributes?.['custom:member_id'];

        setUserName(email || 'Gebruiker');

        // Always try to get member by email first
        try {
          const response = await ApiService.get("/members/me");
          if (response.success && response.data) {
            const memberByEmail = response.data;

            if (memberByEmail) {
              const memberData: MemberInfo = {
                member_id: memberByEmail.member_id,
                voornaam: memberByEmail.voornaam,
                achternaam: memberByEmail.achternaam,
                name: memberByEmail.name,
                straat: memberByEmail.straat,
                postcode: memberByEmail.postcode,
                woonplaats: memberByEmail.woonplaats,
                email: memberByEmail.email,
                phone: memberByEmail.phone || memberByEmail.telefoon
              };

              setMemberInfo(memberData);
              setUserName(memberData.name || 'Gebruiker');
              setCurrentMemberId(memberByEmail.member_id);
              return;
            }
          }
        } catch (emailError) {
          console.error('Failed to load member by email:', emailError);
        }

        if (memberId) {
          setCurrentMemberId(memberId);
          try {
            const response = await memberService.getMember(memberId);
            const member = response.data;

            const memberData: MemberInfo = {
              member_id: memberId,
              voornaam: member.voornaam || user.attributes?.given_name || '',
              achternaam: member.achternaam || user.attributes?.family_name || '',
              name: member.name || `${member.voornaam || ''} ${member.achternaam || ''}`.trim(),
              straat: member.straat || '',
              postcode: member.postcode || '',
              woonplaats: member.woonplaats || '',
              email: member.email || user.attributes?.email || '',
              phone: member.phone || user.attributes?.phone_number || ''
            };

            setMemberInfo(memberData);
            setUserName(memberData.name || memberData.voornaam || email || 'Gebruiker');
          } catch (memberError) {
            console.error('Failed to load member data by ID:', memberError);

            const fallbackMember: MemberInfo = {
              member_id: memberId,
              voornaam: user.attributes?.given_name || '',
              achternaam: user.attributes?.family_name || '',
              name: `${user.attributes?.given_name || ''} ${user.attributes?.family_name || ''}`.trim(),
              straat: '',
              postcode: '',
              woonplaats: '',
              email: user.attributes?.email || '',
              phone: user.attributes?.phone_number || ''
            };
            setMemberInfo(fallbackMember);
            setUserName(fallbackMember.name || email || 'Gebruiker');
          }
        }
      }
    } catch (error) {
      setUserName('Gast');
    }
  }, [user]);

  return {
    userName,
    memberInfo,
    currentMemberId,
    loadUserInfo,
  };
}
