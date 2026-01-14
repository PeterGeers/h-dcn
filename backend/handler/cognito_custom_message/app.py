"""
H-DCN Cognito Custom Message Lambda Function

This function customizes email messages sent by AWS Cognito for different authentication scenarios.
It provides Dutch language templates with H-DCN branding for various message types.

Supported message types:
- CustomMessage_AdminCreateUser: Welcome message for admin-created users
- CustomMessage_ResendCode: Resend verification code
- CustomMessage_ForgotPassword: Password recovery (for fallback scenarios)
- CustomMessage_UpdateUserAttribute: Email change verification
- CustomMessage_VerifyUserAttribute: Attribute verification
- CustomMessage_Authentication: Authentication code delivery
"""

import json
import logging
import os
from datetime import datetime
from template_service import template_service

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get organization details from environment variables
ORGANIZATION_NAME = os.environ.get('ORGANIZATION_NAME', 'Harley-Davidson Club Nederland')
ORGANIZATION_WEBSITE = os.environ.get('ORGANIZATION_WEBSITE', 'https://h-dcn.nl')
ORGANIZATION_EMAIL = os.environ.get('ORGANIZATION_EMAIL', 'webhulpje@h-dcn.nl')
ORGANIZATION_SHORT_NAME = os.environ.get('ORGANIZATION_SHORT_NAME', 'H-DCN')

# Account recovery specific settings
RECOVERY_URL = os.environ.get('RECOVERY_URL', f"{ORGANIZATION_WEBSITE}/recovery")
HELP_URL = os.environ.get('HELP_URL', f"{ORGANIZATION_WEBSITE}/help/passwordless-recovery")
SUPPORT_PHONE = os.environ.get('SUPPORT_PHONE', 'tijdens kantooruren')

def lambda_handler(event, context):
    """
    AWS Cognito Custom Message Lambda trigger handler
    
    Args:
        event: Cognito trigger event containing user data and message type
        context: Lambda context object
        
    Returns:
        Modified event with custom email message and subject
    """
    try:
        logger.info(f"Cognito Custom Message trigger event: {json.dumps(event, default=str)}")
        
        # Extract event information
        trigger_source = event.get('triggerSource')
        user_attributes = event.get('request', {}).get('userAttributes', {})
        username = event.get('userName', '')
        user_pool_id = event.get('userPoolId', '')
        
        # Log the user pool ID for debugging (since it's no longer in environment variables)
        logger.info(f"Processing custom message for User Pool: {user_pool_id}")
        
        # Extract user information
        email = user_attributes.get('email', username)
        given_name = user_attributes.get('given_name', '')
        family_name = user_attributes.get('family_name', '')
        
        # Create display name
        if given_name or family_name:
            display_name = f"{given_name} {family_name}".strip()
        else:
            display_name = email.split('@')[0]  # Use email prefix as fallback
        
        logger.info(f"Processing custom message for trigger: {trigger_source}, user: {email}")
        
        # Generate custom message based on trigger source
        if trigger_source == 'CustomMessage_AdminCreateUser':
            event = handle_admin_create_user(event, display_name, email)
        elif trigger_source == 'CustomMessage_ResendCode':
            event = handle_resend_code(event, display_name, email)
        elif trigger_source == 'CustomMessage_ForgotPassword':
            event = handle_forgot_password(event, display_name, email)
        elif trigger_source == 'CustomMessage_UpdateUserAttribute':
            event = handle_update_user_attribute(event, display_name, email)
        elif trigger_source == 'CustomMessage_VerifyUserAttribute':
            event = handle_verify_user_attribute(event, display_name, email)
        elif trigger_source == 'CustomMessage_Authentication':
            event = handle_authentication(event, display_name, email)
        # Handle passwordless account recovery scenarios
        elif 'Recovery' in trigger_source or 'recovery' in trigger_source.lower():
            event = handle_passwordless_recovery(event, display_name, email)
        else:
            logger.warning(f"Unhandled trigger source: {trigger_source}")
            # Return default message for unhandled cases
            event = handle_default_message(event, display_name, email)
        
        logger.info("Custom message generated successfully")
        return event
        
    except Exception as e:
        logger.error(f"Error in custom message handler: {str(e)}")
        # Return original event on error to prevent authentication failure
        return event

def get_email_footer():
    """Generate consistent email footer with organization details"""
    return f"""---
{ORGANIZATION_NAME}
Website: {ORGANIZATION_WEBSITE}
E-mail: {ORGANIZATION_EMAIL}"""

