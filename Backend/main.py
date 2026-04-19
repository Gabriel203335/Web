from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import bcrypt
import stripe

from database import engine, get_db, Base
from models import User, Payment, Contact

load_dotenv()

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AEGIS API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# ── ESQUEMAS ──────────────────────────────────────────
class UserRegister(BaseModel):
    name: str
    last_name: str = ""
    email: str
    company: str = ""
    password: str
    plan: str = "Starter"

class UserLogin(BaseModel):
    email: str
    password: str

class ContactForm(BaseModel):
    name: str
    email: str
    company: str = ""
    service: str = ""
    message: str = ""

class CheckoutForm(BaseModel):
    email: str
    plan: str
    amount: int

# ── RUTAS ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "AEGIS API funcionando ✅"}

# REGISTRO
@app.post("/register")
def register(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    hashed = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = User(
        name=data.name,
        last_name=data.last_name,
        email=data.email,
        company=data.company,
        password=hashed,
        plan=data.plan
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": f"Usuario {data.name} creado correctamente"}

# LOGIN
@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not bcrypt.checkpw(data.password.encode('utf-8'), user.password.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return {
        "message": f"Bienvenido {user.name}",
        "name": user.name,
        "email": user.email,
        "plan": user.plan
    }

# CONTACTO
@app.post("/contact")
def contact(data: ContactForm, db: Session = Depends(get_db)):
    entry = Contact(
        name=data.name,
        email=data.email,
        company=data.company,
        service=data.service,
        message=data.message
    )
    db.add(entry)
    db.commit()
    return {"message": "Mensaje recibido correctamente"}

# PAGO
@app.post("/checkout")
def checkout(data: CheckoutForm, db: Session = Depends(get_db)):
    payment = Payment(
        user_email=data.email,
        plan=data.plan,
        amount=data.amount,
        status="completed"
    )
    db.add(payment)
    db.commit()
    return {"message": f"Pago del plan {data.plan} registrado correctamente"}
