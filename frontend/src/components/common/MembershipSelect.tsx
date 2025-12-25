import React, { useState, useEffect, ChangeEvent } from 'react';
import { Select, SelectProps } from '@chakra-ui/react';
import { getAuthHeadersForGet } from '../../utils/authHeaders';

interface Membership {
  membership_id?: string;
  id?: string;
  name: string;
  price: number;
}

interface MembershipSelectProps extends Omit<SelectProps, 'onChange'> {
  value?: string;
  onChange?: (event: ChangeEvent<HTMLSelectElement>) => void;
  name?: string;
  placeholder?: string;
}

function MembershipSelect({ 
  value, 
  onChange, 
  name, 
  placeholder, 
  ...props 
}: MembershipSelectProps) {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMemberships();
  }, []);

  const loadMemberships = async () => {
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/memberships`, {
        headers
      });
      if (response.ok) {
        const data: Membership[] = await response.json();
        setMemberships(data);
      }
    } catch (error) {
      console.error('Error loading memberships:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLSelectElement>) => {
    if (onChange) {
      onChange(e);
    }
  };

  if (loading) {
    return (
      <Select placeholder="Laden..." disabled {...props}>
        <option>Lidmaatschappen laden...</option>
      </Select>
    );
  }

  return (
    <Select
      value={value}
      onChange={handleChange}
      name={name}
      placeholder={placeholder}
      {...props}
    >
      {memberships.map((membership) => (
        <option key={membership.membership_id || membership.id} value={membership.name}>
          {membership.name} - €{membership.price}
        </option>
      ))}
    </Select>
  );
}

export default MembershipSelect;