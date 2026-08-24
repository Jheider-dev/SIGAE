"""
Utilitarios para la aplicación 'autenticacion'.

Contiene funciones auxiliares para generación de usernames únicos y el mecanismo
de seguridad de credenciales dinámicas QR mediante HMAC-SHA256 y expiración temporal.
"""

import hmac
import hashlib
import time
from django.conf import settings
from django.contrib.auth import get_user_model


def generar_username_unico(nombres, apellidos):
    """
    Genera un nombre de usuario en mayúsculas a partir del primer nombre y
    las iniciales de los apellidos, resolviendo colisiones numéricamente.

    Ejemplo: "Jaime Perez Condori" -> "JAIMEPC"
    Si ya existe: "JAIMEPC" -> "JAIMEPC1", "JAIMEPC2", etc.
    """
    nombres_list = nombres.strip().split()
    if not nombres_list:
        raise ValueError("El nombre no puede estar vacío.")
    primer_nombre = nombres_list[0].upper()

    apellidos_list = apellidos.strip().split()
    iniciales_apellidos = "".join([part[0].upper() for part in apellidos_list if part])

    base_username = f"{primer_nombre}{iniciales_apellidos}"

    Usuario = get_user_model()
    username = base_username
    contador = 1

    while Usuario.objects.filter(username=username).exists():
        username = f"{base_username}{contador}"
        contador += 1

    return username


def generar_token_qr(usuario):
    """
    Genera un token QR dinámico firmado digitalmente.
    Formato: SIGAE|<rol>|<user_id>|<timestamp>|<firma_hmac>
    """
    timestamp = int(time.time())
    role = usuario.rol
    user_id = usuario.id

    message = f"{role}|{user_id}|{timestamp}"
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return f"SIGAE|{role}|{user_id}|{timestamp}|{signature}"


def verificar_token_qr(token, max_age_seconds=15):
    """
    Desglosa y valida un token QR dinámico.
    Verifica la integridad de la firma HMAC y que el tiempo transcurrido
    sea menor a max_age_seconds.
    
    Retorna (True, usuario) si es válido, o (False, mensaje_error) si es inválido.
    """
    if not token:
        return False, "Código QR vacío."

    parts = token.split('|')
    if len(parts) != 5 or parts[0] != 'SIGAE':
        return False, "El código escaneado no corresponde al formato dinámico de SIGAE."

    role, user_id_str, timestamp_str, signature = parts[1], parts[2], parts[3], parts[4]

    try:
        timestamp = int(timestamp_str)
        user_id = int(user_id_str)
    except ValueError:
        return False, "Estructura interna del código QR con datos inválidos."

    # Verificar tolerancia de tiempo (tolerar un pequeño desfase positivo/negativo)
    now = int(time.time())
    time_difference = abs(now - timestamp)
    if time_difference > max_age_seconds:
        return False, f"Código QR expirado (Excedido por {time_difference} segundos)."

    # Verificar firma HMAC
    message = f"{role}|{user_id}|{timestamp}"
    expected_signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        return False, "Firma de seguridad digital inválida (Posible manipulación)."

    Usuario = get_user_model()
    try:
        usuario = Usuario.objects.get(id=user_id, rol=role)
        return True, usuario
    except Usuario.DoesNotExist:
        return False, "El usuario asociado al código QR no se encuentra en el sistema."