def handle_admin_create_user(event, display_name, email):
    """Handle admin-created user welcome message"""
    temp_password = event.get('request', {}).get('tempPassword', '')
    
    # Use template service to render email
    context = {
        'DISPLAY_NAME': display_name,
        'EMAIL': email,
        'TEMP_PASSWORD': temp_password
    }
    
    subject, message = template_service.render_template('welcome-user', context)
    
    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event

def handle_resend_code(event, display_name, email):
    """Handle resend verification code message"""
    code_parameter = event.get('request', {}).get('codeParameter', '{####}')
    
    # Use template service to render email
    context = {
        'DISPLAY_NAME': display_name,
        'EMAIL': email,
        'CODE': code_parameter
    }
    
    subject, message = template_service.render_template('resend-code', context)
    
    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event

def handle_forgot_password(event, display_name, email):
    """Handle passwordless account recovery message"""
    code_parameter = event.get('request', {}).get('codeParameter', '{####}')
    
    subject = f"{ORGANIZATION_SHORT_NAME} Account Herstel - Toegang herstellen zonder wachtwoord"
    
    message = f"""Hallo {display_name},

U heeft een verzoek ingediend om toegang tot uw {ORGANIZATION_SHORT_NAME} account te herstellen.

**Passwordless Account Recovery**

Uw herstelcode is: {code_parameter}

Volg deze stappen om uw account te herstellen:

**Stap 1: Verifieer uw identiteit**
â€¢ Ga naar {RECOVERY_URL}
â€¢ Voer uw e-mailadres ({email}) in
â€¢ Voer de herstelcode hierboven in

**Stap 2: Stel nieuwe authenticatie in**
â€¢ Kies voor passkey authenticatie (aanbevolen)
â€¢ Of gebruik e-mail verificatie als fallback
â€¢ Geen wachtwoord nodig!

**Stap 3: Toegang hersteld**
â€¢ Log direct in met uw nieuwe authenticatiemethode
â€¢ Toegang tot al uw {ORGANIZATION_SHORT_NAME} functies

**Waarom passwordless?**
â€¢ Veiliger dan wachtwoorden
â€¢ Geen wachtwoorden om te vergeten
â€¢ Sneller inloggen met biometrie
â€¢ Bescherming tegen phishing

Deze herstelcode is 1 uur geldig.

**Veiligheidsmelding:**
Als u dit herstelverzoek niet heeft ingediend, neem dan onmiddellijk contact op via {ORGANIZATION_EMAIL}. Uw account blijft veilig - deze code alleen is niet voldoende voor toegang.

**Hulp nodig?**
â€¢ Bezoek onze hulppagina: {HELP_URL}
â€¢ E-mail ons: {ORGANIZATION_EMAIL}
â€¢ Bel {SUPPORT_PHONE} voor directe hulp

Met vriendelijke groet,
Het {ORGANIZATION_SHORT_NAME} Team

{get_email_footer()}"""

    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event

def handle_update_user_attribute(event, display_name, email):
    """Handle user attribute update verification"""
    code_parameter = event.get('request', {}).get('codeParameter', '{####}')
    
    subject = f"{ORGANIZATION_SHORT_NAME} Account Update - Bevestig wijziging"
    
    message = f"""Hallo {display_name},

U heeft een wijziging aangebracht aan uw {ORGANIZATION_SHORT_NAME} account gegevens.

Uw verificatiecode is: {code_parameter}

Voer deze code in om de wijziging te bevestigen.

Deze code is 24 uur geldig.

Als u deze wijziging niet heeft aangebracht, neem dan onmiddellijk contact op via {ORGANIZATION_EMAIL}

Met vriendelijke groet,
Het {ORGANIZATION_SHORT_NAME} Team

{get_email_footer()}"""

    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event

def handle_verify_user_attribute(event, display_name, email):
    """Handle user attribute verification"""
    code_parameter = event.get('request', {}).get('codeParameter', '{####}')
    
    subject = f"{ORGANIZATION_SHORT_NAME} Account Verificatie - Bevestig uw gegevens"
    
    message = f"""Hallo {display_name},

Welkom bij {ORGANIZATION_SHORT_NAME}! We hebben uw account aangemaakt en moeten uw e-mailadres verifiÃ«ren.

Uw verificatiecode is: {code_parameter}

Voer deze code in om uw e-mailadres te bevestigen en volledige toegang te krijgen tot:
â€¢ Uw persoonlijke lidmaatschapsgegevens
â€¢ De {ORGANIZATION_SHORT_NAME} webshop
â€¢ Evenementen en ritten
â€¢ Contact met andere leden

Deze code is 24 uur geldig.

Heeft u vragen? Neem contact op via {ORGANIZATION_EMAIL}

Met vriendelijke groet,
Het {ORGANIZATION_SHORT_NAME} Team

{get_email_footer()}"""

    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event

