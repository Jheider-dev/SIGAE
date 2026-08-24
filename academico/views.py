"""
Vistas para la aplicación 'academico'.

Define controladores para la gestión y listado de ciclos de preparación académica
y el control y simulación de escaneo de asistencia mediante códigos QR.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from .models import AsistenciaQR, Ciclo

Usuario = get_user_model()


@login_required(login_url='iniciar_sesion')
def listar_ciclos(request):
    """
    Vista que lista todos los ciclos de preparación académica registrados.
    Restringe el acceso para asegurar que solo Secretaría o Administradores puedan
    gestionarlos. Los Docentes ya no tienen acceso.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        fecha_inicio = request.POST.get('fecha_inicio', '').strip()
        fecha_fin = request.POST.get('fecha_fin', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not nombre or not fecha_inicio or not fecha_fin:
            messages.error(request, "Todos los campos con asterisco son obligatorios.")
            return redirect('listar_ciclos')

        try:
            Ciclo.objects.create(
                nombre=nombre,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                descripcion=descripcion,
                activo=True
            )
            messages.success(request, f"¡Ciclo '{nombre}' registrado con éxito!")
        except Exception as e:
            messages.error(request, f"Error al registrar ciclo: {str(e)}")
        return redirect('listar_ciclos')

    ciclos = Ciclo.objects.all().order_by('-fecha_inicio')
    contexto = {
        'ciclos': ciclos
    }
    return render(request, 'academico/listar_ciclos.html', contexto)


@login_required(login_url='iniciar_sesion')
def gestionar_alumnos_ciclo(request, ciclo_id):
    """
    Vista para que la secretaria agregue o remueva alumnos de un ciclo específico.
    Los alumnos se listan independientemente de su área académica.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    ciclo = get_object_or_404(Ciclo, id=ciclo_id)
    from .models import Matricula

    if request.method == 'POST':
        alumno_id = request.POST.get('alumno_id')
        accion = request.POST.get('accion')

        if alumno_id and accion:
            alumno = get_object_or_404(Usuario, id=alumno_id, rol='ALUMNO')
            if accion == 'agregar':
                if not Matricula.objects.filter(alumno=alumno, ciclo=ciclo).exists():
                    Matricula.objects.create(
                        alumno=alumno,
                        ciclo=ciclo,
                        codigo_matricula=f"EULER-{ciclo.id}-{alumno.id}",
                        activo=True
                    )
                    messages.success(request, f"Alumno {alumno.get_full_name()} agregado al ciclo con éxito.")
            elif accion == 'eliminar':
                Matricula.objects.filter(alumno=alumno, ciclo=ciclo).delete()
                messages.warning(request, f"Alumno {alumno.get_full_name()} removido del ciclo.")
        return redirect('gestionar_alumnos_ciclo', ciclo_id=ciclo.id)

    # Alumnos actualmente inscritos
    matriculas = Matricula.objects.filter(ciclo=ciclo, activo=True).select_related('alumno')
    
    # Alumnos registrados en el sistema no matriculados en este ciclo (independientemente del área)
    alumnos_disponibles = Usuario.objects.filter(rol='ALUMNO').exclude(matriculas__ciclo=ciclo).order_by('last_name')

    contexto = {
        'ciclo': ciclo,
        'matriculas': matriculas,
        'alumnos_disponibles': alumnos_disponibles
    }
    return render(request, 'academico/gestionar_alumnos_ciclo.html', contexto)


import datetime
import json
from django.http import JsonResponse


@login_required(login_url='iniciar_sesion')
def control_asistencia(request):
    """
    Controlador para el panel de asistencia QR.

    Soporta peticiones síncronas (para renderizado de plantillas) y
    peticiones asíncronas AJAX/fetch (para registrar el escaneo QR en tiempo real).
    """
    if request.user.rol not in ['ADMIN', 'SECRETARIA', 'ALUMNO'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso no autorizado.")
        return redirect('raiz')

    # Procesamiento del escaneo de QR (peticiones asíncronas Fetch POST de Secretaría o Administrador)
    if request.method == 'POST' and (request.user.rol in ['SECRETARIA', 'ADMIN'] or request.user.is_superuser or request.user.is_staff):
        token_qr = ''
        
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                token_qr = data.get('token_qr', '').strip()
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Cuerpo JSON mal estructurado.'}, status=400)
        else:
            token_qr = request.POST.get('token_qr', '').strip()

        # Validar token QR dinámico usando HMAC y tolerancia de 15 segundos
        from autenticacion.utils import verificar_token_qr
        from sigae.utils import log_evento_auditoria
        es_valido, res_val = verificar_token_qr(token_qr, max_age_seconds=15)
        
        if not es_valido:
            log_evento_auditoria('ASISTENCIA_RECHAZADA', f"Intento de registro fallido. Motivo: {res_val}.", request)
            return JsonResponse({'error': res_val}, status=400)

        usuario = res_val
        hoy = datetime.date.today()
        from .models import Pago

        pagos_pendientes_set = set(Pago.objects.filter(estado='PENDIENTE').values_list('alumno_id', flat=True))
        pagos_realizados_set = set(Pago.objects.filter(estado='PAGADO').values_list('alumno_id', flat=True))

        if usuario.rol == 'ALUMNO':
            # Evitar registro de asistencia múltiple el mismo día
            if AsistenciaQR.objects.filter(alumno=usuario, fecha=hoy).exists():
                log_evento_auditoria('ASISTENCIA_RECHAZADA', f"El alumno {usuario.username} ya marcó hoy.", request)
                return JsonResponse({
                    'error': f'El alumno {usuario.get_full_name()} ya registró su ingreso el día de hoy.'
                }, status=400)

            # Registrar asistencia como PRESENTE
            asistencia = AsistenciaQR.objects.create(
                alumno=usuario,
                codigo_qr_escaneado=token_qr,
                estado=AsistenciaQR.ESTADO_PRESENTE
            )

            log_evento_auditoria('ASISTENCIA_ALUMNO', f"Asistencia registrada con éxito para alumno {usuario.username}.", request)

            rol_area_text = f"Alumno - {usuario.get_area_academica_display() or 'General'}"

            if usuario.id in pagos_pendientes_set:
                estado_pago = 'Pensión Pendiente'
                estado_pago_badge = 'badge-danger'
                alerta_deuda = True
            elif usuario.id in pagos_realizados_set:
                estado_pago = 'Al día'
                estado_pago_badge = 'badge-success'
                alerta_deuda = False
            else:
                estado_pago = 'Pensión Pendiente'
                estado_pago_badge = 'badge-warning'
                alerta_deuda = True

            return JsonResponse({
                'success': True,
                'rol': 'ALUMNO',
                'mensaje': f'¡Ingreso registrado para {usuario.get_full_name()}! [Finanzas: {estado_pago}]',
                'asistencia': {
                    'nombre': usuario.get_full_name(),
                    'rol_display': 'Alumno',
                    'rol_area': rol_area_text,
                    'fecha': asistencia.fecha.strftime('%d/%m/%Y'),
                    'hora': asistencia.hora_acceso.strftime('%H:%M:%S'),
                    'token': token_qr[:25] + '...',
                    'estado': 'Presente',
                    'estado_pago': estado_pago,
                    'estado_pago_badge': estado_pago_badge,
                    'alerta_deuda': alerta_deuda
                }
            })

        elif usuario.rol == 'DOCENTE':
            # Comprobar si ya marcó hoy
            from .models import AsistenciaDocente
            if AsistenciaDocente.objects.filter(docente=usuario, fecha=hoy).exists():
                log_evento_auditoria('ASISTENCIA_RECHAZADA', f"El docente {usuario.username} ya marcó hoy.", request)
                return JsonResponse({
                    'error': f'El docente {usuario.get_full_name()} ya registró su asistencia el día de hoy.'
                }, status=400)

            log_evento_auditoria('ASISTENCIA_DOCENTE_SCAN', f"Escaneo QR exitoso para docente {usuario.username}. Esperando confirmación de horas.", request)

            # Para docentes, devolvemos confirmación de horas sugerida (1.5)
            return JsonResponse({
                'success': True,
                'rol': 'DOCENTE',
                'needs_hours_confirmation': True,
                'docente_id': usuario.id,
                'docente_nombre': usuario.get_full_name() or usuario.username,
                'token_qr': token_qr,
                'sugerencia_horas': '1.5'
            })

    from .models import Pago
    pagos_pendientes_set = set(Pago.objects.filter(estado='PENDIENTE').values_list('alumno_id', flat=True))
    pagos_realizados_set = set(Pago.objects.filter(estado='PAGADO').values_list('alumno_id', flat=True))

    # Filtrar historial de asistencias para el renderizado inicial de la página
    if request.user.rol == 'ALUMNO':
        asistencias = AsistenciaQR.objects.filter(alumno=request.user).order_by('-fecha', '-hora_acceso')
        asistencias_list = []
        for asis in asistencias:
            asistencias_list.append({
                'nombre': asis.alumno.get_full_name() or asis.alumno.username,
                'rol': 'ALUMNO',
                'rol_area': f"Alumno - {asis.alumno.get_area_academica_display() or 'General'}",
                'fecha': asis.fecha,
                'hora': asis.hora_acceso,
                'token': asis.codigo_qr_escaneado,
                'estado_badge': 'badge-success',
                'estado_text': 'Presente' if asis.estado == 'PRESENTE' else ('Tarde' if asis.estado == 'TARDE' else 'Falta')
            })
        alumnos = None
    else:
        # Secretaría (historial consolidado de últimos 25 registros)
        asistencias_al = AsistenciaQR.objects.all().select_related('alumno').order_by('-fecha', '-hora_acceso')[:20]
        from .models import AsistenciaDocente
        asistencias_doc = AsistenciaDocente.objects.all().select_related('docente').order_by('-fecha', '-hora_acceso')[:20]

        asistencias_list = []
        for asis in asistencias_al:
            if asis.alumno.id in pagos_pendientes_set:
                pago_st = 'Pensión Pendiente'
                pago_bg = 'badge-danger'
            elif asis.alumno.id in pagos_realizados_set:
                pago_st = 'Al día'
                pago_bg = 'badge-success'
            else:
                pago_st = 'Pensión Pendiente'
                pago_bg = 'badge-warning'

            asistencias_list.append({
                'nombre': asis.alumno.get_full_name() or asis.alumno.username,
                'rol': 'ALUMNO',
                'rol_area': f"Alumno - {asis.alumno.get_area_academica_display() or 'General'}",
                'fecha': asis.fecha,
                'hora': asis.hora_acceso,
                'token': asis.codigo_qr_escaneado,
                'estado_badge': 'badge-success',
                'estado_text': 'Presente' if asis.estado == 'PRESENTE' else ('Tarde' if asis.estado == 'TARDE' else 'Falta'),
                'estado_pago': pago_st,
                'estado_pago_badge': pago_bg
            })
        for asis in asistencias_doc:
            asistencias_list.append({
                'nombre': asis.docente.get_full_name() or asis.docente.username,
                'rol': 'DOCENTE',
                'rol_area': f"Docente - {asis.docente.curso_asignado or 'General'}",
                'fecha': asis.fecha,
                'hora': asis.hora_acceso,
                'token': asis.codigo_qr_escaneado,
                'estado_badge': 'badge-warning',
                'estado_text': f'Dictado ({asis.horas_dictadas} hrs)',
                'estado_pago': 'Docente',
                'estado_pago_badge': 'badge-primary'
            })

        # Ordenar por fecha y hora de ingreso descendente
        asistencias_list.sort(key=lambda x: (x['fecha'], x['hora']), reverse=True)
        asistencias_list = asistencias_list[:25]
        alumnos = Usuario.objects.filter(rol='ALUMNO').order_by('first_name', 'last_name')

    contexto = {
        'asistencias_list': asistencias_list,
        'alumnos': alumnos
    }
    return render(request, 'academico/control_asistencia.html', contexto)


@login_required(login_url='iniciar_sesion')
def registrar_asistencia_docente(request):
    """
    Registra la asistencia de un docente confirmada por la secretaria
    después de validar las horas de dictado.
    """
    if request.user.rol != 'SECRETARIA':
        return JsonResponse({'error': 'Acceso no autorizado.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Cuerpo JSON mal formado.'}, status=400)

    docente_id = data.get('docente_id')
    horas_str = data.get('horas', '1.5')
    token_qr = data.get('token_qr', '')

    if not docente_id or not token_qr:
        return JsonResponse({'error': 'Faltan parámetros obligatorios.'}, status=400)

    try:
        horas = float(horas_str)
    except ValueError:
        return JsonResponse({'error': 'Horas dictadas inválidas.'}, status=400)

    # Validar token QR (tolerancia 60s para la secretaria interactuando con el popup)
    from autenticacion.utils import verificar_token_qr
    from sigae.utils import log_evento_auditoria
    es_valido, res_val = verificar_token_qr(token_qr, max_age_seconds=60)
    if not es_valido:
        log_evento_auditoria('ASISTENCIA_RECHAZADA', f"Intento fallido de confirmación docente. QR inválido o expirado: {res_val}.", request)
        return JsonResponse({'error': f'Código QR inválido o expirado: {res_val}'}, status=400)

    docente = res_val
    if docente.id != int(docente_id) or docente.rol != 'DOCENTE':
        log_evento_auditoria('ASISTENCIA_RECHAZADA', f"Intento de confirmación fallido. Datos no coinciden con el QR. Docente solicitado ID: {docente_id}, QR ID: {docente.id}.", request)
        return JsonResponse({'error': 'Los datos del docente no coinciden con el QR.'}, status=400)

    # Evitar duplicados hoy
    hoy = datetime.date.today()
    from .models import AsistenciaDocente
    if AsistenciaDocente.objects.filter(docente=docente, fecha=hoy).exists():
        log_evento_auditoria('ASISTENCIA_RECHAZADA', f"Intento fallido de confirmación docente. Docente {docente.username} ya marcó hoy.", request)
        return JsonResponse({'error': f'El docente {docente.get_full_name()} ya registró asistencia hoy.'}, status=400)

    try:
        asistencia = AsistenciaDocente.objects.create(
            docente=docente,
            horas_dictadas=horas,
            codigo_qr_escaneado=token_qr
        )

        log_evento_auditoria('ASISTENCIA_DOCENTE_VALIDADA', f"Asistencia confirmada para docente {docente.username} con {horas} horas.", request)

        rol_area_text = f"Docente - {docente.curso_asignado or 'General'}"

        return JsonResponse({
            'success': True,
            'mensaje': f'¡Asistencia registrada para {docente.get_full_name()} con {horas} hrs!',
            'asistencia': {
                'nombre': docente.get_full_name(),
                'rol_display': 'Docente',
                'rol_area': rol_area_text,
                'fecha': asistencia.fecha.strftime('%d/%m/%Y'),
                'hora': asistencia.hora_acceso.strftime('%H:%M:%S'),
                'token': token_qr[:25] + '...',
                'estado': f'Dictado ({horas} hrs)'
            }
        })
    except Exception as e:
        return JsonResponse({'error': f'Error al registrar la asistencia: {str(e)}'}, status=500)


@login_required(login_url='iniciar_sesion')
def editar_ciclo(request, ciclo_id):
    """
    Vista para editar la información de un ciclo académico (nombre, fechas, descripción, estado).
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    ciclo = get_object_or_404(Ciclo, id=ciclo_id)

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        fecha_inicio = request.POST.get('fecha_inicio', '').strip()
        fecha_fin = request.POST.get('fecha_fin', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        activo = request.POST.get('activo') == '1'

        if not nombre or not fecha_inicio or not fecha_fin:
            messages.error(request, "El nombre y las fechas de inicio y fin son obligatorios.")
            return render(request, 'academico/editar_ciclo.html', {'ciclo': ciclo})

        try:
            ciclo.nombre = nombre
            ciclo.fecha_inicio = fecha_inicio
            ciclo.fecha_fin = fecha_fin
            ciclo.descripcion = descripcion
            ciclo.activo = activo
            ciclo.save()
            messages.success(request, f"¡Ciclo '{ciclo.nombre}' actualizado correctamente!")
            return redirect('listar_ciclos')
        except Exception as e:
            messages.error(request, f"Error al actualizar el ciclo: {str(e)}")

    return render(request, 'academico/editar_ciclo.html', {'ciclo': ciclo})


@login_required(login_url='iniciar_sesion')
def cambiar_estado_ciclo(request, ciclo_id):
    """
    Alterna el estado Activo / Finalizado de un ciclo académico.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    if request.method == 'POST':
        from sigae.utils import log_evento_auditoria
        ciclo = get_object_or_404(Ciclo, id=ciclo_id)
        ciclo.activo = not ciclo.activo
        ciclo.save()
        nuevo_estado = "Activo" if ciclo.activo else "Finalizado"
        messages.success(request, f"El ciclo '{ciclo.nombre}' ahora se encuentra: {nuevo_estado}.")
        log_evento_auditoria('CAMBIO_ESTADO_CICLO', f"Ciclo {ciclo.nombre} cambiado a {nuevo_estado}.", request)

    return redirect('listar_ciclos')


@login_required(login_url='iniciar_sesion')
def ver_liquidacion_docentes(request):
    """
    Panel financiero de liquidación mensual para el Administrador (Director).
    Suma las horas de asistencia de los docentes en un mes/año y las multiplica
    por su precio por hora.
    """
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Administradores del sistema.")
        return redirect('raiz')

    import datetime
    hoy = datetime.date.today()
    mes_seleccionado = int(request.GET.get('mes', hoy.month))
    anio_seleccionado = int(request.GET.get('anio', hoy.year))

    from .models import AsistenciaDocente
    asistencias = AsistenciaDocente.objects.filter(
        fecha__month=mes_seleccionado,
        fecha__year=anio_seleccionado
    ).select_related('docente')

    from collections import defaultdict
    docentes_datos = defaultdict(lambda: {
        'nombre': '',
        'curso': '',
        'precio_hora': 0.0,
        'horas_totales': 0.0,
        'total_pagar': 0.0,
        'asistencias_count': 0
    })

    for asis in asistencias:
        docente = asis.docente
        d_id = docente.id
        if not docentes_datos[d_id]['nombre']:
            docentes_datos[d_id]['nombre'] = docente.get_full_name() or docente.username
            docentes_datos[d_id]['curso'] = docente.curso_asignado or 'No asignado'
            docentes_datos[d_id]['precio_hora'] = float(docente.precio_hora or 0.0)
            
        docentes_datos[d_id]['horas_totales'] += float(asis.horas_dictadas)
        docentes_datos[d_id]['asistencias_count'] += 1

    liquidacion_list = []
    gran_total_horas = 0.0
    gran_total_monto = 0.0

    for d_id, data in docentes_datos.items():
        data['total_pagar'] = round(data['horas_totales'] * data['precio_hora'], 2)
        gran_total_horas += data['horas_totales']
        gran_total_monto += data['total_pagar']
        liquidacion_list.append(data)

    liquidacion_list.sort(key=lambda x: x['nombre'])

    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    anios = list(range(hoy.year - 2, hoy.year + 2))

    contexto = {
        'liquidacion_list': liquidacion_list,
        'mes_seleccionado': mes_seleccionado,
        'anio_seleccionado': anio_seleccionado,
        'gran_total_horas': gran_total_horas,
        'gran_total_monto': gran_total_monto,
        'meses': meses,
        'anios': anios
    }
    return render(request, 'academico/liquidacion_docentes.html', contexto)


@login_required(login_url='iniciar_sesion')
def exportar_liquidacion_docentes_csv(request):
    """
    Exporta el reporte de liquidación docente a archivo CSV compatible con Excel.
    """
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Administradores.")
        return redirect('raiz')

    import csv
    import datetime
    from django.http import HttpResponse
    from collections import defaultdict
    from .models import AsistenciaDocente

    hoy = datetime.date.today()
    mes_seleccionado = int(request.GET.get('mes', hoy.month))
    anio_seleccionado = int(request.GET.get('anio', hoy.year))

    asistencias = AsistenciaDocente.objects.filter(
        fecha__month=mes_seleccionado,
        fecha__year=anio_seleccionado
    ).select_related('docente')

    docentes_datos = defaultdict(lambda: {
        'dni': '',
        'nombre': '',
        'curso': '',
        'precio_hora': 0.0,
        'horas_totales': 0.0,
        'total_pagar': 0.0,
    })

    for asis in asistencias:
        docente = asis.docente
        d_id = docente.id
        if not docentes_datos[d_id]['nombre']:
            docentes_datos[d_id]['dni'] = docente.dni or ''
            docentes_datos[d_id]['nombre'] = docente.get_full_name() or docente.username
            docentes_datos[d_id]['curso'] = docente.curso_asignado or 'No asignado'
            docentes_datos[d_id]['precio_hora'] = float(docente.precio_hora or 0.0)
            
        docentes_datos[d_id]['horas_totales'] += float(asis.horas_dictadas)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="liquidacion_docentes_{mes_seleccionado}_{anio_seleccionado}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Periodo Mes', 'Periodo Anio', 'DNI', 'Docente', 'Curso Asignado', 'Precio por Hora (S/.)', 'Horas Dictadas', 'Total a Pagar (S/.)'])

    for d_id, data in sorted(docentes_datos.items(), key=lambda x: x[1]['nombre']):
        total_pagar = round(data['horas_totales'] * data['precio_hora'], 2)
        writer.writerow([
            mes_seleccionado,
            anio_seleccionado,
            data['dni'],
            data['nombre'],
            data['curso'],
            f"{data['precio_hora']:.2f}",
            f"{data['horas_totales']:.2f}",
            f"{total_pagar:.2f}"
        ])

    return response


@login_required(login_url='iniciar_sesion')
def exportar_asistencias_csv(request):
    """
    Exporta el historial consolidado de asistencias (alumnos y docentes) a archivo CSV.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal autorizado.")
        return redirect('raiz')

    import csv
    import datetime
    from django.http import HttpResponse
    from .models import AsistenciaDocente, AsistenciaQR

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    fecha_str = datetime.date.today().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="reporte_asistencias_sigae_{fecha_str}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Tipo Persona', 'Fecha', 'Hora Ingreso', 'DNI', 'Usuario', 'Nombre Completo', 'Rol / Area / Curso', 'Estado Asistencia / Horas'])

    # Asistencias Alumnos
    asistencias_al = AsistenciaQR.objects.all().select_related('alumno').order_by('-fecha', '-hora_acceso')
    for asis in asistencias_al:
        writer.writerow([
            'Alumno',
            asis.fecha.strftime('%d/%m/%Y'),
            asis.hora_acceso.strftime('%H:%M:%S'),
            asis.alumno.dni or '',
            asis.alumno.username,
            asis.alumno.get_full_name() or asis.alumno.username,
            f"Alumno - {asis.alumno.get_area_academica_display() or 'General'}",
            asis.get_estado_display()
        ])

    # Asistencias Docentes
    asistencias_doc = AsistenciaDocente.objects.all().select_related('docente').order_by('-fecha', '-hora_acceso')
    for asis in asistencias_doc:
        writer.writerow([
            'Docente',
            asis.fecha.strftime('%d/%m/%Y'),
            asis.hora_acceso.strftime('%H:%M:%S'),
            asis.docente.dni or '',
            asis.docente.username,
            asis.docente.get_full_name() or asis.docente.username,
            f"Docente - {asis.docente.curso_asignado or 'General'}",
            f"Dictado ({asis.horas_dictadas} hrs)"
        ])

    return response


@login_required(login_url='iniciar_sesion')
def control_pagos(request):
    """
    Panel de control de pagos, cuotas y pensiones de alumnos.
    Accesible para Administradores y Secretaría.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    import datetime
    from django.db.models import Sum, Q
    from .models import Pago, Matricula

    hoy = datetime.date.today()
    q_busqueda = request.GET.get('q', '').strip()
    concepto_filtro = request.GET.get('concepto', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    pagos_qs = Pago.objects.all().select_related('alumno', 'ciclo', 'registrado_por').order_by('-fecha_pago', '-id')

    if q_busqueda:
        pagos_qs = pagos_qs.filter(
            Q(alumno__dni__icontains=q_busqueda) |
            Q(alumno__first_name__icontains=q_busqueda) |
            Q(alumno__last_name__icontains=q_busqueda) |
            Q(alumno__username__icontains=q_busqueda) |
            Q(numero_operacion__icontains=q_busqueda)
        )

    if concepto_filtro:
        pagos_qs = pagos_qs.filter(concepto=concepto_filtro)

    if estado_filtro:
        pagos_qs = pagos_qs.filter(estado=estado_filtro)

    # Métricas de resumen
    recaudado_mes = Pago.objects.filter(
        fecha_pago__year=hoy.year,
        fecha_pago__month=hoy.month,
        estado=Pago.ESTADO_PAGADO
    ).aggregate(total=Sum('monto'))['total'] or 0.00

    total_pagos_mes = Pago.objects.filter(
        fecha_pago__year=hoy.year,
        fecha_pago__month=hoy.month,
        estado=Pago.ESTADO_PAGADO
    ).count()

    # Total alumnos activos
    total_alumnos_activos = Usuario.objects.filter(rol=Usuario.ROL_ALUMNO, is_active=True).count()
    pagos_pendientes_ids = set(Pago.objects.filter(estado='PENDIENTE').values_list('alumno_id', flat=True))
    pagos_realizados_ids = set(Pago.objects.filter(estado='PAGADO').values_list('alumno_id', flat=True))
    
    alumnos_al_dia = len(pagos_realizados_ids - pagos_pendientes_ids)
    alumnos_pendientes = len(pagos_pendientes_ids)

    alumnos_todos = Usuario.objects.filter(rol=Usuario.ROL_ALUMNO).order_by('last_name', 'first_name')
    ciclos = Ciclo.objects.filter(activo=True)

    contexto = {
        'pagos': pagos_qs[:100],
        'recaudado_mes': float(recaudado_mes),
        'total_pagos_mes': total_pagos_mes,
        'total_alumnos_activos': total_alumnos_activos,
        'alumnos_al_dia': alumnos_al_dia,
        'alumnos_pendientes': alumnos_pendientes,
        'alumnos_todos': alumnos_todos,
        'ciclos': ciclos,
        'conceptos_choices': Pago.CONCEPTOS_CHOICES,
        'estados_choices': Pago.ESTADOS_CHOICES,
        'q_busqueda': q_busqueda,
        'concepto_filtro': concepto_filtro,
        'estado_filtro': estado_filtro
    }
    return render(request, 'academico/control_pagos.html', contexto)


@login_required(login_url='iniciar_sesion')
def registrar_pago_alumno(request, alumno_id=None):
    """
    Formulario para registrar un cobro de matrícula, pensión o servicio a un alumno.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    import datetime
    from .models import Pago, Matricula

    alumno = None
    if alumno_id:
        alumno = get_object_or_404(Usuario, id=alumno_id, rol=Usuario.ROL_ALUMNO)

    if request.method == 'POST':
        selected_alumno_id = request.POST.get('alumno_id') or alumno_id
        selected_alumno = get_object_or_404(Usuario, id=selected_alumno_id, rol=Usuario.ROL_ALUMNO)

        ciclo_id = request.POST.get('ciclo_id')
        concepto = request.POST.get('concepto', Pago.CONCEPTO_MATRICULA)
        monto_str = request.POST.get('monto', '0')
        metodo_pago = request.POST.get('metodo_pago', Pago.METODO_EFECTIVO)
        numero_operacion = request.POST.get('numero_operacion', '').strip()
        fecha_pago_str = request.POST.get('fecha_pago', '').strip()
        estado = request.POST.get('estado', Pago.ESTADO_PAGADO)
        observaciones = request.POST.get('observaciones', '').strip()

        try:
            monto = float(monto_str)
            if monto <= 0:
                messages.error(request, "El monto del pago debe ser mayor a 0.")
                return redirect('registrar_pago_alumno', alumno_id=selected_alumno.id)
        except ValueError:
            messages.error(request, "Monto inválido.")
            return redirect('registrar_pago_alumno', alumno_id=selected_alumno.id)

        fecha_pago = datetime.date.today()
        if fecha_pago_str:
            try:
                fecha_pago = datetime.datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        ciclo = None
        if ciclo_id:
            ciclo = Ciclo.objects.filter(id=ciclo_id).first()
        else:
            mat = Matricula.objects.filter(alumno=selected_alumno, activo=True).first()
            if mat:
                ciclo = mat.ciclo

        from sigae.utils import log_evento_auditoria
        pago = Pago.objects.create(
            alumno=selected_alumno,
            ciclo=ciclo,
            concepto=concepto,
            monto=monto,
            estado=estado,
            metodo_pago=metodo_pago,
            numero_operacion=numero_operacion,
            fecha_pago=fecha_pago,
            observaciones=observaciones,
            registrado_por=request.user
        )

        log_evento_auditoria('PAGO_REGISTRADO', f"Cobro de S/. {monto} ({concepto}) registrado para alumno {selected_alumno.username}.", request)
        messages.success(request, f"¡Pago de S/. {monto:.2f} registrado exitosamente para {selected_alumno.get_full_name()}!")
        return redirect('historial_pagos_alumno', alumno_id=selected_alumno.id)

    alumnos = Usuario.objects.filter(rol=Usuario.ROL_ALUMNO).order_by('last_name', 'first_name')
    ciclos = Ciclo.objects.all().order_by('-activo', '-id')

    contexto = {
        'alumno_seleccionado': alumno,
        'alumnos': alumnos,
        'ciclos': ciclos,
        'conceptos_choices': Pago.CONCEPTOS_CHOICES,
        'metodos_choices': Pago.METODOS_CHOICES,
        'estados_choices': Pago.ESTADOS_CHOICES,
        'hoy_str': datetime.date.today().strftime('%Y-%m-%d')
    }
    return render(request, 'academico/registrar_pago.html', contexto)


@login_required(login_url='iniciar_sesion')
def historial_pagos_alumno(request, alumno_id):
    """
    Vista detallada del historial de pagos y cuenta corriente de un estudiante específico.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    from django.db.models import Sum
    from .models import Pago, Matricula

    alumno = get_object_or_404(Usuario, id=alumno_id, rol=Usuario.ROL_ALUMNO)
    pagos = Pago.objects.filter(alumno=alumno).select_related('ciclo', 'registrado_por').order_by('-fecha_pago', '-id')
    matricula = Matricula.objects.filter(alumno=alumno, activo=True).select_related('ciclo', 'aula').first()

    total_pagado = pagos.filter(estado=Pago.ESTADO_PAGADO).aggregate(total=Sum('monto'))['total'] or 0.00
    pagos_pendientes = pagos.filter(estado=Pago.ESTADO_PENDIENTE)

    if pagos_pendientes.exists():
        estado_financiero = 'Pensión Pendiente'
        estado_badge = 'badge-danger'
    elif total_pagado > 0:
        estado_financiero = 'Al día'
        estado_badge = 'badge-success'
    else:
        estado_financiero = 'Pensión Pendiente'
        estado_badge = 'badge-warning'

    contexto = {
        'alumno': alumno,
        'pagos': pagos,
        'matricula': matricula,
        'total_pagado': float(total_pagado),
        'pagos_pendientes_count': pagos_pendientes.count(),
        'estado_financiero': estado_financiero,
        'estado_badge': estado_badge
    }
    return render(request, 'academico/historial_pagos_alumno.html', contexto)


@login_required(login_url='iniciar_sesion')
def cambiar_estado_pago(request, pago_id):
    """
    Permite anular o cambiar el estado de un registro de pago.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso no autorizado.")
        return redirect('raiz')

    if request.method == 'POST':
        from .models import Pago
        from sigae.utils import log_evento_auditoria
        pago = get_object_or_404(Pago, id=pago_id)
        nuevo_estado = request.POST.get('nuevo_estado')
        if nuevo_estado in [Pago.ESTADO_PAGADO, Pago.ESTADO_PENDIENTE, Pago.ESTADO_ANULADO]:
            pago.estado = nuevo_estado
            pago.save()
            log_evento_auditoria('CAMBIO_ESTADO_PAGO', f"Pago ID {pago.id} cambiado a {nuevo_estado}.", request)
            messages.success(request, f"Estado del pago actualizado a: {pago.get_estado_display()}.")

        return redirect('historial_pagos_alumno', alumno_id=pago.alumno.id)

    return redirect('control_pagos')


@login_required(login_url='iniciar_sesion')
def mis_asistencias_docente(request):
    """
    Vista para que el docente consulte su propio historial de asistencias y acumulado de horas dictadas.
    """
    if request.user.rol != 'DOCENTE':
        messages.error(request, "Acceso exclusivo para docentes.")
        return redirect('raiz')

    import datetime
    from django.db.models import Sum
    from .models import AsistenciaDocente

    hoy = datetime.date.today()
    mes_seleccionado = int(request.GET.get('mes', hoy.month))
    anio_seleccionado = int(request.GET.get('anio', hoy.year))

    asistencias_qs = AsistenciaDocente.objects.filter(
        docente=request.user,
        fecha__month=mes_seleccionado,
        fecha__year=anio_seleccionado
    ).order_by('-fecha', '-hora_acceso')

    total_horas = asistencias_qs.aggregate(total=Sum('horas_dictadas'))['total'] or 0.00
    total_clases = asistencias_qs.count()
    tarifa_hora = float(request.user.precio_hora or 0.0)
    ingresos_estimados = round(float(total_horas) * tarifa_hora, 2)

    meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    anios = list(range(hoy.year - 2, hoy.year + 2))

    contexto = {
        'asistencias': asistencias_qs,
        'mes_seleccionado': mes_seleccionado,
        'anio_seleccionado': anio_seleccionado,
        'total_horas': float(total_horas),
        'total_clases': total_clases,
        'tarifa_hora': tarifa_hora,
        'ingresos_estimados': ingresos_estimados,
        'meses': meses,
        'anios': anios
    }
    return render(request, 'autenticacion/mis_asistencias_docente.html', contexto)


