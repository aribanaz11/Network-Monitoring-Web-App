import logging
from .models import AuditLog

logger = logging.getLogger('netwatch.audit')

SENSITIVE_AUDIT_KEYS = {
    'password', 'passwd', 'secret', 'token', 'access_token', 'refresh_token',
    'ssh_password', 'snmp_community', 'fernet_key', 'authorization', 'api_key', 'private_key'
}

def redact_sensitive_data(data):
    """
    Recursively redacts sensitive keys from audit log dictionaries and payloads.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_AUDIT_KEYS):
                sanitized[k] = '[REDACTED]'
            elif isinstance(v, (dict, list)):
                sanitized[k] = redact_sensitive_data(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data

def log_audit_event(user, action, resource_type, resource_id='', ip_address='127.0.0.1', details=None):
    """
    Helper function to record an immutable audit log entry.
    Handles anonymous/system events safely and automatically sanitizes sensitive payloads.
    """
    try:
        user_instance = user if (user and hasattr(user, 'is_authenticated') and user.is_authenticated) else None
        sanitized_details = redact_sensitive_data(details or {})
        
        log_entry = AuditLog.objects.create(
            user=user_instance,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            ip_address=ip_address or '127.0.0.1',
            details=sanitized_details
        )
        logger.info(f"AUDIT: {action} on {resource_type} (ID: {resource_id}) by {user_instance}")
        return log_entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {str(e)}", exc_info=True)
        return None
