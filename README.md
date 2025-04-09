# Exam Manager API

Exam Manager API is a Django-based application for managing exams, questions, choices, participants, and answers. It provides a RESTful API built with Django Ninja and supports features like authentication, role-based access control, and asynchronous tasks using Celery.

## Features

- **User Management**: Create, update, delete, and list users with roles (`ADMIN` or `PARTICIPANT`).
- **Exam Management**: Create, update, delete, and list exams.
- **Question Management**: Manage questions for exams, including multiple-choice questions.
- **Choice Management**: Manage choices for questions.
- **Participant Management**: Register participants for exams and manage their data.
- **Answer Management**: Submit and edit answers for participants.
- **Automatic Grading**: Asynchronous grading of answers using Celery.
- **Ranking**: Automatic calculation and retrieval of rankings for participants in exams.
- **JWT Authentication**: Secure authentication using JSON Web Tokens (JWT).
- **Pagination and Filtering**: Support for pagination and filtering in list endpoints.
- **API Documentation**: Auto-generated API documentation available at `/api/docs`.

## Requirements

- Python 3.10 or higher
- Django 5.1 or higher
- Django Ninja 1.3 or higher
- PostgreSQL
- Redis (for Celery)
- Docker and Docker Compose (optional, for containerized setup)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/exam-manager-api.git
cd exam-manager-api/controller
```
### 2. Set Up a Virtual Environment

```python   
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 3. Install Dependencies

```python   
pip install -r requirements.txt
```
### 4. Configure the Database


Update the database settings in `core/settings.py` to match your PostgreSQL configuration.

### 5. Apply Migrations

```python   
python manage.py migrate
```
### 6. Create a Superuser
```python   
python manage.py createsuperuser
```
### 7. Run the Development Server
```python   
python manage.py runserver
```
The API will be available at `http://localhost:8000`.

## Running with Docker

### 1. Build and Start the Containers

```docker   
docker-compose up --build
```
### 2. Access the API

The API will be available at `http://localhost:8000`.

## API Documentation

The API documentation is auto-generated and available at:
```
http://localhost:8000/api/docs
```
## Asynchronous Tasks

The project uses Celery for asynchronous tasks like grading answers and calculating rankings. To start the Celery worker:
```python
celery -A exam_manager worker --loglevel=info
```

## Running Tests
To run the test suite:

```python   
python manage.py test
```
## Project Structure
```
controller/
├── core/               # Core Django project files
├── exams/              # Exam-related models, views, and APIs
├── users/              # User-related models, views, and APIs
├── [docker-compose.yml]  # Docker Compose configuration
└── [manage.py]           # Django management script
```