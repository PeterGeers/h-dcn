/**
 * Generic Email Service - Parameter-driven email utility for H-DCN Portal
 * 
 * This service provides a generic, reusable email system that can be used across
 * all modules (membership, webshop, events, etc.) with parameter-driven configuration.
 */

import { apiCall } from './errorHandler';
import { API_URLS } from '../config/api';
import { getAuthHeaders } from './authHeaders';

// ============================================================================
// GENERIC EMAIL INTERFACES
// ============================================================================

export interface EmailContext {
  [key: string]: any; // Allow any context variables for maximum flexibility
}

export interface EmailRecipients {
  admin: string[];
  cc?: string[];
  bcc?: string[];
}

export interface EmailNotificationConfig {
  enabled: boolean;
  templates: Record<string, string>;
  recipients: EmailRecipients;
  triggers: Record<string, boolean>;
}

export interface EmailOptions {
  template: string;
  recipient: string;
  cc?: string[];
  bcc?: string[];
  context: EmailContext;
}

export interface BulkEmailOptions {
  template: string;
  recipients: Array<{
    email: string;
    context: EmailContext;
  }>;
  cc?: string[];
  bcc?: string[];
}

// ============================================================================
// GENERIC EMAIL SERVICE
// ============================================================================

/**
 * Send a single email using a template
 */
export const sendEmail = async (options: EmailOptions): Promise<void> => {
  try {
    const emailData = {
      template: options.template,
      recipient: options.recipient,
      cc: options.cc,
      bcc: options.bcc,
      context: {
        ...options.context,
        // Add timestamp if not provided
        TIMESTAMP: options.context.TIMESTAMP || new Date().toISOString(),
        // Add formatted date if not provided
        FORMATTED_DATE: options.context.FORMATTED_DATE || new Date().toLocaleDateString('nl-NL', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        })
      }
    };

    await apiCall(
      fetch(`${API_URLS.base}/send-email`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(await getAuthHeaders())
        },
        body: JSON.stringify(emailData)
      }),
      `verzenden email (${options.template})`
    );

    console.log(`✅ Email sent: ${options.template} to ${options.recipient}`);
  } catch (error) {
    console.error(`Error sending email (${options.template}):`, error);
    throw error;
  }
};

/**
 * Send multiple emails efficiently
 */
export const sendBulkEmails = async (options: BulkEmailOptions): Promise<void> => {
  try {
    const emailPromises = options.recipients.map(recipient =>
      sendEmail({
        template: options.template,
        recipient: recipient.email,
        cc: options.cc,
        bcc: options.bcc,
        context: recipient.context
      })
    );

    await Promise.all(emailPromises);
    console.log(`✅ Bulk emails sent: ${options.template} to ${options.recipients.length} recipients`);
  } catch (error) {
    console.error(`Error sending bulk emails (${options.template}):`, error);
    throw error;
  }
};

/**
 * Send templated email to multiple recipients with same context
 */
export const sendTemplatedEmail = async (
  templateName: string,
  recipients: string[],
  context: EmailContext,
  options?: { cc?: string[]; bcc?: string[] }
): Promise<void> => {
  try {
    const emailPromises = recipients.map(recipient =>
      sendEmail({
        template: templateName,
        recipient,
        cc: options?.cc,
        bcc: options?.bcc,
        context
      })
    );

    await Promise.all(emailPromises);
    console.log(`✅ Templated emails sent: ${templateName} to ${recipients.length} recipients`);
  } catch (error) {
    console.error(`Error sending templated emails (${templateName}):`, error);
    throw error;
  }
};

/**
 * Send emails based on configuration and triggers
 */
export const sendConfiguredEmails = async (
  config: EmailNotificationConfig,
  triggerName: string,
  templateKey: string,
  context: EmailContext,
  recipientEmail?: string
): Promise<void> => {
  // Check if emails are enabled and trigger is active
  if (!config.enabled || !config.triggers[triggerName]) {
    console.log(`📧 Email disabled: ${triggerName} (${templateKey})`);
    return;
  }

  const templateName = config.templates[templateKey];
  if (!templateName) {
    console.error(`❌ Template not found: ${templateKey}`);
    return;
  }

  try {
    const emailPromises: Promise<void>[] = [];

    // Send to specific recipient if provided
    if (recipientEmail) {
      emailPromises.push(
        sendEmail({
          template: templateName,
          recipient: recipientEmail,
          context
        })
      );
    }

    // Send to admin recipients
    if (config.recipients.admin.length > 0) {
      emailPromises.push(
        sendTemplatedEmail(
          templateName,
          config.recipients.admin,
          context,
          {
            cc: config.recipients.cc,
            bcc: config.recipients.bcc
          }
        )
      );
    }

    await Promise.all(emailPromises);
    console.log(`✅ Configured emails sent: ${triggerName} (${templateName})`);
  } catch (error) {
    console.error(`Error sending configured emails (${triggerName}):`, error);
    throw error;
  }
};

