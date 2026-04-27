from fastapi import FastAPI, Depends, HTTPException, Request
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

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AEGIS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://divine-generosity-production-652a.up.railway.app")

# ── ESQUEMAS ──────────────────────────────────────────
class UserRegister(BaseModel):
    name: str
    last_name: str = ""
    email: str
    company: str = ""
    password: str

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
        plan="Starter"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "message": f"Usuario {data.name} creado correctamente",
        "name": data.name,
        "email": data.email,
        "plan": "Starter"
    }

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

# PAGO CON STRIPE
@app.post("/create-checkout-session")
def create_checkout_session(data: CheckoutForm, db: Session = Depends(get_db)):
    # Precios en centavos MXN
    prices = {
        "Starter": 4900,
        "Professional": 14900,
        "Enterprise": 49900
    }
    unit_amount = prices.get(data.plan, data.amount * 100)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "mxn",
                    "product_data": {
                        "name": f"AEGIS {data.plan}",
                        "description": f"Plan {data.plan} — Ciberseguridad AEGIS"
                    },
                    "unit_amount": unit_amount,
                    "recurring": {"interval": "month"}
                },
                "quantity": 1
            }],
            mode="subscription",
            customer_email=data.email,
            success_url=f"{FRONTEND_URL}?pago=exitoso&plan={data.plan}",
            cancel_url=f"{FRONTEND_URL}?pago=cancelado"
        )

        # Guardar pago pendiente en la BD
        payment = Payment(
            user_email=data.email,
            plan=data.plan,
            amount=unit_amount,
            status="pending",
            stripe_id=session.id
        )
        db.add(payment)
        db.commit()

        return {"url": session.url}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# WEBHOOK DE STRIPE (para confirmar pagos exitosos)
@app.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Webhook inválido")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment = db.query(Payment).filter(Payment.stripe_id == session["id"]).first()
        if payment:
            payment.status = "completed"
            db.commit()

    return {"status": "ok"}
