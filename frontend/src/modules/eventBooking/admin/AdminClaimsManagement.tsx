import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Button,
  HStack,
  VStack,
  Text,
  Heading,
  Spinner,
  Input,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  useDisclosure,
  useToast,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  FormControl,
  FormLabel,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { getAuthHeaders } from '../../../utils/authHeaders';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

// --- Types ---

interface ClaimEntry {
  row_id: string;
  label: string;
  status: 'available' | 'claimed' | 'pending';
  delegate_name?: string;
  delegate_email?: string;
  claimed_at?: string;
}

interface PaginationInfo {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

interface ClaimsResponse {
  claims: ClaimEntry[];
  pagination: PaginationInfo;
  row_label: string;
}

// --- API helpers ---

async function fetchClaims(eventId: string, page: number): Promise<ClaimsResponse> {
  const headers = await getAuthHeaders();
  const response = await axios.get<ClaimsResponse>(
    `${BASE_URL}/admin/events/${encodeURIComponent(eventId)}/claims`,
    { headers, params: { page } }
  );
  return response.data;
}

async function releaseClaim(eventId: string, rowId: string): Promise<void> {
  const headers = await getAuthHeaders();
  await axios.delete(
    `${BASE_URL}/admin/events/${encodeURIComponent(eventId)}/claims/${encodeURIComponent(rowId)}`,
    { headers }
  );
}

async function assignClaim(
  eventId: string,
  rowId: string,
  email: string
): Promise<void> {
  const headers = await getAuthHeaders();
  await axios.post(
    `${BASE_URL}/admin/events/${encodeURIComponent(eventId)}/claims/${encodeURIComponent(rowId)}`,
    { email, action: 'assign' },
    { headers }
  );
}

async function reassignPrimary(
  eventId: string,
  rowId: string,
  email: string
): Promise<void> {
  const headers = await getAuthHeaders();
  await axios.post(
    `${BASE_URL}/admin/events/${encodeURIComponent(eventId)}/claims/${encodeURIComponent(rowId)}`,
    { email, action: 'reassign_primary' },
    { headers }
  );
}

async function removeSecondary(eventId: string, rowId: string): Promise<void> {
  const headers = await getAuthHeaders();
  await axios.post(
    `${BASE_URL}/admin/events/${encodeURIComponent(eventId)}/claims/${encodeURIComponent(rowId)}`,
    { action: 'remove_secondary' },
    { headers }
  );
}

async function cancelInvitation(eventId: string, rowId: string): Promise<void> {
  const headers = await getAuthHeaders();
  await axios.post(
    `${BASE_URL}/admin/events/${encodeURIComponent(eventId)}/claims/${encodeURIComponent(rowId)}`,
    { action: 'cancel_invitation' },
    { headers }
  );
}

// --- Component ---

interface AdminClaimsManagementProps {
  eventId: string;
}

/**
 * Admin Claims Management UI.
 *
 * Displays a paginated table of all registry rows with claim status,
 * and provides actions: release, assign, reassign primary, remove secondary,
 * cancel pending invitation.
 *
 * Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
 */
const AdminClaimsManagement: React.FC<AdminClaimsManagementProps> = ({ eventId }) => {
  const { t } = useTranslation('eventBooking');
  const toast = useToast();

  // --- State ---
  const [claims, setClaims] = useState<ClaimEntry[]>([]);
  const [pagination, setPagination] = useState<PaginationInfo | null>(null);
  const [, setRowLabel] = useState<string>('row');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  // Release confirmation dialog
  const {
    isOpen: isReleaseOpen,
    onOpen: onReleaseOpen,
    onClose: onReleaseClose,
  } = useDisclosure();
  const [releaseTarget, setReleaseTarget] = useState<ClaimEntry | null>(null);
  const [releaseLoading, setReleaseLoading] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Assign modal
  const {
    isOpen: isAssignOpen,
    onOpen: onAssignOpen,
    onClose: onAssignClose,
  } = useDisclosure();
  const [assignTarget, setAssignTarget] = useState<ClaimEntry | null>(null);
  const [assignEmail, setAssignEmail] = useState('');
  const [assignLoading, setAssignLoading] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  // Reassign primary modal
  const {
    isOpen: isReassignOpen,
    onOpen: onReassignOpen,
    onClose: onReassignClose,
  } = useDisclosure();
  const [reassignTarget, setReassignTarget] = useState<ClaimEntry | null>(null);
  const [reassignEmail, setReassignEmail] = useState('');
  const [reassignLoading, setReassignLoading] = useState(false);
  const [reassignError, setReassignError] = useState<string | null>(null);

  // --- Load claims ---
  const loadClaims = useCallback(async () => {
    if (!eventId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchClaims(eventId, currentPage);
      setClaims(data.claims);
      setPagination(data.pagination);
      setRowLabel(data.row_label);
    } catch (err) {
      setError(t('admin.claims.load_failed'));
    } finally {
      setLoading(false);
    }
  }, [eventId, currentPage, t]);

  useEffect(() => {
    loadClaims();
  }, [loadClaims]);

  // --- Release ---
  const handleReleaseClick = (claim: ClaimEntry) => {
    setReleaseTarget(claim);
    onReleaseOpen();
  };

  const handleReleaseConfirm = async () => {
    if (!releaseTarget) return;
    setReleaseLoading(true);
    try {
      await releaseClaim(eventId, releaseTarget.row_id);
      toast({
        title: t('admin.claims.release_success'),
        status: 'success',
        duration: 3000,
      });
      onReleaseClose();
      loadClaims();
    } catch (err) {
      toast({
        title: t('admin.claims.release_failed'),
        status: 'error',
        duration: 5000,
      });
    } finally {
      setReleaseLoading(false);
    }
  };

  // --- Assign ---
  const handleAssignClick = (claim: ClaimEntry) => {
    setAssignTarget(claim);
    setAssignEmail('');
    setAssignError(null);
    onAssignOpen();
  };

  const handleAssignConfirm = async () => {
    if (!assignTarget || !assignEmail.trim()) return;
    setAssignLoading(true);
    setAssignError(null);
    try {
      await assignClaim(eventId, assignTarget.row_id, assignEmail.trim());
      toast({
        title: t('admin.claims.assign_success'),
        status: 'success',
        duration: 3000,
      });
      onAssignClose();
      loadClaims();
    } catch (err: any) {
      const status = err?.response?.status;
      const message = err?.response?.data?.message || err?.response?.data?.error;
      if (status === 409) {
        setAssignError(t('admin.claims.already_claimed'));
      } else if (status === 404) {
        setAssignError(t('admin.claims.member_not_found'));
      } else {
        setAssignError(message || t('admin.claims.assign_failed'));
      }
    } finally {
      setAssignLoading(false);
    }
  };

  // --- Reassign primary ---
  const handleReassignClick = (claim: ClaimEntry) => {
    setReassignTarget(claim);
    setReassignEmail('');
    setReassignError(null);
    onReassignOpen();
  };

  const handleReassignConfirm = async () => {
    if (!reassignTarget || !reassignEmail.trim()) return;
    setReassignLoading(true);
    setReassignError(null);
    try {
      await reassignPrimary(eventId, reassignTarget.row_id, reassignEmail.trim());
      toast({
        title: t('admin.claims.reassign_success'),
        status: 'success',
        duration: 3000,
      });
      onReassignClose();
      loadClaims();
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 404) {
        setReassignError(t('admin.claims.member_not_found'));
      } else {
        setReassignError(t('admin.claims.reassign_failed'));
      }
    } finally {
      setReassignLoading(false);
    }
  };

