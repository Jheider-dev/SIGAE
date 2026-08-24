# SIGAE - Sistema Integral de Gestión Académica y Evaluación
### Academia Preuniversitaria Euler

**SIGAE** es una plataforma web modular e inteligente diseñada específicamente para optimizar la administración académica, el control de accesos de estudiantes mediante códigos QR en tiempo real y el procesamiento analítico de simulacros para la **Academia Preuniversitaria Euler**.

---

## Características y Módulos Principales

### 1. Autenticación y Control de Roles (RBAC)
*   **Acceso Restringido**: Sistema de inicio de sesión seguro con diferenciación estricta de roles (`Alumno`, `Docente` y `Secretaría`).
*   **Dashboards Personalizados**: Paneles de control adaptados visual y funcionalmente según los permisos del usuario activo.

### 2. Registro Automatizado y Reglas de Negocio (Secretaría)
*   **Ficha de Inscripción**: Formulario administrativo para el alta de nuevos estudiantes.
*   **Algoritmo de Username Autogenerado**: Genera automáticamente nombres de usuario en mayúsculas uniendo el primer nombre y las iniciales de los apellidos (ej. "Jaime Perez Condori" -> `JAIMEPC`).
*   **Resolución de Colisiones**: Manejo inteligente de nombres duplicados agregando un sufijo correlativo numérico incremental (ej. `JAIMEPC1`, `JAIMEPC2`).
*   **Seguridad Inicial**: Asignación automática de contraseña temporal idéntica al DNI del alumno registrado.

### 3. Control de Asistencia QR en Tiempo Real
*   **Credencial QR Digital**: Los estudiantes disponen en su perfil de una tarjeta con su código QR personal encriptado en el formato `SIGAE-ALUMNO-<id_usuario>`, renderizado en cliente mediante `qrcode.js` para optimizar rendimiento.
*   **Escáner QR por Webcam**: El panel de Secretaría utiliza la webcam y la librería `html5-qrcode` para realizar escaneos interactivos en vivo de las credenciales de los alumnos.
*   **UX Dinámica**:
    *   Registro e inserción instantánea del historial en pantalla sin recarga de página (Fetch API / AJAX).
    *   Tono sonoro de confirmación sintetizado ("Beep") al marcar la entrada con éxito.
    *   Retardo anti-rebotes de 3.5 segundos para evitar registros duplicados accidentales.

### 4. Módulo Académico y Simulacros de Evaluación
*   **Gestión de Ciclos y Aulas**: Creación y organización de aulas de preparación y ciclos académicos.
*   **Hojas de Respuestas Electrónicas**: Interfaz interactiva para que los alumnos rindan simulacros de opción múltiple (A, B, C, D, E y Omitida).
*   **Cálculo Automatizado**: Procesamiento inmediato de puntajes basados en reglas de aciertos (puntaje positivo), fallos (puntaje negativo) y omisiones (sin penalización).

### 5. Reportes Analíticos y Cuadros de Mérito
*   **Servicio GeneradorReportesService**: Lógica analítica pura (cálculo al vuelo mediante agregaciones del ORM de Django) para obtener promedios, notas máximas y notas mínimas por examen y ciclo académico.
*   **Ranking de Mérito**: Renderizado de tablas jerárquicas ordenadas con insignias y badges visuales para destacar el desempeño y las posiciones generales, resaltando automáticamente la ubicación del alumno logueado.

---

##  Stack Tecnológico

*   **Backend**: Python (3.13+) & Django Framework (6.0.7+)
*   **Base de Datos**: PostgreSQL (Conector `psycopg2-binary`)
*   **Frontend**: HTML5 Semántico, Vanilla CSS3 (Aestethic Glassmorphism & Euler Blue Palette), JavaScript nativo (ES6+).
*   **Librerías Externas**:
    *   `html5-qrcode` (Captura y escaneo de video QR vía webcam)
    *   `qrcode.js` (Generación de código QR del lado del cliente)

---

##  Estructura de Módulos del Proyecto

El proyecto está diseñado bajo una arquitectura modular limpia en la raíz:

```text
├── sigae/                  # Directorio del proyecto Django (Settings, URLs raíz)
├── autenticacion/          # App de usuarios, roles, login/logout, perfiles y dashboards
├── academico/              # App de ciclos académicos, aulas, matrículas y asistencia QR
├── simulacros/             # App de banco de preguntas, exámenes y procesamiento de respuestas
├── reportes/               # App de generación de rankings de mérito y estadísticas agregadas
├── templates/              # Directorio común de plantillas HTML
├── static/                 # Recursos estáticos (Hojas de estilo CSS corporativas)
├── requirements.txt        # Declaración de dependencias del proyecto
└── .env                    # Configuración de variables de entorno y base de datos
```

---

##  Guía de Instalación y Configuración Rápida

Sigue estos pasos para desplegar el proyecto localmente:

### 1. Activar el Entorno Virtual
Abre una terminal en la raíz del proyecto y ejecuta:
```powershell
.venv\Scripts\activate
```

### 2. Instalar las Dependencias
Instala los paquetes declarados en el archivo de requerimientos:
```bash
pip install -r requirements.txt
```

### 3. Configurar la Base de Datos PostgreSQL
Asegúrate de que la base de datos `sigae_euler_db` esté creada en tu servidor PostgreSQL local y que el archivo `.env` en la raíz del proyecto cuente con las credenciales correctas:
```ini
DEBUG=True
SECRET_KEY=tu-clave-secreta-super-segura
DB_NAME=sigae_euler_db
DB_USER=postgres
DB_PASSWORD=76925540
DB_HOST=localhost
DB_PORT=5432
```

### 4. Compilar y Ejecutar las Migraciones
Impacta el esquema relacional de modelos sobre PostgreSQL:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Iniciar el Servidor de Desarrollo
Lanza el servidor local de Django:
```bash
python manage.py runserver
```

### 6. Acceso al Sistema
Abre tu navegador de preferencia e ingresa a la siguiente URL para iniciar sesión:
 **[http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)**
