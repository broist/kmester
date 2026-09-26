import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]
SECRET = os.environ["APP_SECRET"]
USERNAME = os.environ["APP_USERNAME"]
PASSWORD = os.environ["APP_PASSWORD"]
OFF_AGENT = os.getenv("OFF_USER_AGENT", "KaloriaMester/1.0 (self-hosted)")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine)
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class Base(DeclarativeBase): pass
class Food(Base):
    __tablename__ = "foods"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250))
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    serving_size_g: Mapped[Decimal | None] = mapped_column(Numeric(10,2), nullable=True)
    kcal: Mapped[Decimal] = mapped_column(Numeric(10,3), default=0)
    protein: Mapped[Decimal] = mapped_column(Numeric(10,3), default=0)
    carbs: Mapped[Decimal] = mapped_column(Numeric(10,3), default=0)
    fat: Mapped[Decimal] = mapped_column(Numeric(10,3), default=0)
    fiber: Mapped[Decimal | None] = mapped_column(Numeric(10,3), nullable=True)
    sugar: Mapped[Decimal | None] = mapped_column(Numeric(10,3), nullable=True)
    saturated_fat: Mapped[Decimal | None] = mapped_column(Numeric(10,3), nullable=True)
    salt: Mapped[Decimal | None] = mapped_column(Numeric(10,3), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    confidence: Mapped[str] = mapped_column(String(32), default="precise")
    verified_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class MealEntry(Base):
    __tablename__ = "meal_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id"))
    log_date: Mapped[date] = mapped_column(Date, index=True)
    meal: Mapped[str] = mapped_column(String(20))
    grams: Mapped[Decimal] = mapped_column(Numeric(10,2))
    food: Mapped[Food] = relationship()

class Profile(Base):
    """Single-user profile and a deliberately transparent calorie estimate."""
    __tablename__ = "profile"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    sex: Mapped[str] = mapped_column(String(16), default="other")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(6,2), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6,2), nullable=True)
    activity: Mapped[str] = mapped_column(String(24), default="sedentary")
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6,2), nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weekly_loss_kg: Mapped[Decimal] = mapped_column(Numeric(4,2), default=Decimal("0.50"))
    calorie_override: Mapped[Decimal | None] = mapped_column(Numeric(8,1), nullable=True)

class FoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=250); brand: str | None = None; barcode: str | None = None
    serving_size_g: Decimal | None = Field(None, ge=0); kcal: Decimal = Field(ge=0); protein: Decimal = Field(ge=0); carbs: Decimal = Field(ge=0); fat: Decimal = Field(ge=0)
    fiber: Decimal | None = Field(None, ge=0); sugar: Decimal | None = Field(None, ge=0); saturated_fat: Decimal | None = Field(None, ge=0); salt: Decimal | None = Field(None, ge=0)
    source: Literal["open_food_facts", "manual", "recipe", "estimated"] = "manual"; confidence: Literal["precise", "incomplete", "estimated"] = "precise"; verified_by_user: bool = False; notes: str | None = None
class EntryIn(BaseModel): food_id: int; log_date: date; meal: Literal["breakfast","lunch","dinner","snack"]; grams: Decimal = Field(gt=0)
class Login(BaseModel): username: str; password: str
class ProfileIn(BaseModel):
    sex: Literal["female", "male", "other"] = "other"
    birth_date: date | None = None
    height_cm: Decimal | None = Field(None, ge=80, le=250)
    weight_kg: Decimal | None = Field(None, ge=25, le=400)
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"] = "sedentary"
    target_weight_kg: Decimal | None = Field(None, ge=25, le=400)
    target_date: date | None = None
    weekly_loss_kg: Decimal = Field(Decimal("0.50"), ge=0, le=2)
    calorie_override: Decimal | None = Field(None, ge=800, le=8000)

def db():
    with SessionLocal() as s: yield s
def user(token: HTTPAuthorizationCredentials = Depends(security)):
    try: return jwt.decode(token.credentials, SECRET, algorithms=["HS256"])
    except jwt.PyJWTError: raise HTTPException(401, "Érvénytelen munkamenet")
