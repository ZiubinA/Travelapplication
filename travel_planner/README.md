Note: '129884' is a confirmed, valid ID

# Travel Planner API
This is a RESTful API built with
FastAPI for managing travel projects and places to visit. 
SQLite
database
for storage.

## Tech Stack
Python 3.11
FastAPI
SQLA1chemy (SQLite)
Docker & Docker Compose

## Features Implemented
CRUD operations for Travel Projects and Places.
Business logic validation (max 10 places per project, duplicate prevention, delete restrictions).
Integration with a third-party API for validation.
Basic Authentication.
Dockerized environment for easy local setup.
Auto-generated OpenAPI/Swagger documentation.

## Prerequisites
Make sure you have [Docker] (https:// www.docker.com/) and Docker Compose installed on your hine.
Clone this repository and navigate to the project root folder.
Run the following command in your
terminal to build and start the application:
bash
docker-compose up --build

Open your browser and go to: http://localhost:8000/docs
Authentication: Click the "Authorize" button (padlock icon) at the top right of the page to log in.
name: admin
password: password123

Example Request: Creating a Project
When testing the POST /projects/ endpoint, you must use valid external_id values from the Art Institute of Chicago API. You can use the following valid JSON payload to easily test the creation of a project:

{
  "name": "chicago art tour",
  "description": "exploring the Art Institute",
  "start_date": "12.07.2026",
  "places": [
    {
      "external_id": "129884", 
      "notes": "Check out this"
    }
  ]
}

Update Project (PUT /projects/{project_id})
Enter 1 for project_id, paste this JSON, and click Execute:

{
  "name": "updated chicago tour",
  "description": "Trip extended"
}

Create Place (POST /projects/{project_id}/places/)
Enter 1 for project_id, paste this JSON, and click Execute:

{
  "external_id": "27992",
  "notes": "American Gothic painting"
}

Update Place / Mark Visited (PUT /projects/{project_id}/places/{place_id})
Enter 1 for project_id, 1 for place_id, paste this JSON, and click Execute:

{
  "notes": "Looked great in person!",
  "visited": true
}

Delete Project (DELETE /projects/{project_id})
Note: The API restricts deleting projects if any places are marked as visited. To test this, create a new project first, or set visited to false.
Open DELETE /projects/{project_id}
Enter the ID of a project with unvisited places.
Click Execute.