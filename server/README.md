server/
├── migrations/
├── src/
│   └── server/
│       ├── __init__.py
│       ├── config.py # Application configuration
|       ├── extensions.py
|       ├── dependencies.py # Initialize services here
│       │
│       ├── routes/ # Receive HTTP requests, extract request data, validate request structure, call service, return http response
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── attendance.py # Might contain something like POST /api/scan, GET /api/attendance, GET /api/attendance/today
│       │   ├── students.py
│       │   ├── equipment.py
│       │   └── reports.py
│       │
│       ├── services/ # This is where the actual application behavior lives. **Services should be INDEPENDENT of Flask**
│       │   ├── __init__.py
│       │   ├── attendance.py # Process scan, determine if checking in or out, prevent invalid attendance operations, handle repeated scans, coordinate attendance records
│       │   ├── students.py # Register student, update student info, change student scan id, check if student already exists
│       │   ├── equipment.py
│       │   └── reports.py # Determine which records belong in a report, apply report filters, prepare attendance data for export
│       │
│       ├── repositories/ # Database access. The repository layer should not decide *whether* a student is allowed to check in
│       │   ├── __init__.py
│       │   ├── attendance.py # Handles attendance-related queries and persistence.
│       │   ├── students.py # Might provide operations like get_by_csu_id(), get_by_scan_id(), get_all(), create(), update(), delete()
│       │   └── equipment.py
│       │
│       ├── models/ # SQLAlchemy models. **Don't put business logic in SQLAlchemy models.**
│       │   ├── __init__.py
│       │   ├── student.py
│       │   ├── attendance.py
│       │   └── equipment.py
│       │
│       ├── forms/
│       │   ├── __init__.py
│       │   └── students.py
│       │
│       ├── utils/
│       │   ├── __init__.py
│       │   ├── dates.py
│       │   └── excel.py
│       │
│       ├── templates/
│       └── static/
│
└── tests/