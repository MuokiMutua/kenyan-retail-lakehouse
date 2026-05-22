#  Real-Time Retail Lakehouse & Command Center
<img width="1909" height="1028" alt="image" src="https://github.com/user-attachments/assets/ec456ae9-41a9-4d29-af84-8741d0a1cbb5" />


![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=Streamlit&logoColor=white)
![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?style=flat&logo=apachekafka&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-4EA94B?style=flat&logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

An end-to-end, real-time data engineering pipeline and streaming dashboard built to simulate, ingest, and visualize Point-of-Sale (POS) telemetry for a major retail chain.

This project demonstrates a modern **Data Lakehouse** architecture, combining the rigid, relational structure of PostgreSQL (for dimension and target data) with the flexible, high-volume document storage of MongoDB (for immutable raw audit logs).

##  Architecture Overview

1. **POS Simulator (`kenyan_pos_simulator.py`):** Generates synthetic, highly localized retail transactions in real-time. It handles deep-copying memory safety, idempotent SQL upserts, and graceful shutdown lifecycles.
2. **Streaming Layer (Apache Kafka):** Acts as the central nervous system, buffering high-throughput transactions.
3. **Data Storage (Postgres & Mongo):**
    * **PostgreSQL:** Stores the relational product catalog, sector dimensions, and daily business targets.
    * **MongoDB:** Serves as the NoSQL data lake, storing the unstructured JSON receipts as an immutable audit log.
4. **Command Center (`dashboard.py`):** A Streamlit application using Pandas and Plotly to execute federated queries across both databases, joining relational targets with streaming NoSQL actuals in real-time.

##  Key Features

* **Federated Queries:** Merges data from SQL and NoSQL sources on the fly using Pandas.
* **Resilient Database Connections:** Implements self-healing connection logic to automatically recover from dropped database connections or container restarts.
* **Live Streaming UI:** Utilizes `streamlit-autorefresh` for a flicker-free, continuously updating executive dashboard.
* **Agentic Decision Log:** Simulates an AI orchestrator monitoring thresholds and triggering automated alerts (e.g., flash sales, restock alerts).
* **Containerized Infrastructure:** Fully orchestrated via `docker-compose` with built-in UI tools (pgAdmin, Mongo Express, AKHQ).

##  Prerequisites

* [Docker](https://www.docker.com/) & Docker Compose
* [Python 3.10+](https://www.python.org/)
* [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)

##  Setup & Installation

### 1. Start the Infrastructure
Spin up the Kafka, PostgreSQL, and MongoDB containers. The database schema and initial targets will be automatically seeded via `init.sql`.
```bash
# Start the containers
docker-compose up -d

# (Optional) If you need to reset the databases to a clean state:
docker-compose down -v && docker-compose up -d
