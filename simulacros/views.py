"""
Vistas para la aplicación 'simulacros'.

Define controladores para el listado de exámenes disponibles, la hoja de
rendición de pruebas y el procesamiento automático de las respuestas marcadas.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from .models import DetalleRespuesta, Pregunta, ResultadoSimulacro, Simulacro


@login_required(login_url='iniciar_sesion')
def listar_simulacros(request):
    """
    Lista los simulacros activos pendientes e el historial de simulacros rendidos.
    """
    if request.user.rol != 'ALUMNO':
        messages.error(request, "Acceso restringido a Alumnos.")
        return redirect('raiz')

    area_alumno = request.user.area_academica
    
    # Obtener los IDs de simulacros ya rendidos
    resultados_ids = ResultadoSimulacro.objects.filter(alumno=request.user).values_list('simulacro_id', flat=True)

    if not area_alumno:
        simulacros_activos = Simulacro.objects.none()
    else:
        # Simulacros activos del área del alumno que aún no han sido rendidos
        simulacros_activos = Simulacro.objects.filter(
            activo=True, 
            area_academica=area_alumno
        ).exclude(id__in=resultados_ids).order_by('-fecha')
    
    # Historial de simulacros rendidos con cálculo de ranking en su área
    historial_qs = ResultadoSimulacro.objects.filter(alumno=request.user).select_related('simulacro').order_by('-simulacro__fecha')
    
    historial_rendidos = []
    for res in historial_qs:
        puesto = ResultadoSimulacro.objects.filter(
            simulacro=res.simulacro,
            alumno__area_academica=area_alumno,
            puntaje_total__gt=res.puntaje_total
        ).count() + 1
        total_evaluados = ResultadoSimulacro.objects.filter(
            simulacro=res.simulacro,
            alumno__area_academica=area_alumno
        ).count()

        historial_rendidos.append({
            'resultado': res,
            'simulacro': res.simulacro,
            'puntaje_total': res.puntaje_total,
            'puesto': puesto,
            'total_evaluados': total_evaluados
        })

    contexto = {
        'simulacros_activos': simulacros_activos,
        'historial_rendidos': historial_rendidos
    }
    return render(request, 'simulacros/listar_simulacros.html', contexto)


@login_required(login_url='iniciar_sesion')
def rendir_simulacro(request, simulacro_id):
    """
    Renderiza la hoja de examen con el banco de preguntas asociadas.

    Previene que un alumno rinda más de una vez el mismo examen.

    Args:
        request: Objeto HttpRequest de Django.
        simulacro_id (int): Identificador único del simulacro a rendir.

    Returns:
        HttpResponse: Renderizado del examen o redirección si ya fue rendido.
    """
    if request.user.rol != 'ALUMNO':
        messages.error(request, "Acceso restringido a Alumnos.")
        return redirect('raiz')

    simulacro = get_object_or_404(Simulacro, id=simulacro_id, activo=True)

    # Validar área académica
    if request.user.area_academica != simulacro.area_academica:
        messages.error(request, "Este simulacro no corresponde a tu área académica.")
        return redirect('listar_simulacros')

    # Validar si ya se rindió la evaluación
    if ResultadoSimulacro.objects.filter(alumno=request.user, simulacro=simulacro).exists():
        messages.warning(request, "Ya has rendido este simulacro previamente.")
        return redirect('listar_simulacros')

    preguntas = Pregunta.objects.filter(simulacro=simulacro).order_by('numero_pregunta')

    contexto = {
        'simulacro': simulacro,
        'preguntas': preguntas
    }
    return render(request, 'simulacros/rendir_simulacro.html', contexto)


@login_required(login_url='iniciar_sesion')
def procesar_respuestas(request, simulacro_id):
    """
    Procesa las respuestas enviadas por el alumno (POST).

    Crea el registro de ResultadoSimulacro e inserta fila a fila cada
    DetalleRespuesta, gatillando el cálculo automático de notas.

    Args:
        request: Objeto HttpRequest de Django.
        simulacro_id (int): Identificador único del simulacro.

    Returns:
        HttpResponseRedirect: Redirección al ranking de mérito del simulacro.
    """
    if request.method != 'POST':
        return redirect('listar_simulacros')

    if request.user.rol != 'ALUMNO':
        messages.error(request, "Acceso restringido a Alumnos.")
        return redirect('raiz')

    simulacro = get_object_or_404(Simulacro, id=simulacro_id, activo=True)

    # Validar área académica
    if request.user.area_academica != simulacro.area_academica:
        messages.error(request, "Este simulacro no corresponde a tu área académica.")
        return redirect('listar_simulacros')

    # Prevenir envíos múltiples concurrentes/duplicados
    resultado, creado = ResultadoSimulacro.objects.get_or_create(
        alumno=request.user,
        simulacro=simulacro
    )

    if not creado:
        messages.warning(request, "Ya has enviado tus respuestas para este examen.")
        return redirect('listar_simulacros')

    preguntas = Pregunta.objects.filter(simulacro=simulacro)

    # Registrar cada respuesta
    for preg in preguntas:
        respuesta_marcada = request.POST.get(f'pregunta_{preg.id}', 'O')
        DetalleRespuesta.objects.create(
            resultado=resultado,
            pregunta=preg,
            alternativa_marcada=respuesta_marcada
        )

    # El método save() del detalle calcula el acumulado del padre en cada creación
    messages.success(request, f"¡Examen finalizado! Tu puntaje total fue: {resultado.puntaje_total}")
    
    # Redirigir al ranking de mérito del simulacro (definido en el módulo de reportes)
    return redirect('ver_ranking_html', simulacro_id=simulacro.id)


import csv
import io

from django.http import HttpResponse


@login_required(login_url='iniciar_sesion')
def descargar_plantilla_simulacro(request):
    """
    Genera y descarga un archivo CSV plantilla de ejemplo para la carga de preguntas y claves de simulacros.
    """
    if request.user.rol != 'DOCENTE' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso no autorizado.")
        return redirect('raiz')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="plantilla_simulacro_sigae.csv"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['NroPregunta', 'Enunciado', 'AlternativaA', 'AlternativaB', 'AlternativaC', 'AlternativaD', 'AlternativaE', 'AlternativaCorrecta'])
    writer.writerow(['1', '¿Cuál es el valor de x en la ecuación 2x + 6 = 14?', '2', '4', '6', '8', '10', 'B'])
    writer.writerow(['2', '¿Cuál es la función principal de la clorofila en las plantas?', 'Absorber luz para la fotosíntesis', 'Transportar savia elaborada', 'Proteger contra plagas', 'Almacenar reservas de agua', 'Fijar nitrógeno molecular', 'A'])
    writer.writerow(['3', '¿En qué año se proclamó la Independencia del Perú?', '1810', '1820', '1821', '1824', '1879', 'C'])
    writer.writerow(['4', '¿Cuál es el elemento químico con símbolo Na?', 'Níquel', 'Nitrógeno', 'Sodio', 'Neón', 'Nobelio', 'C'])
    writer.writerow(['5', '¿Qué figura literaria se utiliza en: Las perlas de tu boca?', 'Metáfora', 'Hipérbole', 'Anáfora', 'Símil', 'Epíteto', 'A'])

    return response


@login_required(login_url='iniciar_sesion')
def listar_simulacros_admin(request):
    """
    Vista consolidada de banco de simulacros para el Administrador / Director.
    Permite consultar todos los simulacros, ver notas, ranking general y subir nuevos exámenes.
    """
    if request.user.rol != 'ADMIN' and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Administradores.")
        return redirect('raiz')

    simulacros = Simulacro.objects.all().select_related('docente').order_by('-fecha')

    contexto = {
        'simulacros': simulacros
    }
    return render(request, 'simulacros/listar_simulacros_admin.html', contexto)


@login_required(login_url='iniciar_sesion')
def subir_simulacro_claves(request):
    """
    Vista para que los docentes y administradores carguen un nuevo simulacro y sus preguntas
    a partir de un archivo plano CSV/TXT.
    """
    if request.user.rol not in ['DOCENTE', 'ADMIN'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso restringido a Docentes y Administradores.")
        return redirect('raiz')

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        fecha_str = request.POST.get('fecha', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        puntaje_maximo = request.POST.get('puntaje_maximo', '400.00').strip()
        
        # Configuración de puntaje de respuestas (con soporte de puntaje libre y sin penalizaciones)
        pt_correcta = request.POST.get('puntaje_correcta', '4.00').strip()
        pt_incorrecta = request.POST.get('puntaje_incorrecta', '0.00').strip()
        pt_omitida = request.POST.get('puntaje_omitida', '0.00').strip()
        area_academica = request.POST.get('area_academica', request.user.area_academica or 'INGENIERIAS').strip()

        archivo = request.FILES.get('archivo')

        if not titulo or not fecha_str or not archivo:
            messages.error(request, "El título, fecha y archivo de preguntas son obligatorios.")
            return render(request, 'simulacros/crear_simulacro_claves.html')

        try:
            # Crear el Simulacro asociado al docente en sesión
            simulacro = Simulacro.objects.create(
                titulo=titulo,
                fecha=fecha_str,
                descripcion=descripcion,
                area_academica=area_academica,
                puntaje_maximo=puntaje_maximo,
                docente=request.user,
                activo=True
            )

            # Leer y decodificar el archivo
            file_data = archivo.read().decode('utf-8')
            csv_file = io.StringIO(file_data)
            
            # Detectar delimitador
            first_line = csv_file.readline()
            delimiter = ';' if ';' in first_line else ','
            csv_file.seek(0)

            reader = csv.reader(csv_file, delimiter=delimiter)
            
            preguntas_creadas = 0
            for row in reader:
                if not row or len(row) < 8:
                    continue
                    
                # Ignorar encabezados
                if row[0].lower().startswith('num') or row[0].lower().startswith('pregunta'):
                    continue

                try:
                    num_preg = int(row[0])
                    enunciado = row[1].strip()
                    alt_a = row[2].strip()
                    alt_b = row[3].strip()
                    alt_c = row[4].strip()
                    alt_d = row[5].strip()
                    alt_e = row[6].strip()
                    alt_correcta = row[7].strip().upper()
                except (ValueError, IndexError):
                    continue

                # Crear la pregunta
                Pregunta.objects.create(
                    simulacro=simulacro,
                    numero_pregunta=num_preg,
                    enunciado=enunciado,
                    alternativa_a=alt_a,
                    alternativa_b=alt_b,
                    alternativa_c=alt_c,
                    alternativa_d=alt_d,
                    alternativa_e=alt_e,
                    alternativa_correcta=alt_correcta,
                    puntaje_correcta=pt_correcta,
                    puntaje_incorrecta=pt_incorrecta,
                    puntaje_omitida=pt_omitida
                )
                preguntas_creadas += 1

            if preguntas_creadas == 0:
                simulacro.delete()
                messages.error(request, "No se pudieron procesar preguntas del archivo. Revise el formato (ej. Nro;Enunciado;A;B;C;D;E;Clave).")
            else:
                messages.success(request, f"¡Simulacro '{titulo}' creado con éxito con {preguntas_creadas} preguntas!")
                return redirect('dashboard_docente')

        except Exception as e:
            messages.error(request, f"Error al procesar el archivo: {str(e)}")

    return render(request, 'simulacros/crear_simulacro_claves.html')


@login_required(login_url='iniciar_sesion')
def ver_revision_simulacro(request, simulacro_id, alumno_id=None):
    """
    Vista detallada para que el alumno revise su simulacro rendido:
    cantidad de aciertos, desaciertos, omitidas y desglose de cada pregunta con sus claves y puntajes.
    """
    target_alumno = request.user
    if alumno_id and (request.user.rol in ['ADMIN', 'DOCENTE', 'SECRETARIA'] or request.user.is_superuser):
        from django.contrib.auth import get_user_model
        Usuario = get_user_model()
        target_alumno = get_object_or_404(Usuario, id=alumno_id)

    simulacro = get_object_or_404(Simulacro, id=simulacro_id)
    resultado = get_object_or_404(ResultadoSimulacro, alumno=target_alumno, simulacro=simulacro)

    # Calcular puesto y total evaluados en su área
    puesto = ResultadoSimulacro.objects.filter(
        simulacro=simulacro,
        alumno__area_academica=target_alumno.area_academica,
        puntaje_total__gt=resultado.puntaje_total
    ).count() + 1

    total_evaluados_area = ResultadoSimulacro.objects.filter(
        simulacro=simulacro,
        alumno__area_academica=target_alumno.area_academica
    ).count()

    detalles_respuestas = DetalleRespuesta.objects.filter(
        resultado=resultado
    ).select_related('pregunta').order_by('pregunta__numero_pregunta')

    lista_desglose = []
    for det in detalles_respuestas:
        preg = det.pregunta
        if det.alternativa_marcada == 'O':
            estado_resp = 'OMITIDA'
            estado_badge = 'badge-warning'
            estado_texto = 'Omitida / En Blanco'
        elif det.alternativa_marcada == preg.alternativa_correcta:
            estado_resp = 'CORRECTA'
            estado_badge = 'badge-success'
            estado_texto = 'Correcta'
        else:
            estado_resp = 'INCORRECTA'
            estado_badge = 'badge-danger'
            estado_texto = 'Incorrecta'

        lista_desglose.append({
            'numero': preg.numero_pregunta,
            'enunciado': preg.enunciado,
            'alternativa_a': preg.alternativa_a,
            'alternativa_b': preg.alternativa_b,
            'alternativa_c': preg.alternativa_c,
            'alternativa_d': preg.alternativa_d,
            'alternativa_e': preg.alternativa_e,
            'clave_correcta': preg.alternativa_correcta,
            'clave_marcada': det.alternativa_marcada,
            'puntaje': det.puntaje_obtenido,
            'estado_resp': estado_resp,
            'estado_badge': estado_badge,
            'estado_texto': estado_texto
        })

    porcentaje_acierto = 0.0
    total_preguntas = len(lista_desglose)
    if total_preguntas > 0:
        porcentaje_acierto = round((resultado.respuestas_correctas / total_preguntas) * 100.0, 1)

    contexto = {
        'simulacro': simulacro,
        'resultado': resultado,
        'alumno': target_alumno,
        'puesto': puesto,
        'total_evaluados_area': total_evaluados_area,
        'desglose': lista_desglose,
        'total_preguntas': total_preguntas,
        'porcentaje_acierto': porcentaje_acierto
    }
    return render(request, 'simulacros/revision_simulacro.html', contexto)


@login_required(login_url='iniciar_sesion')
def exportar_ranking_simulacro_csv(request, simulacro_id):
    """
    Exporta la sábana de notas y cuadro de méritos del simulacro a archivo CSV compatible con Excel.
    """
    if request.user.rol not in ['SECRETARIA', 'ADMIN', 'DOCENTE'] and not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "Acceso no autorizado.")
        return redirect('raiz')

    import csv
    from django.http import HttpResponse

    simulacro = get_object_or_404(Simulacro, id=simulacro_id)
    resultados = ResultadoSimulacro.objects.filter(
        simulacro=simulacro
    ).select_related('alumno').order_by('-puntaje_total')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"ranking_simulacro_{simulacro.id}_{simulacro.fecha.strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Puesto General', 'DNI', 'Apellidos', 'Nombres', 'Usuario', 'Area Academica',
        'Correctas', 'Incorrectas', 'Omitidas', 'Puntaje Obtenido', 'Puntaje Maximo', 'Rendimiento (%)'
    ])

    for i, res in enumerate(resultados, start=1):
        rendimiento = 0.0
        if float(simulacro.puntaje_maximo) > 0:
            rendimiento = round((float(res.puntaje_total) / float(simulacro.puntaje_maximo)) * 100.0, 1)

        writer.writerow([
            i,
            res.alumno.dni or '',
            res.alumno.last_name or '',
            res.alumno.first_name or '',
            res.alumno.username,
            res.alumno.get_area_academica_display() or 'General',
            res.respuestas_correctas,
            res.respuestas_incorrectas,
            res.respuestas_omitidas,
            f"{float(res.puntaje_total):.2f}",
            f"{float(simulacro.puntaje_maximo):.2f}",
            f"{rendimiento:.1f}%"
        ])

    return response