  // --- Remove secondary ---
  const handleRemoveSecondary = async (claim: ClaimEntry) => {
    try {
      await removeSecondary(eventId, claim.row_id);
      toast({
        title: t('admin.claims.remove_secondary_success'),
        status: 'success',
        duration: 3000,
      });
      loadClaims();
    } catch (err) {
      toast({
        title: t('admin.claims.remove_secondary_failed'),
        status: 'error',
        duration: 5000,
      });
    }
  };

  // --- Cancel invitation ---
  const handleCancelInvitation = async (claim: ClaimEntry) => {
    try {
      await cancelInvitation(eventId, claim.row_id);
      toast({
        title: t('admin.claims.cancel_invitation_success'),
        status: 'success',
        duration: 3000,
      });
      loadClaims();
    } catch (err) {
      toast({
        title: t('admin.claims.cancel_invitation_failed'),
        status: 'error',
        duration: 5000,
      });
    }
  };

  // --- Pagination ---
  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  // --- Status badge ---
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'claimed':
        return <Badge colorScheme="green">{t('admin.claims.status_claimed')}</Badge>;
      case 'pending':
        return <Badge colorScheme="yellow">{t('admin.claims.status_pending')}</Badge>;
      default:
        return <Badge colorScheme="gray">{t('admin.claims.status_available')}</Badge>;
    }
  };

  // --- Format date ---
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  // --- Render ---
  if (loading && claims.length === 0) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="lg" />
        <Text mt={2}>{t('admin.claims.loading')}</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      <HStack justify="space-between">
        <Heading size="md">{t('admin.claims.title')}</Heading>
        <Button size="sm" onClick={loadClaims} isLoading={loading}>
          {t('admin.claims.refresh')}
        </Button>
      </HStack>

      {error && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}

      {/* Claims Table */}
      <Box overflowX="auto" bg="white" borderRadius="md" borderWidth={1}>
        <Table size="sm">
          <Thead>
            <Tr>
              <Th>{t('admin.claims.col_label')}</Th>
              <Th>{t('admin.claims.col_status')}</Th>
              <Th>{t('admin.claims.col_delegate')}</Th>
              <Th>{t('admin.claims.col_email')}</Th>
              <Th>{t('admin.claims.col_claimed_at')}</Th>
              <Th>{t('admin.claims.col_actions')}</Th>
            </Tr>
          </Thead>
          <Tbody>
            {claims.map((claim) => (
              <Tr key={claim.row_id}>
                <Td fontWeight="medium">{claim.label}</Td>
                <Td>{getStatusBadge(claim.status)}</Td>
                <Td>{claim.delegate_name || '-'}</Td>
                <Td>{claim.delegate_email || '-'}</Td>
                <Td>{formatDate(claim.claimed_at)}</Td>
                <Td>
                  {claim.status === 'claimed' ? (
                    <Menu>
                      <MenuButton
                        as={Button}
                        size="xs"
                        variant="outline"
                        aria-label={t('admin.claims.actions')}
                      >
                        ⋮
                      </MenuButton>
                      <MenuList>
                        <MenuItem onClick={() => handleReleaseClick(claim)}>
                          {t('admin.claims.action_release')}
                        </MenuItem>
                        <MenuItem onClick={() => handleReassignClick(claim)}>
                          {t('admin.claims.action_reassign')}
                        </MenuItem>
                        <MenuItem onClick={() => handleRemoveSecondary(claim)}>
                          {t('admin.claims.action_remove_secondary')}
                        </MenuItem>
                        <MenuItem onClick={() => handleCancelInvitation(claim)}>
                          {t('admin.claims.action_cancel_invitation')}
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  ) : (
                    <Button
                      size="xs"
                      colorScheme="blue"
                      onClick={() => handleAssignClick(claim)}
                    >
                      {t('admin.claims.action_assign')}
                    </Button>
                  )}
                </Td>
              </Tr>
            ))}
            {claims.length === 0 && !loading && (
              <Tr>
                <Td colSpan={6} textAlign="center" py={8}>
                  <Text color="gray.500">{t('admin.claims.no_rows')}</Text>
                </Td>
              </Tr>
            )}
          </Tbody>
        </Table>
      </Box>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <HStack justify="center" spacing={2}>
          <Button
            size="sm"
            isDisabled={currentPage <= 1}
            onClick={() => handlePageChange(currentPage - 1)}
          >
            {t('admin.claims.prev_page')}
          </Button>
          <Text fontSize="sm">
            {t('admin.claims.page_info', {
              page: currentPage,
              total: pagination.total_pages,
            })}
          </Text>
          <Button
            size="sm"
            isDisabled={currentPage >= pagination.total_pages}
            onClick={() => handlePageChange(currentPage + 1)}
          >
            {t('admin.claims.next_page')}
          </Button>
        </HStack>
      )}

      {/* Release Confirmation Dialog */}
      <AlertDialog
        isOpen={isReleaseOpen}
        leastDestructiveRef={cancelRef as React.RefObject<HTMLButtonElement>}
        onClose={onReleaseClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader>
              {t('admin.claims.release_confirm_title')}
            </AlertDialogHeader>
            <AlertDialogBody>
              {t('admin.claims.release_confirm_body', {
                label: releaseTarget?.label || '',
                email: releaseTarget?.delegate_email || '',
              })}
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onReleaseClose}>
                {t('admin.claims.cancel')}
              </Button>
              <Button
                colorScheme="red"
                onClick={handleReleaseConfirm}
                ml={3}
                isLoading={releaseLoading}
              >
                {t('admin.claims.release_confirm')}
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      {/* Assign Modal */}
      <Modal isOpen={isAssignOpen} onClose={onAssignClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {t('admin.claims.assign_title', { label: assignTarget?.label || '' })}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <FormControl>
              <FormLabel>{t('admin.claims.assign_email_label')}</FormLabel>
              <Input
                type="email"
                placeholder={t('admin.claims.assign_email_placeholder')}
                value={assignEmail}
                onChange={(e) => setAssignEmail(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAssignConfirm();
                }}
              />
            </FormControl>
            {assignError && (
              <Alert status="error" mt={3} borderRadius="md">
                <AlertIcon />
                {assignError}
              </Alert>
            )}
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onAssignClose}>
              {t('admin.claims.cancel')}
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleAssignConfirm}
              isLoading={assignLoading}
              isDisabled={!assignEmail.trim()}
            >
              {t('admin.claims.assign_confirm')}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Reassign Primary Modal */}
      <Modal isOpen={isReassignOpen} onClose={onReassignClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {t('admin.claims.reassign_title', { label: reassignTarget?.label || '' })}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <Text mb={3}>
              {t('admin.claims.reassign_description', {
                current: reassignTarget?.delegate_email || '',
              })}
            </Text>
            <FormControl>
              <FormLabel>{t('admin.claims.reassign_email_label')}</FormLabel>
              <Input
                type="email"
                placeholder={t('admin.claims.reassign_email_placeholder')}
                value={reassignEmail}
                onChange={(e) => setReassignEmail(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleReassignConfirm();
                }}
              />
            </FormControl>
            {reassignError && (
              <Alert status="error" mt={3} borderRadius="md">
                <AlertIcon />
                {reassignError}
              </Alert>
            )}
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onReassignClose}>
              {t('admin.claims.cancel')}
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleReassignConfirm}
              isLoading={reassignLoading}
              isDisabled={!reassignEmail.trim()}
            >
              {t('admin.claims.reassign_confirm')}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </VStack>
  );
};

export default AdminClaimsManagement;
