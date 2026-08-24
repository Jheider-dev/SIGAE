"""
Módulo de utilitarios globales del sistema SIGAE.

Contiene funciones auxiliares globales, especialmente el subsistema de auditoría
para registrar eventos de seguridad y accesos del sistema.
"""

import logging

logger = logging.getLogger('sigae.audit')


def log_evento_auditoria(tipo_evento, mensaje, request=None):
    """
    Escribe un registro de auditoría de seguridad formateado en var/log/sigae/audit.log.

    Args:
        tipo_evento (str): Identificador del tipo de evento (ej: LOGIN_EXITOSO, LOGIN_FALLIDO, ASISTENCIA_VAL).
        mensaje (str): Explicación detallada del evento.
        request: Objeto HttpRequest de Django para extraer IP y usuario activo (opcional).
    """
    ip_address = 'N/A'
    username = 'N/A'

    if request:
        # Extraer IP real en caso de proxy inverso (Nginx / Gunicorn)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR', 'N/A')

        if request.user and request.user.is_authenticated:
            username = request.user.username

    log_msg = f"[{tipo_evento}] [Usuario: {username}] [IP: {ip_address}] - {mensaje}"
    logger.info(log_msg)
