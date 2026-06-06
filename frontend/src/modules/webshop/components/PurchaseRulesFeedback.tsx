import React, { useEffect, useMemo } from 'react';
import { Alert, AlertIcon, VStack, Text } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { PurchaseRules } from '../types/unifiedProduct.types';

export interface PurchaseRuleViolation {
  rule: 'max_per_order' | 'max_per_member' | 'max_per_club' | 'requires_membership';
  limit?: number;
  current?: number;
  remaining?: number;
}

export interface PurchaseRulesFeedbackProps {
  /** Purchase rules configured on the product */
  rules: PurchaseRules;
  /** Quantity the buyer wants to add/order */
  requestedQuantity: number;
  /** Total quantity this member already has across paid/pending orders */
  memberOrderTotal: number;
  /** Total quantity this member's club already has across paid/pending orders */
  clubOrderTotal: number;
  /** Whether the buyer has an active membership */
  hasMembership: boolean;
  /** Callback invoked when violation state changes (true = has violation) */
  onViolation: (hasViolation: boolean) => void;
}

/**
 * Evaluates purchase rules and returns any violations.
 */
export function evaluatePurchaseRules(
  rules: PurchaseRules | undefined,
  requestedQuantity: number,
  memberOrderTotal: number = 0,
  clubOrderTotal: number = 0,
  hasMembership: boolean = true
): PurchaseRuleViolation[] {
  if (!rules) return [];

  const violations: PurchaseRuleViolation[] = [];

  if (
    rules.max_per_order != null &&
    requestedQuantity > rules.max_per_order
  ) {
    violations.push({
      rule: 'max_per_order',
      limit: rules.max_per_order,
      current: requestedQuantity,
      remaining: rules.max_per_order,
    });
  }

  if (
    rules.max_per_member != null &&
    memberOrderTotal + requestedQuantity > rules.max_per_member
  ) {
    const remaining = Math.max(0, rules.max_per_member - memberOrderTotal);
    violations.push({
      rule: 'max_per_member',
      limit: rules.max_per_member,
      current: memberOrderTotal,
      remaining,
    });
  }

  if (
    rules.max_per_club != null &&
    clubOrderTotal + requestedQuantity > rules.max_per_club
  ) {
    const remaining = Math.max(0, rules.max_per_club - clubOrderTotal);
    violations.push({
      rule: 'max_per_club',
      limit: rules.max_per_club,
      current: clubOrderTotal,
      remaining,
    });
  }

  if (rules.requires_membership && !hasMembership) {
    violations.push({
      rule: 'requires_membership',
    });
  }

  return violations;
}

interface FeedbackMessage {
  text: string;
  status: 'warning' | 'error' | 'info';
}

/**
 * PurchaseRulesFeedback displays purchase rule violation messages and
 * informational limits. Calls onViolation(true) when any rule is violated
 * so the parent can disable the add-to-cart button.
 *
 * Requirements: 5.7–5.10
 */
const PurchaseRulesFeedback: React.FC<PurchaseRulesFeedbackProps> = ({
  rules,
  requestedQuantity,
  memberOrderTotal,
  clubOrderTotal,
  hasMembership,
  onViolation,
}) => {
  const { t } = useTranslation('webshop');

  const { violations, messages } = useMemo(() => {
    const violations: PurchaseRuleViolation[] = [];
    const messages: FeedbackMessage[] = [];

    // max_per_order check
    if (rules.max_per_order != null && requestedQuantity > rules.max_per_order) {
      violations.push({
        rule: 'max_per_order',
        limit: rules.max_per_order,
        current: requestedQuantity,
        remaining: rules.max_per_order,
      });
      messages.push({
        text: t('purchase_rules.max_per_order', { limit: rules.max_per_order }),
        status: 'warning',
      });
    }

    // max_per_member check
    if (rules.max_per_member != null) {
      const remaining = Math.max(0, rules.max_per_member - memberOrderTotal);
      if (memberOrderTotal + requestedQuantity > rules.max_per_member) {
        violations.push({
          rule: 'max_per_member',
          limit: rules.max_per_member,
          current: memberOrderTotal,
          remaining,
        });
        messages.push({
          text: t('purchase_rules.max_per_member', { remaining, limit: rules.max_per_member }),
          status: 'warning',
        });
      } else {
        messages.push({
          text: t('purchase_rules.max_per_member', { remaining, limit: rules.max_per_member }),
          status: 'info',
        });
      }
    }

    // max_per_club check
    if (rules.max_per_club != null) {
      const remaining = Math.max(0, rules.max_per_club - clubOrderTotal);
      if (clubOrderTotal + requestedQuantity > rules.max_per_club) {
        violations.push({
          rule: 'max_per_club',
          limit: rules.max_per_club,
          current: clubOrderTotal,
          remaining,
        });
        messages.push({
          text: t('purchase_rules.max_per_club', { remaining, limit: rules.max_per_club }),
          status: 'warning',
        });
      } else {
        messages.push({
          text: t('purchase_rules.max_per_club', { remaining, limit: rules.max_per_club }),
          status: 'info',
        });
      }
    }

    // requires_membership check
    if (rules.requires_membership && !hasMembership) {
      violations.push({
        rule: 'requires_membership',
      });
      messages.push({
        text: t('purchase_rules.requires_membership'),
        status: 'error',
      });
    }

    return { violations, messages };
  }, [rules, requestedQuantity, memberOrderTotal, clubOrderTotal, hasMembership, t]);

  const hasViolation = violations.length > 0;

  useEffect(() => {
    onViolation(hasViolation);
  }, [hasViolation, onViolation]);

  if (messages.length === 0) {
    return null;
  }

  return (
    <VStack spacing={2} align="stretch" w="100%">
      {messages.map((msg, index) => (
        <Alert
          key={index}
          status={msg.status}
          borderRadius="md"
          fontSize="sm"
          py={2}
          px={3}
        >
          <AlertIcon boxSize="16px" />
          <Text fontSize="sm">{msg.text}</Text>
        </Alert>
      ))}
    </VStack>
  );
};

export default PurchaseRulesFeedback;