def serialize_food(f: Food):
    return {c.name: (float(getattr(f,c.name)) if isinstance(getattr(f,c.name), Decimal) else getattr(f,c.name)) for c in Food.__table__.columns}
def validate_barcode(code: str):
    code = ''.join(c for c in code if c.isdigit())
    if len(code) not in (6, 8, 12, 13): raise HTTPException(422, "EAN-8, EAN-13, UPC-A vagy UPC-E vonalkód szükséges")
    return code
def calculate_profile(p: Profile):
    result = {"configured": False, "bmr": None, "maintenance": None, "daily_target": None, "weekly_loss_kg": float(p.weekly_loss_kg), "deadline_weekly_loss_kg": None, "warning": None}
    if not (p.birth_date and p.height_cm and p.weight_kg): return result
    age = (date.today() - p.birth_date).days / 365.2425
    sex_constant = 5 if p.sex == "male" else -161 if p.sex == "female" else -78
    bmr = 10 * float(p.weight_kg) + 6.25 * float(p.height_cm) - 5 * age + sex_constant
    maintenance = bmr * {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}[p.activity]
    weekly = float(p.weekly_loss_kg)
    if p.target_weight_kg is not None and p.target_date and p.target_date > date.today() and float(p.target_weight_kg) < float(p.weight_kg):
        weekly = (float(p.weight_kg) - float(p.target_weight_kg)) * 7 / (p.target_date - date.today()).days
        result["deadline_weekly_loss_kg"] = round(weekly, 2)
    target = float(p.calorie_override) if p.calorie_override is not None else maintenance - weekly * 1100
    minimum = 1500 if p.sex == "male" else 1200
    if p.calorie_override is None and target < minimum:
        target = minimum
        result["warning"] = "A célidőpont túl nagy megszorítást igényelne, ezért a becsült napi cél biztonsági alsó korlátot használ."
    elif weekly > 1:
        result["warning"] = "Az 1 kg/hét feletti cél általában nem javasolt orvosi felügyelet nélkül."
    result.update(configured=True, bmr=round(bmr), maintenance=round(maintenance), daily_target=round(target), weekly_loss_kg=round(weekly, 2))
    return result

app = FastAPI(title="KalóriaMester")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("APP_URL", "http://localhost:5173")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
@app.on_event("startup")
def start(): Base.metadata.create_all(engine)
@app.get("/health")
def health(): return {"ok": True}
@app.post("/api/auth/login")
def login(data: Login):
    if data.username != USERNAME or data.password != PASSWORD: raise HTTPException(401, "Hibás felhasználónév vagy jelszó")
    return {"token": jwt.encode({"sub": USERNAME, "exp": datetime.now(timezone.utc)+timedelta(days=30)}, SECRET, algorithm="HS256")}
@app.get("/api/profile")
def get_profile(s: Session = Depends(db), _: dict = Depends(user)):
    p = s.get(Profile, 1) or Profile(id=1)
    if s.get(Profile, 1) is None: s.add(p); s.commit(); s.refresh(p)
    return {"profile": {c.name: (float(getattr(p,c.name)) if isinstance(getattr(p,c.name), Decimal) else getattr(p,c.name)) for c in Profile.__table__.columns}, "calculation": calculate_profile(p)}
@app.put("/api/profile")
def update_profile(data: ProfileIn, s: Session = Depends(db), _: dict = Depends(user)):
    p = s.get(Profile, 1) or Profile(id=1)
    for k,v in data.model_dump().items(): setattr(p,k,v)
    s.add(p); s.commit(); s.refresh(p)
    return {"profile": {c.name: (float(getattr(p,c.name)) if isinstance(getattr(p,c.name), Decimal) else getattr(p,c.name)) for c in Profile.__table__.columns}, "calculation": calculate_profile(p)}
@app.get("/api/foods")
def foods(q: str = "", s: Session = Depends(db), _: dict = Depends(user)):
    return [serialize_food(x) for x in s.scalars(select(Food).where(Food.name.ilike(f"%{q}%")).order_by(Food.updated_at.desc()).limit(40))]
@app.post("/api/foods")
def add_food(data: FoodIn, s: Session = Depends(db), _: dict = Depends(user)):
    f=Food(**data.model_dump()); s.add(f); s.commit(); s.refresh(f); return serialize_food(f)
