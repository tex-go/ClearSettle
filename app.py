from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import pandas as pd
import io
import re

app = FastAPI(title="Lead Generator")

# ============================================================
# DATABASE
# ============================================================

engine = create_engine(
    "sqlite:///lead_generator.db",
    connect_args={"check_same_thread": False}
)

Session = sessionmaker(bind=engine)
Base = declarative_base()


class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True)

    seller_name = Column(String)
    phone = Column(String, index=True)

    business_name = Column(String)
    gst_number = Column(String)

    instagram_url = Column(String)
    website = Column(String)

    cluster = Column(String)

    address = Column(Text)

    duplicate_count = Column(Integer, default=1)

    lead_score = Column(Integer, default=0)

    status = Column(String, default="New")

    notes = Column(Text)


Base.metadata.create_all(engine)


# ============================================================
# HELPERS
# ============================================================

def clean_phone(value):
    value = re.sub(r"\D", "", str(value))

    if len(value) >= 10:
        return value[-10:]

    return value


def detect_cluster(address):

    address = str(address).lower()

    north = [
        "avinashi",
        "kaniyampoondi",
        "rakkiyapalayam",
        "thirumuruganpoondi"
    ]

    south = [
        "mangalam",
        "veerapandi",
        "muthanampalayam",
        "mudalipalayam"
    ]

    east = [
        "uthukuli",
        "perumanallur"
    ]

    west = [
        "palladam",
        "angeripalayam",
        "kuppandampalayam"
    ]

    if any(x in address for x in north):
        return "North"

    if any(x in address for x in south):
        return "South"

    if any(x in address for x in east):
        return "East"

    if any(x in address for x in west):
        return "West"

    return "Outside"


def calculate_score(seller):

    score = 0

    if seller.gst_number:
        score += 20

    if seller.website:
        score += 20

    if seller.instagram_url:
        score += 15

    if seller.business_name:
        score += 15

    return score


# ============================================================
# HOME
# ============================================================

@app.get("/", response_class=HTMLResponse)
def home(search: str = ""):

    db = Session()

    query = db.query(Seller)

    if search:
        query = query.filter(
            Seller.phone.contains(search)
        )

    sellers = query.all()

    rows = ""

    for s in sellers:

        rows += f"""
        <tr>
            <td>{s.id}</td>
            <td>{s.seller_name or ''}</td>
            <td>{s.phone}</td>
            <td>{s.cluster}</td>
            <td>{s.status}</td>
            <td>
                <a href='/seller/{s.id}'>Edit</a>
            </td>
        </tr>
        """

    return f"""
    <h2>Lead Generator</h2>

    <hr>

    <form action="/upload" method="post"
    enctype="multipart/form-data">

        <input type="file" name="file">

        <button>Upload Excel</button>

    </form>

    <br>

    <form>

        <input
            name="search"
            placeholder="Search Phone"
        >

        <button>Search</button>

    </form>

    <br>

    <a href="/export">
        Export Excel
    </a>

    <hr>

    <table border="1" cellpadding="5">

        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Phone</th>
            <th>Cluster</th>
            <th>Status</th>
            <th></th>
        </tr>

        {rows}

    </table>
    """


# ============================================================
# IMPORT EXCEL
# ============================================================

@app.post("/upload")
async def upload(file: UploadFile = File(...)):

    df = pd.read_excel(file.file)

    cols = list(df.columns)

    name_col = cols[0]
    address_col = cols[1]
    phone_col = cols[2]

    db = Session()

    phone_count = {}

    for _, row in df.iterrows():

        phone = clean_phone(row[phone_col])

        phone_count[phone] = (
            phone_count.get(phone, 0) + 1
        )

    for _, row in df.iterrows():

        phone = clean_phone(row[phone_col])

        existing = (
            db.query(Seller)
            .filter(Seller.phone == phone)
            .first()
        )

        if existing:
            continue

        address = str(row[address_col])

        db.add(
            Seller(
                seller_name=str(row[name_col]),
                phone=phone,
                address=address,
                duplicate_count=phone_count.get(phone, 1),
                cluster=detect_cluster(address)
            )
        )

    db.commit()

    return RedirectResponse("/", status_code=302)


# ============================================================
# SELLER DETAILS
# ============================================================

@app.get("/seller/{seller_id}", response_class=HTMLResponse)
def seller_page(seller_id: int):

    db = Session()

    seller = (
        db.query(Seller)
        .filter(Seller.id == seller_id)
        .first()
    )

    return f"""
    <h2>Seller #{seller.id}</h2>

    <form action="/seller/{seller.id}"
          method="post">

    Business Name

    <br>

    <input
        name="business_name"
        value="{seller.business_name or ''}"
    >

    <br><br>

    GST Number

    <br>

    <input
        name="gst_number"
        value="{seller.gst_number or ''}"
    >

    <br><br>

    Instagram

    <br>

    <input
        name="instagram_url"
        value="{seller.instagram_url or ''}"
    >

    <br><br>

    Website

    <br>

    <input
        name="website"
        value="{seller.website or ''}"
    >

    <br><br>

    Status

    <br>

    <input
        name="status"
        value="{seller.status or ''}"
    >

    <br><br>

    Notes

    <br>

    <textarea
        name="notes"
        rows="6"
        cols="50"
    >{seller.notes or ''}</textarea>

    <br><br>

    <button>Save</button>

    </form>

    <hr>

    <a href="/">Back</a>
    """


@app.post("/seller/{seller_id}")
def update_seller(
    seller_id: int,
    business_name: str = Form(""),
    gst_number: str = Form(""),
    instagram_url: str = Form(""),
    website: str = Form(""),
    status: str = Form(""),
    notes: str = Form("")
):

    db = Session()

    seller = (
        db.query(Seller)
        .filter(Seller.id == seller_id)
        .first()
    )

    seller.business_name = business_name
    seller.gst_number = gst_number
    seller.instagram_url = instagram_url
    seller.website = website
    seller.status = status
    seller.notes = notes

    seller.lead_score = calculate_score(seller)

    db.commit()

    return RedirectResponse(
        f"/seller/{seller_id}",
        status_code=302
    )


# ============================================================
# EXPORT
# ============================================================

@app.get("/export")
def export_data():

    db = Session()

    sellers = db.query(Seller).all()

    data = []

    for s in sellers:

        data.append({
            "ID": s.id,
            "Seller Name": s.seller_name,
            "Phone": s.phone,
            "Business Name": s.business_name,
            "GST": s.gst_number,
            "Instagram": s.instagram_url,
            "Website": s.website,
            "Cluster": s.cluster,
            "Duplicate Count": s.duplicate_count,
            "Lead Score": s.lead_score,
            "Status": s.status,
            "Notes": s.notes
        })

    df = pd.DataFrame(data)

    output = io.BytesIO()

    df.to_excel(
        output,
        index=False
    )

    output.seek(0)

    return StreamingResponse(
        output,
        media_type=
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition":
            "attachment; filename=leads.xlsx"
        }
    )