/**
 * PurchaseRulesFeedback Component Tests
 *
 * Tests for the purchase rules feedback display and violation detection.
 * Validates: Requirements 5.7–5.10
 */

import React from 'react';
import { render, screen, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      if (params) {
        return Object.entries(params).reduce(
          (str, [k, v]) => str.replace(`{{${k}}}`, String(v)),
          key
        );
      }
      return key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Alert: ({ children, status, ...props }: any) => (
    <div data-testid={`alert-${status}`} role="alert" {...props}>
      {children}
    </div>
  ),
  AlertIcon: () => <span data-testid="alert-icon" />,
  VStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Text: ({ children, ...props }: any) => <span {...props}>{children}</span>,
}));

import PurchaseRulesFeedback, {
  PurchaseRulesFeedbackProps,
} from '../components/PurchaseRulesFeedback';

const renderComponent = (props: Partial<PurchaseRulesFeedbackProps> = {}) => {
  const defaultProps: PurchaseRulesFeedbackProps = {
    rules: {},
    requestedQuantity: 1,
    memberOrderTotal: 0,
    clubOrderTotal: 0,
    hasMembership: true,
    onViolation: jest.fn(),
    ...props,
  };

  let result: ReturnType<typeof render>;
  act(() => {
    result = render(<PurchaseRulesFeedback {...defaultProps} />);
  });
  return result!;
};

describe('PurchaseRulesFeedback', () => {
  describe('max_per_order', () => {
    it('displays violation when requested quantity exceeds max_per_order', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_order: 3 },
        requestedQuantity: 5,
        onViolation,
      });

      expect(screen.getByText('purchase_rules.max_per_order')).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(true);
    });

    it('does not display violation when quantity is within limit', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_order: 5 },
        requestedQuantity: 3,
        onViolation,
      });

      expect(screen.queryByText('purchase_rules.max_per_order')).not.toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(false);
    });

    it('does not display violation when quantity equals max_per_order', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_order: 3 },
        requestedQuantity: 3,
        onViolation,
      });

      expect(screen.queryByText('purchase_rules.max_per_order')).not.toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(false);
    });
  });

  describe('max_per_member', () => {
    it('displays violation when member total + requested exceeds max_per_member', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_member: 5 },
        requestedQuantity: 3,
        memberOrderTotal: 4,
        onViolation,
      });

      expect(
        screen.getByText('purchase_rules.max_per_member')
      ).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(true);
    });

    it('displays info message when member is within limit', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_member: 10 },
        requestedQuantity: 2,
        memberOrderTotal: 3,
        onViolation,
      });

      expect(
        screen.getByText('purchase_rules.max_per_member')
      ).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(false);
    });

    it('shows 0 remaining when member has exactly reached the limit', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_member: 5 },
        requestedQuantity: 1,
        memberOrderTotal: 5,
        onViolation,
      });

      expect(
        screen.getByText('purchase_rules.max_per_member')
      ).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(true);
    });
  });

  describe('max_per_club', () => {
    it('displays violation when club total + requested exceeds max_per_club', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_club: 20 },
        requestedQuantity: 5,
        clubOrderTotal: 18,
        onViolation,
      });

      expect(
        screen.getByText('purchase_rules.max_per_club')
      ).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(true);
    });

    it('displays info message when club is within limit', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { max_per_club: 20 },
        requestedQuantity: 2,
        clubOrderTotal: 5,
        onViolation,
      });

      expect(
        screen.getByText('purchase_rules.max_per_club')
      ).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(false);
    });
  });

  describe('requires_membership', () => {
    it('displays error when membership is required but user lacks it', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { requires_membership: true },
        hasMembership: false,
        onViolation,
      });

      expect(
        screen.getByText('purchase_rules.requires_membership')
      ).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(true);
    });

    it('does not display error when membership is required and user has it', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { requires_membership: true },
        hasMembership: true,
        onViolation,
      });

      expect(
        screen.queryByText('purchase_rules.requires_membership')
      ).not.toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(false);
    });

    it('does not display error when requires_membership is false', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: { requires_membership: false },
        hasMembership: false,
        onViolation,
      });

      expect(
        screen.queryByText('purchase_rules.requires_membership')
      ).not.toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(false);
    });
  });

  describe('multiple violations', () => {
    it('reports violation when any rule is violated', () => {
      const onViolation = jest.fn();
      renderComponent({
        rules: {
          max_per_order: 2,
          max_per_member: 5,
          requires_membership: true,
        },
        requestedQuantity: 3,
        memberOrderTotal: 4,
        hasMembership: false,
        onViolation,
      });

      expect(screen.getByText('purchase_rules.max_per_order')).toBeInTheDocument();
      expect(
        screen.getByText('purchase_rules.max_per_member')
      ).toBeInTheDocument();
      expect(
        screen.getByText('purchase_rules.requires_membership')
      ).toBeInTheDocument();
      expect(onViolation).toHaveBeenCalledWith(true);
    });
  });

  describe('no rules', () => {
    it('renders nothing when no rules are defined', () => {
      const onViolation = jest.fn();
      const { container } = renderComponent({
        rules: {},
        onViolation,
      });

      expect(container.firstChild).toBeNull();
      expect(onViolation).toHaveBeenCalledWith(false);
    });
  });

  describe('alert severity', () => {
    it('uses error status for membership violations', () => {
      renderComponent({
        rules: { requires_membership: true },
        hasMembership: false,
        onViolation: jest.fn(),
      });

      expect(screen.getByTestId('alert-error')).toBeInTheDocument();
    });

    it('uses warning status for quantity violations', () => {
      renderComponent({
        rules: { max_per_order: 2 },
        requestedQuantity: 5,
        onViolation: jest.fn(),
      });

      expect(screen.getByTestId('alert-warning')).toBeInTheDocument();
    });

    it('uses info status for non-violated limits', () => {
      renderComponent({
        rules: { max_per_member: 10 },
        requestedQuantity: 1,
        memberOrderTotal: 0,
        onViolation: jest.fn(),
      });

      expect(screen.getByTestId('alert-info')).toBeInTheDocument();
    });
  });
});