// ============================================================================
// MEMBERSHIP-SPECIFIC EMAIL FUNCTIONS (using generic service)
// ============================================================================

/**
 * Send membership application confirmation email to the applicant
 */
export const sendMembershipApplicationConfirmation = async (
  applicantEmail: string,
  context: EmailContext
): Promise<void> => {
  return sendEmail({
    template: 'membership-application-confirmation',
    recipient: applicantEmail,
    context: {
      ...context,
      EMAIL: applicantEmail
    }
  });
};

/**
 * Send membership application notification email to administrators
 */
export const sendMembershipApplicationAdminNotification = async (
  context: EmailContext,
  config?: EmailNotificationConfig
): Promise<void> => {
  const defaultRecipients = ['ledenadministratie@h-dcn.nl'];
  const recipients = config?.recipients.admin || defaultRecipients;

  return sendTemplatedEmail(
    'membership-application-admin-notification',
    recipients,
    context,
    {
      cc: config?.recipients.cc,
      bcc: config?.recipients.bcc
    }
  );
};

/**
 * Send both confirmation and admin notification emails for a membership application
 */
export const sendMembershipApplicationEmails = async (
  memberData: any,
  config?: EmailNotificationConfig
): Promise<void> => {
  // Check if emails should be sent
  if (config && (!config.enabled || !config.triggers.onSubmission)) {
    console.log('📧 Membership application emails disabled in configuration');
    return;
  }

  try {
    // Prepare email context from member data
    const context: EmailContext = {
      DISPLAY_NAME: `${memberData.voornaam} ${memberData.tussenvoegsel || ''} ${memberData.achternaam}`.trim(),
      FULL_NAME: `${memberData.voornaam} ${memberData.tussenvoegsel || ''} ${memberData.achternaam}`.trim(),
      EMAIL: memberData.email,
      PHONE: memberData.telefoon,
      BIRTH_DATE: memberData.geboortedatum ? new Date(memberData.geboortedatum).toLocaleDateString('nl-NL') : '',
      
      // Address
      ADDRESS: `${memberData.straat || ''}`,
      CITY: memberData.woonplaats,
      POSTAL_CODE: memberData.postcode,
      COUNTRY: memberData.land,
      
      // Membership
      MEMBERSHIP_TYPE: memberData.lidmaatschap,
      REGION: memberData.regio,
      HOW_FOUND: memberData.wiewatwaar,
      MAGAZINE_PREFERENCE: memberData.clubblad,
      NEWSLETTER_PREFERENCE: memberData.nieuwsbrief,
      PRIVACY_CONSENT: memberData.privacy,
      
      // Motor information (if applicable)
      MOTOR_INFO: !!(memberData.motormerk || memberData.motortype),
      MOTOR_BRAND: memberData.motormerk,
      MOTOR_TYPE: memberData.motortype,
      MOTOR_YEAR: memberData.bouwjaar?.toString(),
      LICENSE_PLATE: memberData.kenteken,
      
      // Payment
      PAYMENT_METHOD: memberData.betaalwijze,
      IBAN: memberData.bankrekeningnummer,
      
      // System
      ORGANIZATION_WEBSITE: window.location.origin,
      APPLICATION_DATE: new Date().toLocaleDateString('nl-NL', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    };

    // Send both emails concurrently
    await Promise.all([
      sendMembershipApplicationConfirmation(memberData.email, context),
      sendMembershipApplicationAdminNotification(context, config)
    ]);

    console.log('✅ All membership application emails sent successfully');
  } catch (error) {
    console.error('Error sending membership application emails:', error);
    throw error;
  }
};

// ============================================================================
// WEBSHOP EMAIL FUNCTIONS (future use)
// ============================================================================

/**
 * Send order confirmation email (future implementation)
 */
export const sendOrderConfirmationEmail = async (
  customerEmail: string,
  orderData: any,
  config?: EmailNotificationConfig
): Promise<void> => {
  if (config && (!config.enabled || !config.triggers.onOrderPlaced)) {
    return;
  }

  const context: EmailContext = {
    CUSTOMER_NAME: orderData.customerName,
    ORDER_NUMBER: orderData.orderNumber,
    ORDER_TOTAL: orderData.total,
    ORDER_ITEMS: orderData.items,
    DELIVERY_ADDRESS: orderData.deliveryAddress,
    // ... other order-specific context
  };

  return sendEmail({
    template: config?.templates.orderConfirmation || 'order-confirmation',
    recipient: customerEmail,
    context
  });
};

// ============================================================================
// DEFAULT EXPORT WITH ALL METHODS
// ============================================================================

export const emailService = {
  // Generic methods
  sendEmail,
  sendBulkEmails,
  sendTemplatedEmail,
  sendConfiguredEmails,
  
  // Membership-specific methods
  sendMembershipApplicationConfirmation,
  sendMembershipApplicationAdminNotification,
  sendMembershipApplicationEmails,
  
  // Future webshop methods
  sendOrderConfirmationEmail
};