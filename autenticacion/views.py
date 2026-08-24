"""
Vistas para la aplicación 'autenticacion'.

Controladores para el inicio/cierre de sesión de usuarios y visualización
de dashboards según el rol asignado (Alumno, Docente, Secretaría).
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def iniciar_sesion(request):
    """
    Controlador para el inicio de sesión.

    Si el método es POST, valida las credenciales del usuario y redirige
    automáticamente al panel adecuado según su rol. Si es GET, renderiza
    el formulario de login.
    """
    from sigae.utils import log_evento_auditoria

    if request.user.is_authenticated:
        return redirigir_segun_rol(request.user, request)

    if request.method == 'POST':
        usuario_str = request.POST.get('username', '').strip()
        clave_str = request.POST.get('password', '').strip()

        usuario = authenticate(request, username=usuario_str, password=clave_str)

        if usuario is not None:
            login(request, usuario)
            log_evento_auditoria('LOGIN_EXITOSO', f"Inicio de sesión exitoso para el rol {usuario.rol}.", request)
            return redirigir_segun_rol(usuario, request)
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
            log_evento_auditoria('LOGIN_FALLIDO', f"Intento de ingreso fallido para el username: '{usuario_str}'.", request)

    return render(request, 'autenticacion/login.html')


def cerrar_sesion(request):
    """
    Cierra la sesión activa del usuario y lo redirige al formulario de login.
    """
    from sigae.utils import log_evento_auditoria
    if request.user.is_authenticated:
        log_evento_auditoria('LOGOUT', f"Cierre de sesión del usuario.", request)
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('iniciar_sesion')


def redirigir_segun_rol(usuario, request=None):
    """
    Helper para redirigir a los usuarios al panel adecuado según su rol y tipo de dispositivo.

    En teléfonos/dispositivos móviles:
    - ALUMNO -> Mi Credencial QR (/perfil/)
    - DOCENTE -> Mi Credencial QR (/perfil/)
    - SECRETARIA -> Panel Asistencia QR (/academico/asistencia/)
    - ADMIN -> Dashboard (/dashboard/admin/)

    En computadoras de escritorio/laptops:
    - Redirige a los dashboards principales respectivos.

    Args:
        usuario (Usuario): Instancia del usuario autenticado.
        request (HttpRequest, optional): Objeto HttpRequest para detección de User-Agent.

    Returns:
        HttpResponseRedirect: Redirección al panel o credencial asignada.
    """
    is_mobile = False
    if request:
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(k in user_agent for k in ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'webos', 'blackberry', 'iemobile', 'opera mini'])

    if usuario.rol == 'ADMIN' or usuario.is_superuser or usuario.is_staff:
        return redirect('dashboard_admin')
    elif usuario.rol == 'ALUMNO':
        if is_mobile:
            return redirect('perfil_alumno')
        return redirect('dashboard_alumno')
    elif usuario.rol == 'DOCENTE':
        if is_mobile:
            return redirect('perfil_alumno')
        return redirect('dashboard_docente')
    elif usuario.rol == 'SECRETARIA':
        if is_mobile:
            return redirect('control_asistencia')
        return redirect('dashboard_secretaria')
    else:
        # En caso de no tener rol, enviar a login
        return redirect('iniciar_sesion')


@login_required(login_url='iniciar_sesion')
def dashboard_alumno(request):
    """
    Muestra el panel de control para estudiantes con métricas de su último simulacro,
    su puesto en ranking y su récord acumulado de asistencia.
    """
    if request.user.rol != 'ALUMNO':
        return redirect('iniciar_sesion')

    from simulacros.models import ResultadoSimulacro
    from academico.models import AsistenciaQR, Matricula

    # 1. Métrica de Último Simulacro rendido
    ultimo_resultado = ResultadoSimulacro.objects.filter(
        alumno=request.user
    ).select_related('simulacro').order_by('-fecha_evaluacion', '-id').first()

    if ultimo_resultado:
        area_alumno = request.user.area_academica
        puesto_ranking = ResultadoSimulacro.objects.filter(
            simulacro=ultimo_resultado.simulacro,
            alumno__area_academica=area_alumno,
            puntaje_total__gt=ultimo_resultado.puntaje_total
        ).count() + 1
        total_en_area = ResultadoSimulacro.objects.filter(
            simulacro=ultimo_resultado.simulacro,
            alumno__area_academica=area_alumno
        ).count()

        ultimo_simulacro = {
            'titulo': ultimo_resultado.simulacro.titulo,
            'puntaje': float(ultimo_resultado.puntaje_total),
            'puntaje_maximo': float(ultimo_resultado.simulacro.puntaje_maximo),
            'puesto': puesto_ranking,
            'total_area': total_en_area,
            'fecha': ultimo_resultado.simulacro.fecha
        }
    else:
        ultimo_simulacro = None

    # 2. Métrica de Récord de Asistencia en el ciclo
    matricula_activa = Matricula.objects.filter(alumno=request.user, activo=True).select_related('ciclo').first()
    asistencias_qs = AsistenciaQR.objects.filter(alumno=request.user)
    if matricula_activa and matricula_activa.ciclo:
        asistencias_ciclo = asistencias_qs.filter(
            fecha__gte=matricula_activa.ciclo.fecha_inicio,
            fecha__lte=matricula_activa.ciclo.fecha_fin
        )
    else:
        asistencias_ciclo = asistencias_qs

    total_asistencias = asistencias_ciclo.count()
    presentes = asistencias_ciclo.filter(estado=AsistenciaQR.ESTADO_PRESENTE).count()
    tardes = asistencias_ciclo.filter(estado=AsistenciaQR.ESTADO_TARDE).count()

    if total_asistencias > 0:
        porcentaje_asistencia = round(((presentes + tardes) / total_asistencias) * 100.0, 1)
    else:
        porcentaje_asistencia = 100.0 if matricula_activa else 0.0

    record_asistencia = {
        'porcentaje': porcentaje_asistencia,
        'total_sesiones': total_asistencias,
        'presentes': presentes,
        'tardes': tardes,
        'ciclo_nombre': matricula_activa.ciclo.nombre if matricula_activa else "Sin Ciclo Asignado"
    }

    contexto = {
        'ultimo_simulacro': ultimo_simulacro,
        'record_asistencia': record_asistencia
    }
    return render(request, 'autenticacion/dashboard_alumno.html', contexto)


@login_required(login_url='iniciar_sesion')
def dashboard_docente(request):
    """
    Muestra el panel de control exclusivo para docentes con métricas de horas acumuladas
    y simulacros asociados a su perfil.
    """
    if request.user.rol != 'DOCENTE':
        return redirect('iniciar_sesion')

    import datetime
    from django.db.models import Sum, Q
    from academico.models import AsistenciaDocente
    from simulacros.models import Simulacro

    hoy = datetime.date.today()
    meses_nombres = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    nombre_mes_actual = meses_nombres.get(hoy.month, '')

    # Horas dictadas acumuladas del mes actual
    asistencias_mes = AsistenciaDocente.objects.filter(
        docente=request.user,
        fecha__year=hoy.year,
        fecha__month=hoy.month
    )
    total_horas = asistencias_mes.aggregate(Sum('horas_dictadas'))['horas_dictadas__sum'] or 0.0
    total_sesiones = asistencias_mes.count()

    # Filtrar simulacros creados por el docente en sesión o asociados a sus cursos asignados
    curso = (request.user.curso_asignado or '').strip()
    filtro_simulacros = Q(docente=request.user)
    if curso:
        filtro_simulacros |= Q(titulo__icontains=curso) | Q(descripcion__icontains=curso)
    if request.user.area_academica:
        filtro_simulacros |= Q(area_academica=request.user.area_academica, docente__isnull=True)

    simulacros = Simulacro.objects.filter(activo=True).filter(filtro_simulacros).distinct().order_by('-fecha')

    contexto = {
        'simulacros': simulacros,
        'total_horas': float(total_horas),
        'total_sesiones': total_sesiones,
        'mes_actual_nombre': nombre_mes_actual,
        'anio_actual': hoy.year
    }
    return render(request, 'autenticacion/dashboard_docente.html', contexto)


@login_required(login_url='iniciar_sesion')
def dashboard_admin(request):
    """
    Panel de Control exclusivo para el Director / Administrador de la Academia.
    Muestra métricas globales del sistema, estado financiero docente y monitoreo en tiempo real.
    """
    if request.user.rol != Usuario.ROL_ADMIN and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Administradores.")
        return redirect('raiz')

    import datetime
    from academico.models import Ciclo, AsistenciaQR, AsistenciaDocente
    from simulacros.models import Simulacro

    hoy = datetime.date.today()
    meses_nombres = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    nombre_mes = meses_nombres.get(hoy.month, '')

    # 1. Métricas de Estudiantes y Docentes
    total_alumnos_activos = Usuario.objects.filter(rol=Usuario.ROL_ALUMNO, is_active=True).count()
    total_docentes_activos = Usuario.objects.filter(rol=Usuario.ROL_DOCENTE, is_active=True).count()
    total_ciclos_activos = Ciclo.objects.filter(activo=True).count()

    # 2. Métricas de Asistencia del Día
    asistencias_hoy_alumnos = AsistenciaQR.objects.filter(fecha=hoy).count()
    porcentaje_asistencia_hoy = round((asistencias_hoy_alumnos / total_alumnos_activos * 100), 1) if total_alumnos_activos > 0 else 0.0

    # 3. Métricas Financieras (Planilla Docente Estimada del Mes Actual)
    asistencias_doc_mes = AsistenciaDocente.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month
    ).select_related('docente')

    total_horas_dictadas_mes = sum(float(a.horas_dictadas) for a in asistencias_doc_mes)
    total_planilla_mes = sum(float(a.horas_dictadas) * float(a.docente.precio_hora or 0.0) for a in asistencias_doc_mes)

    # 4. Últimos Simulacros
    simulacros_recientes = Simulacro.objects.all().order_by('-fecha')[:5]

    # 5. Monitoreo de Últimas Asistencias
    ultimas_asistencias_al = AsistenciaQR.objects.select_related('alumno').order_by('-fecha', '-hora_acceso')[:6]
    ultimas_asistencias_doc = AsistenciaDocente.objects.select_related('docente').order_by('-fecha', '-hora_acceso')[:6]

    contexto = {
        'total_alumnos_activos': total_alumnos_activos,
        'total_docentes_activos': total_docentes_activos,
        'total_ciclos_activos': total_ciclos_activos,
        'asistencias_hoy_alumnos': asistencias_hoy_alumnos,
        'porcentaje_asistencia_hoy': porcentaje_asistencia_hoy,
        'total_horas_dictadas_mes': round(total_horas_dictadas_mes, 1),
        'total_planilla_mes': round(total_planilla_mes, 2),
        'mes_nombre': nombre_mes,
        'anio_actual': hoy.year,
        'simulacros_recientes': simulacros_recientes,
        'ultimas_asistencias_al': ultimas_asistencias_al,
        'ultimas_asistencias_doc': ultimas_asistencias_doc
    }
    return render(request, 'autenticacion/dashboard_admin.html', contexto)


@login_required(login_url='iniciar_sesion')
def dashboard_secretaria(request):
    """
    Muestra el panel de control exclusivo para secretaría.
    """
    if request.user.rol != 'SECRETARIA' and not request.user.is_superuser and not request.user.is_staff and request.user.rol != 'ADMIN':
        return redirect('iniciar_sesion')
        
    return render(request, 'autenticacion/dashboard_secretaria.html')


@login_required(login_url='iniciar_sesion')
def perfil_alumno(request):
    """
    Vista de perfil del usuario (Alumno o Docente).

    Renderiza los datos personales del usuario y su código QR dinámico
    de asistencia.
    """
    usuario = request.user
    if usuario.rol not in ['ALUMNO', 'DOCENTE']:
        messages.error(request, "Acceso restringido a Alumnos y Docentes.")
        return redirect('raiz')
        
    ciclo_nombre = "Ninguno"
    if usuario.rol == 'ALUMNO':
        from academico.models import Matricula
        mat = Matricula.objects.filter(alumno=usuario, activo=True).first()
        if mat:
            ciclo_nombre = mat.ciclo.nombre
    elif usuario.rol == 'DOCENTE':
        if usuario.ciclo:
            ciclo_nombre = usuario.ciclo.nombre

    return render(request, 'autenticacion/perfil_alumno.html', {'ciclo_nombre': ciclo_nombre})


from .models import Usuario


@login_required(login_url='iniciar_sesion')
def registrar_alumno(request):
    """
    Vista para que el rol de Secretaría registre a nuevos alumnos.

    Autogenera el nombre de usuario siguiendo la regla de primer nombre +
    iniciales de los apellidos, en mayúsculas, y resolviendo duplicados.
    La contraseña inicial es el DNI ingresado.

    Args:
        request: Objeto HttpRequest de Django.

    Returns:
        HttpResponse: Renderizado del formulario o redirección tras guardar.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    if request.method == 'POST':
        nombres = request.POST.get('nombres', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        dni = request.POST.get('dni', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        email = request.POST.get('email', '').strip()
        area_academica = request.POST.get('area_academica', '').strip()

        # Validaciones básicas
        if not nombres or not apellidos or not dni or not area_academica:
            messages.error(request, "Los campos Nombres, Apellidos, DNI y Área Académica son obligatorios.")
            return render(request, 'autenticacion/registrar_alumno.html')

        if area_academica not in ['INGENIERIAS', 'BIOMEDICAS', 'SOCIALES']:
            messages.error(request, "El área académica seleccionada es inválida.")
            return render(request, 'autenticacion/registrar_alumno.html')

        # Validar DNI duplicado
        if Usuario.objects.filter(dni=dni).exists():
            messages.error(request, "Ya existe un usuario registrado con este DNI.")
            return render(request, 'autenticacion/registrar_alumno.html')

        try:
            from .utils import generar_username_unico
            username = generar_username_unico(nombres, apellidos)

            # Creación del usuario Alumno
            # Por defecto, la contraseña temporal es el DNI
            nuevo_alumno = Usuario.objects.create_user(
                username=username,
                password=dni,
                first_name=nombres,
                last_name=apellidos,
                email=email,
                rol=Usuario.ROL_ALUMNO,
                dni=dni,
                telefono=telefono,
                direccion=direccion,
                area_academica=area_academica
            )
            messages.success(
                request,
                f"Alumno {nuevo_alumno.get_full_name()} registrado correctamente. "
                f"Nombre de usuario autogenerado: {username}. La contraseña inicial es su DNI."
            )
            return redirect('registrar_alumno')
        except Exception as e:
            messages.error(request, f"Ocurrió un error al guardar el estudiante: {str(e)}")

    return render(request, 'autenticacion/registrar_alumno.html')


@login_required(login_url='iniciar_sesion')
def registrar_alumno_masivo(request):
    """
    Registra alumnos de forma masiva a partir de un archivo CSV o TXT.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría y Administración.")
        return redirect('raiz')

    if request.method == 'POST':
        archivo = request.FILES.get('archivo_alumnos')
        if not archivo:
            messages.error(request, "Debe seleccionar un archivo válido.")
            return redirect('registrar_alumno')

        try:
            contenido = archivo.read().decode('utf-8')
        except Exception:
            try:
                archivo.seek(0)
                contenido = archivo.read().decode('latin-1')
            except Exception as e:
                messages.error(request, f"Error al decodificar el archivo: {str(e)}")
                return redirect('registrar_alumno')

        import csv
        from io import StringIO
        from .utils import generar_username_unico

        lineas = StringIO(contenido)
        primer_linea = lineas.readline()
        lineas.seek(0)
        delimitador = ';' if ';' in primer_linea else ','

        lector = csv.reader(lineas, delimiter=delimitador)
        registrados = 0
        errores = []

        for idx, fila in enumerate(lector, start=1):
            if not fila or len(fila) < 4:
                continue
            
            # Omitir fila si parece un encabezado
            if idx == 1 and ('nombres' in fila[0].lower() or 'dni' in ''.join(fila).lower()):
                continue

            nombres = fila[0].strip()
            apellidos = fila[1].strip()
            dni = fila[2].strip()
            area_academica = fila[3].strip().upper()
            
            telefono = fila[4].strip() if len(fila) > 4 else ''
            direccion = fila[5].strip() if len(fila) > 5 else ''
            email = fila[6].strip() if len(fila) > 6 else ''

            if not nombres or not apellidos or not dni or not area_academica:
                errores.append(f"Fila {idx}: Faltan campos obligatorios.")
                continue

            if area_academica not in ['INGENIERIAS', 'BIOMEDICAS', 'SOCIALES']:
                errores.append(f"Fila {idx}: Área académica '{area_academica}' inválida.")
                continue

            if len(dni) != 8 or not dni.isdigit():
                errores.append(f"Fila {idx}: DNI '{dni}' debe tener 8 dígitos.")
                continue

            if Usuario.objects.filter(dni=dni).exists():
                errores.append(f"Fila {idx}: DNI '{dni}' ya registrado.")
                continue

            try:
                username = generar_username_unico(nombres, apellidos)
                Usuario.objects.create_user(
                    username=username,
                    password=dni,
                    first_name=nombres,
                    last_name=apellidos,
                    email=email,
                    rol=Usuario.ROL_ALUMNO,
                    dni=dni,
                    telefono=telefono,
                    direccion=direccion,
                    area_academica=area_academica
                )
                registrados += 1
            except Exception as e:
                errores.append(f"Fila {idx}: Error: {str(e)}")

        if registrados > 0:
            messages.success(request, f"¡Se registraron {registrados} alumnos de golpe exitosamente!")
        if errores:
            if len(errores) > 5:
                messages.warning(request, f"Hubo problemas en algunas filas: {', '.join(errores[:5])} y {len(errores)-5} más.")
            else:
                messages.warning(request, f"Hubo problemas: {', '.join(errores)}")

    return redirect('registrar_alumno')


@login_required(login_url='iniciar_sesion')
def descargar_plantilla_alumnos(request):
    """
    Genera y descarga un archivo CSV plantilla de ejemplo para la carga masiva de alumnos.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido.")
        return redirect('raiz')

    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="plantilla_alumnos_sigae.csv"'
    
    # Escribir BOM UTF-8 para compatibilidad perfecta con Microsoft Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['Nombres', 'Apellidos', 'DNI', 'Area_Academica', 'Telefono', 'Direccion', 'Email'])
    writer.writerow(['Juan Carlos', 'Perez Quispe', '71234567', 'INGENIERIAS', '951234567', 'Av. Floral 123, Puno', 'juan.perez@ejemplo.com'])
    writer.writerow(['Maria Elena', 'Luna Gomez', '72345678', 'BIOMEDICAS', '952345678', 'Jr. Puno 456, Juliaca', 'maria.luna@ejemplo.com'])
    writer.writerow(['Carlos Alberto', 'Condori Ramos', '73456789', 'SOCIALES', '953456789', 'Av. El Sol 789, Puno', 'carlos.condori@ejemplo.com'])
    
    return response


@login_required(login_url='iniciar_sesion')
def listar_alumnos(request):
    """
    Vista de Padrón General de Alumnos con buscador, filtros por área, estado y situación de pago.
    Accesible para Secretaría y Administradores.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría o Administradores.")
        return redirect('raiz')

    from django.db.models import Q
    from academico.models import Matricula, Pago

    query = request.GET.get('q', '').strip()
    area_filtro = request.GET.get('area', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    alumnos_qs = Usuario.objects.filter(rol=Usuario.ROL_ALUMNO).order_by('last_name', 'first_name')

    if query:
        alumnos_qs = alumnos_qs.filter(
            Q(dni__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query)
        )

    if area_filtro in ['INGENIERIAS', 'BIOMEDICAS', 'SOCIALES']:
        alumnos_qs = alumnos_qs.filter(area_academica=area_filtro)

    if estado_filtro == 'activo':
        alumnos_qs = alumnos_qs.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        alumnos_qs = alumnos_qs.filter(is_active=False)

    matriculas_activas = {
        m.alumno_id: m.ciclo.nombre
        for m in Matricula.objects.filter(activo=True).select_related('ciclo')
    }

    pagos_pendientes_set = set(Pago.objects.filter(estado='PENDIENTE').values_list('alumno_id', flat=True))
    pagos_realizados_set = set(Pago.objects.filter(estado='PAGADO').values_list('alumno_id', flat=True))

    lista_alumnos = []
    for al in alumnos_qs:
        if al.id in pagos_pendientes_set:
            estado_pago = 'Pensión Pendiente'
            estado_pago_badge = 'badge-danger'
        elif al.id in pagos_realizados_set:
            estado_pago = 'Al día'
            estado_pago_badge = 'badge-success'
        else:
            estado_pago = 'Pensión Pendiente'
            estado_pago_badge = 'badge-warning'

        lista_alumnos.append({
            'id': al.id,
            'username': al.username,
            'nombres_completos': al.get_full_name() or al.username,
            'first_name': al.first_name,
            'last_name': al.last_name,
            'dni': al.dni or '-',
            'area_display': al.get_area_academica_display() or 'No asignada',
            'area_code': al.area_academica,
            'telefono': al.telefono or '-',
            'email': al.email or '-',
            'direccion': al.direccion or '-',
            'is_active': al.is_active,
            'ciclo_actual': matriculas_activas.get(al.id, 'Sin Matrícula Activa'),
            'estado_pago': estado_pago,
            'estado_pago_badge': estado_pago_badge
        })

    contexto = {
        'alumnos': lista_alumnos,
        'query': query,
        'area_filtro': area_filtro,
        'estado_filtro': estado_filtro,
        'total_alumnos': len(lista_alumnos),
        'areas_choices': Usuario.AREAS_CHOICES
    }
    return render(request, 'autenticacion/listar_alumnos.html', contexto)


@login_required(login_url='iniciar_sesion')
def exportar_alumnos_csv(request):
    """
    Exporta el padrón general de alumnos en formato CSV compatible con Microsoft Excel (UTF-8 con BOM).
    Accesible para Administrador y Secretaría.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal autorizado.")
        return redirect('raiz')

    import csv
    import datetime
    from django.http import HttpResponse
    from academico.models import Matricula, Pago

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    fecha_str = datetime.date.today().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="padron_alumnos_sigae_{fecha_str}.csv"'
    response.write('\ufeff')  # BOM para apertura directa en Excel con tildes y caracteres especiales

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID', 'DNI', 'Apellidos', 'Nombres', 'Usuario', 'Area Academica',
        'Ciclo Matriculado', 'Estado Cuenta', 'Estado Pensiones', 'Telefono', 'Email', 'Direccion'
    ])

    matriculas_activas = {
        m.alumno_id: m.ciclo.nombre
        for m in Matricula.objects.filter(activo=True).select_related('ciclo')
    }

    pagos_pendientes_set = set(Pago.objects.filter(estado='PENDIENTE').values_list('alumno_id', flat=True))
    pagos_realizados_set = set(Pago.objects.filter(estado='PAGADO').values_list('alumno_id', flat=True))

    alumnos = Usuario.objects.filter(rol=Usuario.ROL_ALUMNO).order_by('last_name', 'first_name')
    for al in alumnos:
        if al.id in pagos_pendientes_set:
            estado_pago = 'Pension Pendiente'
        elif al.id in pagos_realizados_set:
            estado_pago = 'Al dia'
        else:
            estado_pago = 'Pension Pendiente'

        writer.writerow([
            al.id,
            al.dni or '',
            al.last_name or '',
            al.first_name or '',
            al.username,
            al.get_area_academica_display() or 'No asignada',
            matriculas_activas.get(al.id, 'Sin Matricula Activa'),
            'Activo' if al.is_active else 'Inactivo',
            estado_pago,
            al.telefono or '',
            al.email or '',
            al.direccion or ''
        ])

    return response