def handle_authentication(event, display_name, email):
    """Handle authentication code delivery"""
    code_parameter = event.get('request', {}).get('codeParameter', '{####}')
    
    subject = f"{ORGANIZATION_SHORT_NAME} Inlogcode - Bevestig uw identiteit"
    
    message = f"""Hallo {display_name},

Iemand probeert in te loggen op uw {ORGANIZATION_SHORT_NAME} account.

Uw inlogcode is: {code_parameter}

Voer deze code in om in te loggen op uw {ORGANIZATION_SHORT_NAME} account.

Deze code is 3 minuten geldig.

Als u niet probeert in te loggen, kunt u deze e-mail negeren.

Met vriendelijke groet,
Het {ORGANIZATION_SHORT_NAME} Team

{get_email_footer()}"""

    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event

def handle_passwordless_recovery(event, display_name, email):
    """Handle passwordless account recovery scenarios"""
    code_parameter = event.get('request', {}).get('codeParameter', '{####}')
    
    subject = f"{ORGANIZATION_SHORT_NAME} Passwordless Account Recovery - Veilig toegang herstellen"
    
    message = f"""Hallo {display_name},

**Passwordless Account Recovery voor {ORGANIZATION_SHORT_NAME}**

Uw veilige herstelcode is: {code_parameter}

**Waarom deze e-mail?**
U of iemand anders heeft account recovery aangevraagd voor {email}

**Herstel uw toegang in 3 eenvoudige stappen:**

**Stap 1: Verifieer uw identiteit**
â€¢ Ga naar {RECOVERY_URL}
â€¢ Voer de herstelcode hierboven in
â€¢ Bevestig uw e-mailadres

**Stap 2: Kies uw nieuwe authenticatiemethode**
â€¢ **Passkey (aanbevolen)**: Gebruik Face ID, vingerafdruk of Windows Hello
â€¢ **E-mail verificatie**: Ontvang inlogcodes per e-mail
â€¢ **Geen wachtwoord nodig!**

**Stap 3: Direct toegang**
â€¢ Log meteen in met uw nieuwe methode
â€¢ Toegang tot uw lidmaatschapsgegevens
â€¢ Gebruik van de {ORGANIZATION_SHORT_NAME} webshop
â€¢ Deelname aan evenementen

**Voordelen van passwordless authenticatie:**
- Veiliger dan wachtwoorden
- Geen wachtwoorden om te onthouden
- Sneller inloggen
- Bescherming tegen phishing
- Werkt op alle apparaten

**Veiligheid:**
Deze herstelcode is 1 uur geldig en kan maar een keer gebruikt worden.

**Dit was u niet?**
Als u geen account recovery heeft aangevraagd:
â€¢ Negeer deze e-mail - uw account blijft veilig
â€¢ Neem contact op via {ORGANIZATION_EMAIL} bij zorgen
â€¢ Overweeg om uw e-mail account te controleren

**Hulp nodig?**
E-mail: {ORGANIZATION_EMAIL}
Hulp: {HELP_URL}
Telefonische ondersteuning {SUPPORT_PHONE}

Met vriendelijke groet,
Het {ORGANIZATION_SHORT_NAME} Security Team

{get_email_footer()}"""

    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event

def handle_default_message(event, display_name, email):
    """Handle default message for unrecognized trigger sources"""
    code_parameter = event.get('request', {}).get('codeParameter', '{####}')
    
    subject = f"{ORGANIZATION_SHORT_NAME} Account Verificatie"
    
    message = f"""Hallo {display_name},

Uw {ORGANIZATION_SHORT_NAME} verificatiecode is: {code_parameter}

Voer deze code in om door te gaan.

Met vriendelijke groet,
Het {ORGANIZATION_SHORT_NAME} Team

{get_email_footer()}"""

    event['response']['emailMessage'] = message
    event['response']['emailSubject'] = subject
    
    return event