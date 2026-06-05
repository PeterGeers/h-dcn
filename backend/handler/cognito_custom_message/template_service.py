"""
Email Template Service for S3-based template management with locale support
"""
import json
import boto3
import os
from typing import Dict, Any

# Default locale for fallback
DEFAULT_LOCALE = 'nl'


class EmailTemplateService:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ.get('EMAIL_TEMPLATES_BUCKET', 'hdcn-email-templates')
        self._variables_cache = None
        self._template_cache = {}
    
    def get_variables(self) -> Dict[str, str]:
        """Load variables from S3 config"""
        if self._variables_cache is None:
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key='config/variables.json'
                )
                self._variables_cache = json.loads(response['Body'].read().decode('utf-8'))
            except Exception as e:
                print(f"Error loading variables from S3: {e}")
                # Fallback to environment variables
                self._variables_cache = {
                    'ORGANIZATION_NAME': os.environ.get('ORGANIZATION_NAME', 'Harley-Davidson Club Nederland'),
                    'ORGANIZATION_WEBSITE': os.environ.get('ORGANIZATION_WEBSITE', 'https://portal.h-dcn.nl'),
                    'ORGANIZATION_EMAIL': os.environ.get('ORGANIZATION_EMAIL', 'webhulpje@h-dcn.nl'),
                    'ORGANIZATION_SHORT_NAME': os.environ.get('ORGANIZATION_SHORT_NAME', 'H-DCN'),
                    'RECOVERY_URL': os.environ.get('RECOVERY_URL', 'https://portal.h-dcn.nl/recovery'),
                    'HELP_URL': os.environ.get('HELP_URL', 'https://portal.h-dcn.nl/help/passwordless-recovery'),
                    'SUPPORT_PHONE': os.environ.get('SUPPORT_PHONE', 'tijdens kantooruren')
                }
        return self._variables_cache
    
    def get_template(self, template_name: str, locale: str = DEFAULT_LOCALE) -> str:
        """
        Load template from S3 with locale support.
        
        Tries locale-specific path first: templates/{locale}/{template_name}.html
        Falls back to Dutch: templates/nl/{template_name}.html
        Falls back to legacy path: templates/{template_name}.html
        """
        cache_key = f"{locale}/{template_name}"
        
        if cache_key not in self._template_cache:
            template_html = None
            
            # Try locale-specific template
            if locale and locale != DEFAULT_LOCALE:
                template_html = self._load_s3_template(f'templates/{locale}/{template_name}.html')
            
            # Fallback to Dutch locale directory
            if not template_html:
                template_html = self._load_s3_template(f'templates/{DEFAULT_LOCALE}/{template_name}.html')
            
            # Fallback to legacy flat path (backward compatibility)
            if not template_html:
                template_html = self._load_s3_template(f'templates/{template_name}.html')
            
            # Final fallback to hardcoded template
            if not template_html:
                template_html = self._get_fallback_template(template_name)
            
            self._template_cache[cache_key] = template_html
        
        return self._template_cache[cache_key]
    
    def _load_s3_template(self, key: str) -> str | None:
        """Attempt to load a template from S3. Returns None if not found."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read().decode('utf-8')
        except self.s3_client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            print(f"Error loading template {key} from S3: {e}")
            return None
    
    def render_template(self, template_name: str, context: Dict[str, Any], locale: str = DEFAULT_LOCALE) -> tuple[str, str]:
        """Render template with variables and context, using locale-specific template"""
        template_html = self.get_template(template_name, locale=locale)
        variables = self.get_variables()
        
        # Combine variables and context
        all_vars = {**variables, **context}
        
        # Replace all variables in template
        rendered_html = template_html
        for key, value in all_vars.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_html = rendered_html.replace(placeholder, str(value))
        
        # Extract subject from template (look for title tag)
        subject = self._extract_subject(rendered_html, template_name, all_vars)
        
        # Convert HTML to plain text for email body
        plain_text = self._html_to_plain_text(rendered_html)
        
        return subject, plain_text
    
    def _extract_subject(self, html: str, template_name: str, variables: Dict[str, Any]) -> str:
        """Extract subject from HTML title tag or generate default"""
        import re
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
        
        # Fallback subjects based on template name
        fallback_subjects = {
            'welcome-user': f"{variables.get('ORGANIZATION_SHORT_NAME', 'H-DCN')} Account Aangemaakt - Welkom bij de club!",
            'resend-code': f"{variables.get('ORGANIZATION_SHORT_NAME', 'H-DCN')} Verificatiecode",
            'passwordless-recovery': f"{variables.get('ORGANIZATION_SHORT_NAME', 'H-DCN')} Account Herstel - Toegang herstellen zonder wachtwoord",
            'verify-email': f"{variables.get('ORGANIZATION_SHORT_NAME', 'H-DCN')} E-mail Verificatie",
            'forgot-password': f"{variables.get('ORGANIZATION_SHORT_NAME', 'H-DCN')} Wachtwoord Herstel"
        }
        
        return fallback_subjects.get(template_name, f"{variables.get('ORGANIZATION_SHORT_NAME', 'H-DCN')} Bericht")
    
    def _html_to_plain_text(self, html: str) -> str:
        """Convert HTML to plain text for email body"""
        import re
        
        # Remove HTML tags but preserve structure
        text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<h[1-6][^>]*>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</h[1-6]>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<hr[^>]*>', '\n---\n', text, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Max 2 consecutive newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single space
        text = text.strip()
        
        return text
    
    def _get_fallback_template(self, template_name: str) -> str:
        """Fallback templates if S3 is unavailable"""
        fallback_templates = {
            'welcome-user': '''
            <html><body>
            <h2>Welkom bij {{ORGANIZATION_SHORT_NAME}}, {{DISPLAY_NAME}}!</h2>
            <p>Er is een account voor u aangemaakt.</p>
            <p><strong>E-mailadres:</strong> {{EMAIL}}</p>
            <p><strong>Tijdelijk wachtwoord:</strong> {{TEMP_PASSWORD}}</p>
            <p>Ga naar {{ORGANIZATION_WEBSITE}}/login om in te loggen.</p>
            <p>Met vriendelijke groet,<br>Het {{ORGANIZATION_SHORT_NAME}} Team</p>
            </body></html>
            ''',
            'resend-code': '''
            <html><body>
            <h2>Verificatiecode voor {{ORGANIZATION_SHORT_NAME}}</h2>
            <p>Hallo {{DISPLAY_NAME}},</p>
            <p>Uw verificatiecode: <strong>{{CODE}}</strong></p>
            <p>Met vriendelijke groet,<br>Het {{ORGANIZATION_SHORT_NAME}} Team</p>
            </body></html>
            ''',
            'passwordless-recovery': '''
            <html><body>
            <h2>Account Herstel voor {{ORGANIZATION_SHORT_NAME}}</h2>
            <p>Hallo {{DISPLAY_NAME}},</p>
            <p>Uw herstelcode: <strong>{{CODE}}</strong></p>
            <p>Ga naar {{RECOVERY_URL}} om uw account te herstellen.</p>
            <p>Met vriendelijke groet,<br>Het {{ORGANIZATION_SHORT_NAME}} Team</p>
            </body></html>
            '''
        }
        
        return fallback_templates.get(template_name, '''
        <html><body>
        <h2>{{ORGANIZATION_SHORT_NAME}} Bericht</h2>
        <p>Hallo {{DISPLAY_NAME}},</p>
        <p>{{CODE}}</p>
        <p>Met vriendelijke groet,<br>Het {{ORGANIZATION_SHORT_NAME}} Team</p>
        </body></html>
        ''')

# Global instance
template_service = EmailTemplateService()