@login_required(login_url='iniciar_sesion')
def editar_alumno(request, alumno_id):
    """
    Vista para editar los datos básicos de un alumno (contacto, área académica, ciclo, estado).
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría o Administradores.")
        return redirect('raiz')

    from django.shortcuts import get_object_or_404
    from academico.models import Ciclo, Matricula

    alumno = get_object_or_404(Usuario, id=alumno_id, rol=Usuario.ROL_ALUMNO)
    ciclos = Ciclo.objects.all().order_by('-activo', '-fecha_inicio')
    matricula_actual = Matricula.objects.filter(alumno=alumno, activo=True).first()

    if request.method == 'POST':
        nombres = request.POST.get('nombres', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        email = request.POST.get('email', '').strip()
        area_academica = request.POST.get('area_academica', '').strip()
        ciclo_id = request.POST.get('ciclo_id', '').strip()
        is_active = request.POST.get('is_active') == '1'

        if not nombres or not apellidos or not area_academica:
            messages.error(request, "Nombres, Apellidos y Área Académica son obligatorios.")
            return render(request, 'autenticacion/editar_alumno.html', {
                'alumno': alumno,
                'ciclos': ciclos,
                'matricula_actual': matricula_actual,
                'areas_choices': Usuario.AREAS_CHOICES
            })

        alumno.first_name = nombres
        alumno.last_name = apellidos
        alumno.telefono = telefono
        alumno.direccion = direccion
        alumno.email = email
        alumno.area_academica = area_academica
        alumno.is_active = is_active
        alumno.save()

        # Gestión del Ciclo / Matrícula
        if ciclo_id:
            ciclo_nuevo = Ciclo.objects.filter(id=ciclo_id).first()
            if ciclo_nuevo:
                if matricula_actual and matricula_actual.ciclo_id != ciclo_nuevo.id:
                    matricula_actual.activo = False
                    matricula_actual.save()
                    Matricula.objects.update_or_create(
                        alumno=alumno,
                        ciclo=ciclo_nuevo,
                        defaults={
                            'codigo_matricula': f"EULER-{ciclo_nuevo.id}-{alumno.id}",
                            'activo': True
                        }
                    )
                elif not matricula_actual:
                    Matricula.objects.create(
                        alumno=alumno,
                        ciclo=ciclo_nuevo,
                        codigo_matricula=f"EULER-{ciclo_nuevo.id}-{alumno.id}",
                        activo=True
                    )
        elif matricula_actual:
            matricula_actual.activo = False
            matricula_actual.save()

        messages.success(request, f"¡Datos del alumno {alumno.get_full_name()} actualizados con éxito!")
        return redirect('listar_alumnos')

    return render(request, 'autenticacion/editar_alumno.html', {
        'alumno': alumno,
        'ciclos': ciclos,
        'matricula_actual': matricula_actual,
        'areas_choices': Usuario.AREAS_CHOICES
    })


@login_required(login_url='iniciar_sesion')
def cambiar_estado_alumno(request, alumno_id):
    """
    Alterna el estado Activo / Inactivo de un alumno.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a personal de Secretaría o Administradores.")
        return redirect('raiz')

    if request.method == 'POST':
        from django.shortcuts import get_object_or_404
        from sigae.utils import log_evento_auditoria
        alumno = get_object_or_404(Usuario, id=alumno_id, rol=Usuario.ROL_ALUMNO)
        alumno.is_active = not alumno.is_active
        alumno.save()
        nuevo_estado = "Activo" if alumno.is_active else "Inactivo"
        messages.success(request, f"El estado del alumno {alumno.get_full_name()} ahora es: {nuevo_estado}.")
        log_evento_auditoria('CAMBIO_ESTADO_ALUMNO', f"Alumno {alumno.username} cambiado a {nuevo_estado}.", request)

    return redirect('listar_alumnos')


