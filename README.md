# SIGR: Sistema Integral de Gestión de Restaurante

API REST para gestionar las operaciones de un restaurante con tres tipos de usuario (cliente, mesero y administrador). Esta versión (`v1.0.0`) es la **línea base** del proyecto, desarrollada para el taller de Gestión del software de la Universidad Tecnológica del Oriente.

## Funcionalidades de la línea base

| Módulo | Qué incluye |
|---|---|
| Autenticación | Registro de clientes, login con token firmado y expirable, roles `cliente`, `mesero` y `admin`, contraseñas con hash |
| Menú digital | CRUD de categorías y platos; lectura pública, escritura solo de `admin`; eliminación lógica de platos |
| Pedidos | Pedidos por mesa con varios platos, total calculado, estados `recibido → en_preparacion → listo → entregado → pagado` e historial de cada cambio |
| Reservas | Crear, consultar y cancelar reservas por mesa, fecha y hora (90 minutos, 1 hora de anticipación, sin solapamientos) |
| Caja y reportes | Apertura de caja, cobros por método de pago, cierre con arqueo y reporte diario de ventas con exportación a CSV |

Fuera del alcance de esta versión: pasarela de pagos en línea, facturación electrónica, aplicación móvil, inventario, notificaciones en tiempo real (el estado de un pedido se consulta por la API) y modificación de reservas.

## Requisitos

- Python 3.10 o superior
- Git

## Instalación

```bash
git clone https://github.com/dev-cristian-rodriguez/sigr-sistema-gestion-restaurante.git
cd sigr-sistema-gestion-restaurante
python3 -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Para trabajar exactamente sobre la línea base: `git checkout v1.0.0`.

## Ejecución

```bash
export SECRET_KEY="una-clave-larga-y-secreta"
python run.py                      # http://127.0.0.1:5000
curl http://127.0.0.1:5000/health
```

Variables de entorno: `SECRET_KEY` (firma de tokens) y `DATABASE` (ruta del archivo SQLite, por defecto `sigr.db`). La primera cuenta de administrador debe crearse directamente en la base de datos; luego el administrador crea al resto con `POST /auth/users`.

## Endpoints principales

| Método y ruta | Rol | Descripción |
|---|---|---|
| `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | público / autenticado | Registro de clientes, login y perfil |
| `POST /auth/users` | admin | Crear cuentas internas |
| `GET /menu/categories`, `GET /menu/dishes` | público | Consultar el menú |
| `POST/PUT/DELETE /menu/categories`, `/menu/dishes` | admin | Administrar el menú |
| `POST /orders`, `GET /orders`, `PATCH /orders/<id>/status` | mesero, admin | Pedidos y cambios de estado |
| `GET /orders/<id>` | autenticado | Detalle (el cliente solo ve los suyos) |
| `POST /reservations`, `GET /reservations`, `DELETE /reservations/<id>` | autenticado | Reservas |
| `POST /cashier/open`, `/cashier/payments`, `/cashier/close` | mesero, admin | Caja |
| `GET /reports/daily?date=AAAA-MM-DD&format=csv` | admin | Reporte diario de ventas |

## Pruebas

```bash
pytest                                      # 61 pruebas
pytest --cov=app --cov-report=term-missing  # con cobertura (96 % en la línea base)
```

## Flujo de trabajo y versionado

- Rama estable: `main`. Versionado semántico (`MAJOR.MINOR.PATCH`) y mensajes de commit con [Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/).
- Todo cambio posterior a la línea base se registra como issue en GitHub y se integra por Pull Request.
- El historial de cambios está en [CHANGELOG.md](CHANGELOG.md).

## Licencia

MIT. Ver [LICENSE.txt](LICENSE.txt).

## Autor

Cristian Estiven Rodriguez Benitez, Ingeniería de Software, Universidad Tecnológica del Oriente.
