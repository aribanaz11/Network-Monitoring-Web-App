import logging
from .models import AuditLog

logger = logging.getLogger('netwatch.audit')

def log_audit_event(user, action, resource_type, resource_id='', ip_address='127.0.0.1', details=None):
    """
    Helper function to record an immutable audit log entry.
    Handles anonymous/system events safely.
    """
    try:
        user_instance = user if (user and hasattr(user, 'is_authenticated') and user.is_authenticated) else None
        log_entry = AuditLog.objects.create(
            user=user_instance,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            ip_address=ip_address or '127.0.0.1',
            details=details or {}
        )
        logger.info(f"AUDIT: {action} on {resource_type} (ID: {resource_id}) by {user_instance}")
        return log_entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {str(e)}", exc_info=True)
        return None