@login_required(login_url='iniciar_sesion')
def registrar_docente(request):
    """
    Vista reservada para que el Administrador registre nuevos docentes.
    Genera automáticamente el username (mayúsculas, sin colisiones)
    y la contraseña por defecto es el DNI.
    """
    from academico.models import Ciclo
    ciclos = Ciclo.objects.filter(activo=True)

    if request.user.rol != 'ADMIN' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido exclusivamente a Administradores del sistema.")
        return redirect('raiz')

    if request.method == 'POST':
        nombres = request.POST.get('nombres', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        dni = request.POST.get('dni', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        email = request.POST.get('email', '').strip()
        curso_asignado = request.POST.get('curso_asignado', '').strip()
        precio_hora_str = request.POST.get('precio_hora', '0.00').strip()
        ciclo_id = request.POST.get('ciclo', '').strip()

        if not nombres or not apellidos or not dni or not curso_asignado:
            messages.error(request, "Los campos Nombres, Apellidos, DNI y Curso Asignado son obligatorios.")
            return render(request, 'autenticacion/registrar_docente.html', {'ciclos': ciclos})

        if Usuario.objects.filter(dni=dni).exists():
            messages.error(request, "Ya existe un usuario registrado con este DNI.")
            return render(request, 'autenticacion/registrar_docente.html', {'ciclos': ciclos})

        try:
            from .utils import generar_username_unico
            username = generar_username_unico(nombres, apellidos)
            
            # Crear docente
            nuevo_docente = Usuario.objects.create_user(
                username=username,
                password=dni,
                first_name=nombres,
                last_name=apellidos,
                email=email,
                rol=Usuario.ROL_DOCENTE,
                dni=dni,
                telefono=telefono,
                direccion=direccion,
                curso_asignado=curso_asignado,
                precio_hora=precio_hora_str
            )
            
            if ciclo_id:
                nuevo_docente.ciclo_id = int(ciclo_id)
                nuevo_docente.save()
            
            messages.success(
                request,
                f"Docente {nuevo_docente.get_full_name()} registrado con éxito. "
                f"Username: {username}. Contraseña inicial: DNI."
            )
            return redirect('listar_docentes')
        except Exception as e:
            messages.error(request, f"Error al guardar docente: {str(e)}")

    return render(request, 'autenticacion/registrar_docente.html', {'ciclos': ciclos})


@login_required(login_url='iniciar_sesion')
def listar_docentes(request):
    """
    Vista de Plana Docente para listar, buscar y gestionar a los docentes de la academia.
    Accesible exclusivamente para Administradores.
    """
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Administradores.")
        return redirect('raiz')

    from django.db.models import Q
    query = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '').strip()

    docentes_qs = Usuario.objects.filter(rol=Usuario.ROL_DOCENTE).order_by('last_name', 'first_name')

    if query:
        docentes_qs = docentes_qs.filter(
            Q(dni__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(curso_asignado__icontains=query) |
            Q(username__icontains=query)
        )

    if estado_filtro == 'activo':
        docentes_qs = docentes_qs.filter(is_active=True)
    elif estado_filtro == 'inactivo':
        docentes_qs = docentes_qs.filter(is_active=False)

    docentes = []
    for doc in docentes_qs:
        docentes.append({
            'id': doc.id,
            'username': doc.username,
            'nombres_completos': doc.get_full_name() or doc.username,
            'dni': doc.dni or '-',
            'curso_asignado': doc.curso_asignado or 'Sin asignar',
            'precio_hora': float(doc.precio_hora or 0.0),
            'telefono': doc.telefono or '-',
            'email': doc.email or '-',
            'direccion': doc.direccion or '-',
            'is_active': doc.is_active,
            'ciclo_nombre': doc.ciclo.nombre if doc.ciclo else 'General'
        })

    contexto = {
        'docentes': docentes,
        'query': query,
        'estado_filtro': estado_filtro,
        'total_docentes': len(docentes)
    }
    return render(request, 'autenticacion/listar_docentes.html', contexto)


@login_required(login_url='iniciar_sesion')
def editar_docente(request, docente_id):
    """
    Vista para editar la información, curso y tarifa por hora de un docente.
    """
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Administradores.")
        return redirect('raiz')

    from django.shortcuts import get_object_or_404
    from academico.models import Ciclo

    docente = get_object_or_404(Usuario, id=docente_id, rol=Usuario.ROL_DOCENTE)
    ciclos = Ciclo.objects.filter(activo=True)

    if request.method == 'POST':
        nombres = request.POST.get('nombres', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        email = request.POST.get('email', '').strip()
        curso_asignado = request.POST.get('curso_asignado', '').strip()
        precio_hora = request.POST.get('precio_hora', '0.00').strip()
        ciclo_id = request.POST.get('ciclo', '').strip()
        is_active = request.POST.get('is_active') == '1'

        if not nombres or not apellidos or not curso_asignado:
            messages.error(request, "Nombres, Apellidos y Curso Asignado son obligatorios.")
            return render(request, 'autenticacion/editar_docente.html', {
                'docente': docente,
                'ciclos': ciclos
            })

        docente.first_name = nombres
        docente.last_name = apellidos
        docente.telefono = telefono
        docente.direccion = direccion
        docente.email = email
        docente.curso_asignado = curso_asignado
        docente.precio_hora = precio_hora
        docente.is_active = is_active
        if ciclo_id:
            docente.ciclo_id = int(ciclo_id)
        else:
            docente.ciclo = None
        docente.save()

        messages.success(request, f"¡Docente {docente.get_full_name()} actualizado con éxito!")
        return redirect('listar_docentes')

    return render(request, 'autenticacion/editar_docente.html', {
        'docente': docente,
        'ciclos': ciclos
    })


@login_required(login_url='iniciar_sesion')
def cambiar_estado_docente(request, docente_id):
    """
    Alterna el estado Activo / Inactivo de un docente.
    """
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Administradores.")
        return redirect('raiz')

    if request.method == 'POST':
        from django.shortcuts import get_object_or_404
        from sigae.utils import log_evento_auditoria
        docente = get_object_or_404(Usuario, id=docente_id, rol=Usuario.ROL_DOCENTE)
        docente.is_active = not docente.is_active
        docente.save()
        nuevo_estado = "Activo" if docente.is_active else "Inactivo"
        messages.success(request, f"El estado del docente {docente.get_full_name()} ahora es: {nuevo_estado}.")
        log_evento_auditoria('CAMBIO_ESTADO_DOCENTE', f"Docente {docente.username} cambiado a {nuevo_estado}.", request)

    return redirect('listar_docentes')


from django.http import JsonResponse
from .utils import generar_token_qr

@login_required(login_url='iniciar_sesion')
def generar_token_qr_api(request):
    """
    Endpoint de API para generar un token QR dinámico firmado con HMAC
    para el usuario actualmente autenticado (Alumno o Docente).
    """
    if request.user.rol not in ['ALUMNO', 'DOCENTE']:
        return JsonResponse({'error': 'Acceso no autorizado para este rol.'}, status=403)
        
    token = generar_token_qr(request.user)
    return JsonResponse({
        'token_qr': token,
        'expires_in': 15
    })


