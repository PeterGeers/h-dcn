/**
 * WelcomePackList
 *
 * Tab component listing members with welcome_pack_status=pending.
 * Shows name, address, lidnummer, activation date.
 * Provides "Sent" button per row and bulk "Mark as sent".
 *
 * Validates: Requirements 5.4
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Button,
  Text,
  Spinner,
  VStack,
  HStack,
  Badge,
  useToast,
  Alert,
  AlertIcon,
  Checkbox,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';
import { apiCall } from '../../../utils/errorHandler';

interface WelcomePackMember {
  member_id: string;
  voornaam?: string;
  tussenvoegsel?: string;
  achternaam?: string;
  lidnummer?: string;
  straat?: string;
  huisnummer?: string;
  postcode?: string;
  woonplaats?: string;
  postadres?: string;
  postpostcode?: string;
  postwoonplaats?: string;
  welcome_pack_status?: string;
  welcome_pack_notes?: string;
  ingangsdatum?: string;
}

function WelcomePackList() {
  const { t } = useTranslation('workflows');
  const [members, setMembers] = useState<WelcomePackMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [markingIds, setMarkingIds] = useState<Set<string>>(new Set());
  const toast = useToast();

  const loadPendingMembers = useCallback(async () => {
    try {
      setLoading(true);
      const headers = await getAuthHeaders();
      const response = await apiCall<{ members: WelcomePackMember[] }>(
        fetch(API_URLS.members(), {
          method: 'GET',
          headers,
        }),
        'laden welkomstpakketten'
      );
      // Filter for pending welcome packs
      const pending = (response.members || response as any || []).filter(
        (m: WelcomePackMember) => m.welcome_pack_status === 'pending'
      );
      setMembers(pending);
    } catch (error) {
      console.error('[WelcomePackList] Error loading members:', error);
      toast({
        title: t('welcomePack.sentError'),
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  }, [t, toast]);

  useEffect(() => {
    loadPendingMembers();
  }, [loadPendingMembers]);

  const markAsSent = async (memberId: string) => {
    try {
      setMarkingIds(prev => new Set(prev).add(memberId));
      const headers = await getAuthHeaders();
      await apiCall<void>(
        fetch(API_URLS.member(memberId), {
          method: 'PUT',
          headers,
          body: JSON.stringify({
            welcome_pack_status: 'sent',
            welcome_pack_sent_date: new Date().toISOString().split('T')[0],
          }),
        }),
        'markeren als verzonden'
      );
      // Remove from list
      setMembers(prev => prev.filter(m => m.member_id !== memberId));
      setSelectedIds(prev => {
        const next = new Set(prev);
        next.delete(memberId);
        return next;
      });
      toast({
        title: t('welcomePack.sentSuccess'),
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('[WelcomePackList] Error marking as sent:', error);
      toast({
        title: t('welcomePack.sentError'),
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setMarkingIds(prev => {
        const next = new Set(prev);
        next.delete(memberId);
        return next;
      });
    }
  };

  const markBulkAsSent = async () => {
    const ids = Array.from(selectedIds);
    for (const id of ids) {
      await markAsSent(id);
    }
  };

  const toggleSelect = (memberId: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(memberId)) {
        next.delete(memberId);
      } else {
        next.add(memberId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === members.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(members.map(m => m.member_id)));
    }
  };

  const formatName = (m: WelcomePackMember): string => {
    const parts = [m.voornaam, m.tussenvoegsel, m.achternaam].filter(Boolean);
    return parts.join(' ') || '—';
  };

  const formatAddress = (m: WelcomePackMember): string => {
    // Prefer postal address, fall back to residential
    const straat = m.postadres || m.straat || '';
    const huisnummer = m.huisnummer || '';
    const postcode = m.postpostcode || m.postcode || '';
    const woonplaats = m.postwoonplaats || m.woonplaats || '';
    const line1 = [straat, huisnummer].filter(Boolean).join(' ');
    const line2 = [postcode, woonplaats].filter(Boolean).join(' ');
    return [line1, line2].filter(Boolean).join(', ') || '—';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minH="200px">
        <VStack spacing={4}>
          <Spinner size="lg" color="orange.500" />
          <Text>{t('welcomePack.sending')}</Text>
        </VStack>
      </Box>
    );
  }

  if (members.length === 0) {
    return (
      <Box p={6}>
        <Alert status="info">
          <AlertIcon />
          <Text>{t('welcomePack.empty')}</Text>
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={4}>
      <VStack spacing={4} align="stretch">
        {/* Bulk action bar */}
        {selectedIds.size > 0 && (
          <HStack spacing={4} p={3} bg="orange.50" borderRadius="md">
            <Text fontWeight="medium">
              {t('welcomePack.selected', { count: selectedIds.size })}
            </Text>
            <Button
              size="sm"
              colorScheme="orange"
              onClick={markBulkAsSent}
              isLoading={markingIds.size > 0}
            >
              {t('welcomePack.bulkMarkSent')}
            </Button>
          </HStack>
        )}

        {/* Table */}
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th w="40px">
                  <Checkbox
                    isChecked={selectedIds.size === members.length}
                    isIndeterminate={selectedIds.size > 0 && selectedIds.size < members.length}
                    onChange={toggleSelectAll}
                  />
                </Th>
                <Th>{t('welcomePack.columns.name')}</Th>
                <Th>{t('welcomePack.columns.memberNumber')}</Th>
                <Th>{t('welcomePack.columns.address')}</Th>
                <Th>{t('welcomePack.columns.activationDate')}</Th>
                <Th>{t('welcomePack.columns.action')}</Th>
                <Th></Th>
              </Tr>
            </Thead>
            <Tbody>
              {members.map(member => (
                <Tr
                  key={member.member_id}
                  bg={member.welcome_pack_notes ? 'orange.50' : undefined}
                >
                  <Td>
                    <Checkbox
                      isChecked={selectedIds.has(member.member_id)}
                      onChange={() => toggleSelect(member.member_id)}
                    />
                  </Td>
                  <Td>{formatName(member)}</Td>
                  <Td>{member.lidnummer || '—'}</Td>
                  <Td>{formatAddress(member)}</Td>
                  <Td>{member.ingangsdatum || '—'}</Td>
                  <Td>
                    {member.welcome_pack_notes && (
                      <Badge colorScheme="orange" fontSize="xs">
                        {member.welcome_pack_notes}
                      </Badge>
                    )}
                  </Td>
                  <Td>
                    <Button
                      size="xs"
                      colorScheme="green"
                      onClick={() => markAsSent(member.member_id)}
                      isLoading={markingIds.has(member.member_id)}
                    >
                      {t('welcomePack.markSent')}
                    </Button>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </VStack>
    </Box>
  );
}

export default WelcomePackList;
