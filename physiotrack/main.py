import logging
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from fastapi import FastAPI, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel
import qrcode
import datetime

# Database setup
DATABASE_URL = "sqlite:///./test.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Logging setup
logging.basicConfig(level=logging.INFO)

# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # either 'doctor' or 'patient'

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User")

# Pydantic Models
class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # Define user role on creation

class UserOut(BaseModel):
    id: int
    username: str
    role: str

class ExerciseCreate(BaseModel):
    name: str

# Authentication
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# FastAPI setup
app = FastAPI()

@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate):
    db = SessionLocal()
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password, role=user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserOut)
def read_user(user_id: int):
    db = SessionLocal()
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.post("/exercises/", response_model=None)
def create_exercise(exercise: ExerciseCreate, user_id: int):
    db = SessionLocal()
    db_exercise = Exercise(**exercise.dict(), user_id=user_id)
    db.add(db_exercise)
    db.commit()
    return "Exercise added"

@app.get("/generate_qr/{data}")
def generate_qr(data: str):
    qr = qrcode.make(data)
    qr_path = f"qr_{data}.png"
    qr.save(qr_path)
    return {"qr_code_path": qr_path}

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)  # Create database tables on startup

@app.on_event("shutdown")
def shutdown_event():
    db = SessionLocal()
    db.close()
