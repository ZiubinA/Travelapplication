from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import List, Optional
import requests
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
import secrets
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "password123")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
SQLALCHEMY_DATABASE_URL = "sqlite:///./travel_app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBProject(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    places = relationship("DBPlace", back_populates="project", cascade="all, delete-orphan")

class DBPlace(Base):
    __tablename__ = "places"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)
    notes = Column(String, nullable=True)
    visited = Column(Boolean, default=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("DBProject", back_populates="places")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PlaceCreate(BaseModel):
    external_id: str
    notes: Optional[str] = None

class PlaceUpdate(BaseModel):
    notes: Optional[str] = None
    visited: Optional[bool] = None

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    places: Optional[List[PlaceCreate]] = []

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None

def validate_place_exists(external_id: str):
    """Checks the Art Institute API to see if the place (artwork) exists."""
    url = f"https://api.artic.edu/api/v1/artworks/{external_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Place with ID {external_id} not found in external API.")

def check_project_completed(project: DBProject):
    """Returns True if all places are visited and there is at least 1 place."""
    if not project.places:
        return False
    return all(place.visited for place in project.places)

app = FastAPI(title="Travel Planner API")

@app.post("/projects/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    if len(project.places) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 places allowed.")
    
    unique_ids = set()
    for p in project.places:
        if p.external_id in unique_ids:
            raise HTTPException(status_code=400, detail="Duplicate places not allowed.")
        unique_ids.add(p.external_id)
        validate_place_exists(p.external_id)

    db_project = DBProject(name=project.name, description=project.description, start_date=project.start_date)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    for p in project.places:
        db_place = DBPlace(external_id=p.external_id, notes=p.notes, project_id=db_project.id)
        db.add(db_place)
    db.commit()
    
    return {"message": "Project created", "id": db_project.id}

@app.get("/projects/")
def list_projects(db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    projects = db.query(DBProject).all()
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "name": p.name,
            "completed": check_project_completed(p)
        })
    return result

@app.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    project = db.query(DBProject).filter(DBProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    places_data = [{"id": p.id, "external_id": p.external_id, "visited": p.visited, "notes": p.notes} for p in project.places]
    return {"id": project.id, "name": project.name, "completed": check_project_completed(project), "places": places_data}

@app.put("/projects/{project_id}")
def update_project(project_id: int, update_data: ProjectUpdate, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    project = db.query(DBProject).filter(DBProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if update_data.name: project.name = update_data.name
    if update_data.description: project.description = update_data.description
    if update_data.start_date: project.start_date = update_data.start_date
    db.commit()
    return {"message": "Project updated"}

@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    project = db.query(DBProject).filter(DBProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if any(place.visited for place in project.places):
        raise HTTPException(status_code=400, detail="Cannot delete project: some places are already visited.")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}

@app.post("/projects/{project_id}/places/")
def add_place_to_project(project_id: int, place: PlaceCreate, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    project = db.query(DBProject).filter(DBProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if len(project.places) >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 places per project reached.")
    if any(p.external_id == place.external_id for p in project.places):
        raise HTTPException(status_code=400, detail="Place already exists in this project.")
    
    validate_place_exists(place.external_id)
    
    db_place = DBPlace(external_id=place.external_id, notes=place.notes, project_id=project.id)
    db.add(db_place)
    db.commit()
    return {"message": "Place added"}

@app.put("/projects/{project_id}/places/{place_id}")
def update_place(project_id: int, place_id: int, place_data: PlaceUpdate, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    place = db.query(DBPlace).filter(DBPlace.id == place_id, DBPlace.project_id == project_id).first()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found in this project")
    if place_data.notes is not None:
        place.notes = place_data.notes
    if place_data.visited is not None:
        place.visited = place_data.visited
        
    db.commit()
    return {"message": "Place updated"}