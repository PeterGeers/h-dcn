import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, VStack, HStack, Heading, Text, Table, Thead, Tbody, Tr, Th, Td,
  Button, Input, Checkbox, useToast, Spinner, Alert, AlertIcon,
  Badge, Flex, Spacer, InputGroup, InputRightElement,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  useDisclosure,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { getAuthHeadersForGet } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';

interface MemberAccess {
  member_id: string;
  email?: string;
  member_type?: string;
  name?: string;
}

interface EventAccessManagerProps {
  eventId: string;
  eventName?: string;
}

/**
 * EventAccessManager — Admin component to manage member access to an event.
 *
 * Features:
 * - Lists members with access to the selected event
 * - Grant access to new members by email
 * - Row click opens access detail modal with Revoke action
 * - Bulk grant/revoke access (select multiple + action)
 */
const EventAccessManager: React.FC<EventAccessManagerProps> = ({ eventId, eventName }) => {
  const { t } = useTranslation('eventBooking');
  const toast = useToast();

  const [members, setMembers] = useState<MemberAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [grantEmail, setGrantEmail] = useState('');
  const [granting, setGranting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkProcessing, setBulkProcessing] = useState(false);
  const [selectedMember, setSelectedMember] = useState<MemberAccess | null>(null);
  const [revoking, setRevoking] = useState(false);

  const { isOpen: isDetailOpen, onOpen: onDetailOpen, onClose: onDetailClose } = useDisclosure();

  const fetchMembers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(API_URLS.eventAccess(eventId), { headers });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setMembers(data.members || data || []);
    } catch (err: any) {
      setError(err.message || t('errors.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [eventId, t]);

  useEffect(() => {
    if (eventId) {
      fetchMembers();
    }
  }, [eventId, fetchMembers]);

  const handleGrant = async () => {
    if (!grantEmail.trim()) return;
    setGranting(true);
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(API_URLS.eventAccess(eventId), {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'grant', member_ids: [grantEmail.trim()] }),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.message || `HTTP ${response.status}`);
      }
      toast({
        title: t('admin.accessGranted'),
        status: 'success',
        duration: 3000,
      });
      setGrantEmail('');
      fetchMembers();
    } catch (err: any) {
      toast({
        title: t('admin.grantFailed'),
        description: err.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setGranting(false);
    }
  };

  const handleRevoke = async (memberId: string) => {
    setRevoking(true);
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(API_URLS.eventAccess(eventId), {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'revoke', member_ids: [memberId] }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      toast({
        title: t('admin.accessRevoked'),
        status: 'info',
        duration: 3000,
      });
      onDetailClose();
      fetchMembers();
    } catch (err: any) {
      toast({
        title: t('admin.revokeFailed'),
        description: err.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setRevoking(false);
    }
  };

  const handleBulkGrant = async () => {
    if (selectedIds.size === 0) return;
    setBulkProcessing(true);
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(API_URLS.eventAccess(eventId), {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'grant', member_ids: Array.from(selectedIds) }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      toast({
        title: t('admin.bulkGrantSuccess'),
        description: `${selectedIds.size} ${t('admin.membersUpdated')}`,
        status: 'success',
        duration: 3000,
      });
      setSelectedIds(new Set());
      fetchMembers();
    } catch (err: any) {
      toast({
        title: t('admin.bulkGrantFailed'),
        description: err.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setBulkProcessing(false);
    }
  };

  const handleBulkRevoke = async () => {
    if (selectedIds.size === 0) return;
    setBulkProcessing(true);
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(API_URLS.eventAccess(eventId), {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'revoke', member_ids: Array.from(selectedIds) }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      toast({
        title: t('admin.bulkRevokeSuccess'),
        description: `${selectedIds.size} ${t('admin.membersUpdated')}`,
        status: 'info',
        duration: 3000,
      });
      setSelectedIds(new Set());
      fetchMembers();
    } catch (err: any) {
      toast({
        title: t('admin.bulkRevokeFailed'),
        description: err.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setBulkProcessing(false);
    }
  };

  const toggleSelect = (memberId: string, e: React.MouseEvent | React.ChangeEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
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
      setSelectedIds(new Set(members.map((m) => m.member_id)));
    }
  };

  const openMemberModal = (member: MemberAccess) => {
    setSelectedMember(member);
    onDetailOpen();
  };

  if (loading) {
    return (
      <Box p={4} textAlign="center">
        <Spinner size="lg" color="orange.400" />
        <Text mt={2} color="gray.400">{t('admin.loadingAccess')}</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error" bg="red.900" color="white" borderRadius="md">
        <AlertIcon />
        {error}
      </Alert>
    );
  }

  return (
    <VStack spacing={5} align="stretch">
      <Flex align="center">
        <Heading size="md" color="orange.400">
          {t('admin.manageAccess')}
        </Heading>
        {eventName && (
          <Badge ml={3} colorScheme="orange" fontSize="sm">
            {eventName}
          </Badge>
        )}
        <Spacer />
        <Text color="gray.400" fontSize="sm">
          {members.length} {t('admin.membersWithAccess')}
        </Text>
      </Flex>

      {/* Grant access form */}
      <Box bg="gray.800" p={4} borderRadius="md">
        <Text color="gray.300" mb={2} fontWeight="bold">
          {t('admin.grantAccess')}
        </Text>
        <HStack>
          <InputGroup>
            <Input
              placeholder={t('admin.emailOrMemberId')}
              value={grantEmail}
              onChange={(e) => setGrantEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGrant()}
              bg="gray.700"
              color="white"
              borderColor="gray.600"
              _placeholder={{ color: 'gray.500' }}
            />
            <InputRightElement width="4.5rem">
              <Button
                h="1.75rem"
                size="sm"
                colorScheme="green"
                onClick={handleGrant}
                isLoading={granting}
                leftIcon={<AddIcon />}
              >
                {t('admin.grant')}
              </Button>
            </InputRightElement>
          </InputGroup>
        </HStack>
      </Box>

      {/* Bulk actions */}
      {selectedIds.size > 0 && (
        <HStack bg="gray.800" p={3} borderRadius="md">
          <Text color="gray.300" fontSize="sm">
            {selectedIds.size} {t('admin.selected')}
          </Text>
          <Spacer />
          <Button
            size="sm"
            colorScheme="red"
            variant="outline"
            onClick={handleBulkRevoke}
            isLoading={bulkProcessing}
          >
            {t('admin.revokeAccess')}
          </Button>
          <Button
            size="sm"
            colorScheme="green"
            onClick={handleBulkGrant}
            isLoading={bulkProcessing}
          >
            {t('admin.bulkGrant')}
          </Button>
        </HStack>
      )}

      {/* Members table */}
      {members.length === 0 ? (
        <Box p={4} bg="gray.800" borderRadius="md" textAlign="center">
          <Text color="gray.400">{t('admin.noMembersWithAccess')}</Text>
        </Box>
      ) : (
        <Box overflowX="auto">
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th color="gray.400" px={2}>
                  <Checkbox
                    isChecked={selectedIds.size === members.length && members.length > 0}
                    isIndeterminate={selectedIds.size > 0 && selectedIds.size < members.length}
                    onChange={toggleSelectAll}
                    colorScheme="orange"
                  />
                </Th>
                <Th color="gray.400">{t('admin.colMemberId')}</Th>
                <Th color="gray.400">{t('admin.colEmail')}</Th>
                <Th color="gray.400">{t('admin.colMemberType')}</Th>
              </Tr>
            </Thead>
            <Tbody>
              {members.map((member) => (
                <Tr
                  key={member.member_id}
                  onClick={() => openMemberModal(member)}
                  _hover={{ bg: 'gray.700', cursor: 'pointer' }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') openMemberModal(member);
                  }}
                >
                  <Td px={2} onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      isChecked={selectedIds.has(member.member_id)}
                      onChange={(e) => toggleSelect(member.member_id, e)}
                      colorScheme="orange"
                    />
                  </Td>
                  <Td color="white" fontSize="sm">{member.member_id}</Td>
                  <Td color="white" fontSize="sm">{member.email || '—'}</Td>
                  <Td>
                    <Badge
                      colorScheme={member.member_type === 'event_participant' ? 'purple' : 'green'}
                      fontSize="xs"
                    >
                      {member.member_type || 'hdcn_member'}
                    </Badge>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}

      {/* Access Detail Modal */}
      <Modal isOpen={isDetailOpen} onClose={onDetailClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>{t('admin.accessDetailTitle')}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedMember && (
              <VStack spacing={3} align="stretch">
                <HStack justify="space-between">
                  <Text fontWeight="medium">{t('admin.colMemberId')}</Text>
                  <Text>{selectedMember.member_id}</Text>
                </HStack>
                <HStack justify="space-between">
                  <Text fontWeight="medium">{t('admin.colEmail')}</Text>
                  <Text>{selectedMember.email || '—'}</Text>
                </HStack>
                <HStack justify="space-between">
                  <Text fontWeight="medium">{t('admin.colMemberType')}</Text>
                  <Badge
                    colorScheme={selectedMember.member_type === 'event_participant' ? 'purple' : 'green'}
                    fontSize="xs"
                  >
                    {selectedMember.member_type || 'hdcn_member'}
                  </Badge>
                </HStack>
                {selectedMember.name && (
                  <HStack justify="space-between">
                    <Text fontWeight="medium">{t('admin.colName')}</Text>
                    <Text>{selectedMember.name}</Text>
                  </HStack>
                )}
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onDetailClose}>
              {t('admin.claims.cancel')}
            </Button>
            <Button
              leftIcon={<DeleteIcon />}
              colorScheme="red"
              onClick={() => selectedMember && handleRevoke(selectedMember.member_id)}
              isLoading={revoking}
              isDisabled={revoking}
            >
              {t('admin.revokeAccess')}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </VStack>
  );
};

export default EventAccessManager;