@app.put("/api/foods/{food_id}")
def edit_food(food_id:int,data:FoodIn,s:Session=Depends(db),_:dict=Depends(user)):
    f=s.get(Food,food_id)
    if not f: raise HTTPException(404,"Nincs ilyen étel")
    for k,v in data.model_dump().items(): setattr(f,k,v)
    f.verified_by_user=True; s.commit(); s.refresh(f); return serialize_food(f)
@app.get("/api/barcode/{barcode}")
async def barcode(barcode:str,s:Session=Depends(db),_:dict=Depends(user)):
    barcode=validate_barcode(barcode); local=s.scalar(select(Food).where(Food.barcode==barcode))
    if local: return {"found":True,"cached":True,"food":serialize_food(local)}
    fields="code,product_name,brands,serving_size,product_quantity,nutriments"
    url=f"https://world.openfoodfacts.org/api/v3/product/{barcode}.json"
    try:
      async with httpx.AsyncClient(timeout=12) as client: r=await client.get(url,params={"fields":fields},headers={"User-Agent":OFF_AGENT}); r.raise_for_status(); payload=r.json()
    except httpx.HTTPError: raise HTTPException(503,"Az Open Food Facts most nem érhető el")
    if not payload.get("status"): return {"found":False,"barcode":barcode}
    p=payload.get("product",{}); n=p.get("nutriments",{}); required=["energy-kcal_100g","proteins_100g","carbohydrates_100g","fat_100g"]
    incomplete=any(n.get(x) is None for x in required)
    f=Food(name=p.get("product_name") or "Névtelen termék",brand=p.get("brands"),barcode=p.get("code",barcode),serving_size_g=p.get("product_quantity"),kcal=n.get("energy-kcal_100g") or 0,protein=n.get("proteins_100g") or 0,carbs=n.get("carbohydrates_100g") or 0,fat=n.get("fat_100g") or 0,fiber=n.get("fiber_100g"),sugar=n.get("sugars_100g"),saturated_fat=n.get("saturated-fat_100g"),salt=n.get("salt_100g"),source="open_food_facts",confidence="incomplete" if incomplete else "precise",imported_at=datetime.now(timezone.utc))
    s.add(f); s.commit(); s.refresh(f); return {"found":True,"cached":False,"food":serialize_food(f)}
@app.post("/api/entries")
def add_entry(data:EntryIn,s:Session=Depends(db),_:dict=Depends(user)):
    if not s.get(Food,data.food_id): raise HTTPException(404,"Nincs ilyen étel")
    e=MealEntry(**data.model_dump());s.add(e);s.commit();return {"id":e.id}
@app.delete("/api/entries/{entry_id}")
def delete_entry(entry_id:int,s:Session=Depends(db),_:dict=Depends(user)):
    e=s.get(MealEntry,entry_id)
    if not e: raise HTTPException(404,"Nincs ilyen bejegyzés")
    s.delete(e);s.commit();return {"ok":True}
@app.get("/api/day/{log_date}")
def day(log_date:date,s:Session=Depends(db),_:dict=Depends(user)):
    entries=s.scalars(select(MealEntry).where(MealEntry.log_date==log_date)).all(); result=[]; totals={k:0.0 for k in ["kcal","protein","carbs","fat","fiber","sugar","saturated_fat","salt"]}
    for e in entries:
      f=serialize_food(e.food); factor=float(e.grams)/100; nutrients={k:round((f.get(k) or 0)*factor,2) for k in totals};
      for k,v in nutrients.items(): totals[k]+=v
      result.append({"id":e.id,"meal":e.meal,"grams":float(e.grams),"food":f,"nutrients":nutrients})
    return {"entries":result,"totals":{k:round(v,1) for k,v in totals.items()}}
@app.get("/api/export")
def export(s:Session=Depends(db),_:dict=Depends(user)):
    return {"exported_at":datetime.now(timezone.utc).isoformat(),"foods":[serialize_food(f) for f in s.scalars(select(Food))],"entries":[{"id":e.id,"food_id":e.food_id,"date":e.log_date.isoformat(),"meal":e.meal,"grams":float(e.grams)} for e in s.scalars(select(MealEntry))]}
