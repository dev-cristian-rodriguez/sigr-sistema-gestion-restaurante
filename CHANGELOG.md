# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo. El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-09

Línea base del proyecto.

### Agregado
- Estructura inicial del proyecto, configuración, base de datos SQLite y licencia MIT.
- Módulo de autenticación: registro de clientes, login con token firmado y expirable, y control de acceso por roles (`cliente`, `mesero`, `admin`).
- Módulo de menú digital: CRUD de categorías y platos con validaciones y eliminación lógica.
- Módulo de pedidos: pedidos por mesa con total calculado, máquina de estados e historial de cambios.
- Módulo de reservas por fecha y hora con validación de disponibilidad y de anticipación mínima.
- Módulo de caja y reportes: apertura, cobros por método de pago, cierre con arqueo y reporte diario de ventas con exportación a CSV.
- Pipeline de integración continua con GitHub Actions (instalación, pruebas y umbral de cobertura del 80 %).
- 61 pruebas automatizadas (unitarias, de integración y un flujo extremo a extremo) con 96 % de cobertura.
- README con instrucciones de instalación y ejecución.
