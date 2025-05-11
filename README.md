# Patient Monitoring System

A web application to display hospitalized patients who have been admitted for more than 48 hours without recent lab tests.

---

## Architecture

```
[S3 CSV (out of scope)]
     ↓ (pre-loaded)
  PostgreSQL DB
     ↑         ↑
 FastAPI     React
   API       Frontend
```

---

## Setup Instructions

### 1. Prerequisites

- Docker + Docker Compose
- Node.js (if running frontend manually)

### 2. Clone and Start

```bash
git clone https://github.com/nemoshlag/data-integrator.git
cd data-integrator
docker-compose up --build
```

- Backend: [http://localhost:8000/patients](http://localhost:8000/patients)
- Frontend: [http://localhost:3000](http://localhost:3000)

---

## Database Schema

### `patients`
| Field              | Type      |
|-------------------|-----------|
| id                | int (PK)  |
| first_name        | string    |
| last_name         | string    |
| date_of_birth     | datetime  |
| primary_physician | string    |
| insurance_provider| string    |
| blood_type        | string    |
| allergies         | string    |

### `admissions`
| Field                     | Type      |
|--------------------------|-----------|
| id                       | int (PK)  |
| patient_id               | int (FK)  |
| hospitalization_case_number| int      |
| admission_time           | datetime  |
| release_time            | datetime? |
| department              | string    |
| room_number             | string    |

### `lab_tests`
| Field              | Type      |
|-------------------|-----------|
| id                | int (PK)  |
| patient_id        | int (FK)  |
| test_name         | string    |
| order_time        | datetime  |
| ordering_physician| string    |

### `lab_results`
| Field               | Type      |
|--------------------|-----------|
| id                 | int (PK)  |
| test_id            | int (FK)  |
| result_value       | float     |
| result_unit        | string    |
| reference_range    | string    |
| result_status      | string    |
| performed_time     | datetime  |
| reviewing_physician| string    |

---

## Structure

```
.
├── backend
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── db.py
│   └── requirements.txt
├── frontend
│   ├── public
│   │   └── index.html
│   ├── src
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```