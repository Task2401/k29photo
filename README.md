# k29photo (Web Application / Flickr Clone)

![Language](https://img.shields.io/badge/language-Python%203-blue.svg)
![Framework](https://img.shields.io/badge/framework-Flask-green.svg)
![Database](https://img.shields.io/badge/database-PostgreSQL-blue.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

A modular full-stack web application designed for managing and sharing digital photographs. This project demonstrates relational database styling, server-side rendering, session management, and recommendation algorithms within a web framework environment.

## Overview
The application features a fully responsive photo-sharing ecosystem inspired by Flickr. Users can register profiles, upload imagery, organize items into dedicated albums, and globally categorize files using tags. The system incorporates social networking functions (likes and comments) alongside intelligent, data-driven systems that generate real-time user and photo recommendations based on mutual friends and shared tag metadata.

## Key Technical Features

### 1. Advanced Relational Database Design
The persistence layer aggregates data through an object-relational schema engineered in PostgreSQL:
* Binary Storage (BLOB): Photographs are processed and saved directly into the database using the BYTEA binary type, ensuring data portability, atomicity, and total independence from external file storage systems.
* Integrity Triggers: Database triggers prevent users from generating self-likes or self-comments, keeping data integrity intact directly at the engine level.
* Referential Integrity: Foreign keys enforce automatic cascades upon item removal, cleaning up correlated likes and comment history.

### 2. Algorithmic Recommendations
* Friend Recommendations: A recursive graph system maps relationships to identify mutual connections, recommending potential friends based on the highest count of overlapping connections.
* Photo Recommendations: An analytical engine scans current user habits to isolate the most frequently used tags, then cross-references external publications to surface highly relevant, targeted image discoveries.

### 3. Architecture & Security
* Core Stack: Built on a clean separation of concerns using Python 3 and the Flask micro-framework, completely eliminating custom client-side JavaScript dependencies by driving state via safe server-side Jinja2 processing.
* Access Control: Implements secure user authentication, hashing plain text passwords using the PBKDF2 encryption methodology via Werkzeug security primitives.

## Installation & Usage

### Prerequisites
* Python 3.8 or newer
* PostgreSQL Server 12 or newer
* pip (Python Package Installer)

### Database Setup
Log into your local PostgreSQL console or open pgAdmin to create the database:

```sql
CREATE DATABASE k29photo;
```

Initialize the database tables and restrictions by running the schema.sql script.

For Bash (Linux/macOS):

```bash
psql -U your_username -d k29photo -f src/sql/schema.sql
```

For Windows (Command Prompt/PowerShell):

```powershell
psql -U your_username -d k29photo -f src/sql/schema.sql
```

Seed the initialized tables with default image assets and test records:

For Bash (Linux/macOS):

```bash
python src/sql/inserts.py
```

For Windows (Command Prompt/PowerShell):

```powershell
python src/sql/inserts.py
```

## Configuration

Open the files src/app.py and src/sql/inserts.py to insert your database credentials (DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT) in the connection configuration section located at the top of each script.

### Virtual Environment Setup

For Bash (Linux/macOS):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For Windows (Command Prompt/PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running the Application

Launch the local application server while ensuring your environment remains active.

For Bash (Linux/macOS):

```bash
python src/app.py
```

For Windows (Command Prompt/PowerShell):

```powershell
python src/app.py
```

The application interface will instantly serve clients locally via the browser at: http://127.0.0.1:5000

## Future Work

Planned improvements for upcoming releases:
- Cloud Object Storage Migration: Transitioning from local binary bytea database tables to an automated cloud object file storage bucket structure to minimize database layout bloat.

- Asynchronous Handshakes: Enhancing friendship connections to support pending request logs and approval states rather than direct, instantaneous bindings.

## Author 

**Anastasios - Christos Kyrios** *Software Engineer*



