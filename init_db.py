import json
import random
import os
from sqlalchemy import create_engine, Column, String, Integer, Text, Boolean, Float, Date, BigInteger, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta

Base = declarative_base()

class HsttDrugbrandMst(Base):
    __tablename__ = 'hstt_drugbrand_mst'
    
    # Using a subset of crucial columns from the Java entity
    hstnumItembrandId = Column(BigInteger, primary_key=True, autoincrement=True) # Assuming this is PK
    gnumHospitalCode = Column(Integer, nullable=False)
    hstnumItemId = Column(Integer)
    hststrItemName = Column(String(200))
    hstnumManufacturerId = Column(Integer)
    hstnumDefaultRate = Column(Float)
    hstnumRateUnitId = Column(Integer)
    hstnumApprovedType = Column(Integer)
    hststrSpecification = Column(Text)
    hstnumItemMake = Column(Integer)
    gstrRemarks = Column(Text)
    gdtEffectiveFrm = Column(Date)
    hststrVedCategory = Column(String(1))
    
class HsttRatecontractItemDtl(Base):
    __tablename__ = 'hstt_ratecontract_item_dtl'

    hstnumRcId = Column(BigInteger, primary_key=True, autoincrement=True)
    gnumHospitalCode = Column(Integer, nullable=False)
    hstnumIsApproval = Column(Integer)
    hstnumContractTypeId = Column(Integer)
    hstnumItemId = Column(Integer)
    hstnumItembrandId = Column(Integer) # FK to drugbrand theoretically
    hststrTenderNo = Column(String(100))
    hststrQuotationNo = Column(String(100))
    hstnumSupplierId = Column(Integer)
    hstnumRate = Column(Float)

class GbltHospitalMst(Base):
    __tablename__ = 'gblt_hospital_mst'
    gnumHospitalCode = Column(Integer, primary_key=True)
    gstrHospitalName = Column(String(200), nullable=False)
    gstrHospitalAddress = Column(String(500))
    gnumContactNo = Column(String(20))

class HsttInventoryDtl(Base):
    __tablename__ = 'hstt_inventory_dtl'

    hstnumInventoryId = Column(BigInteger, primary_key=True, autoincrement=True)
    gnumHospitalCode = Column(Integer, nullable=False)
    hstnumItemId = Column(Integer)
    hstnumItembrandId = Column(Integer)
    hstnumStockQty = Column(Integer)
    hstnumMinStockLevel = Column(Integer)
    hstnumMaxStockLevel = Column(Integer)
    hstdtExpiryDate = Column(Date)
    hststrBatchNo = Column(String(50))

class GbltSupplierMst(Base):
    __tablename__ = 'gblt_supplier_mst'
    supplier_id = Column(Integer, primary_key=True)
    supplier_name = Column(String(200), nullable=False)
    email = Column(String(100))
    contact_no = Column(String(20))
    address = Column(String(500))

class ConversationLog(Base):
    __tablename__ = 'conversation_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(10), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(Date, default=datetime.utcnow)

class GbltOfficerMst(Base):
    __tablename__ = 'gblt_officer_mst'
    id = Column(Integer, primary_key=True, autoincrement=True)
    command_sector = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(Date, default=datetime.utcnow)

def init_db():
    db_path = 'medicines.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed old database.")

    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 0. Generate 10 Suppliers (min 10 constraint)
    suppliers = [
        GbltSupplierMst(supplier_id=301, supplier_name="Astra Medical Suppliers Ltd.", email="astra@astramed.in", contact_no="9876543210", address="Delhi Supply Depot"),
        GbltSupplierMst(supplier_id=302, supplier_name="Bharat Pharma Solutions", email="contact@bharatpharma.co.in", contact_no="9876543211", address="Mumbai Central Logistics Hub"),
        GbltSupplierMst(supplier_id=303, supplier_name="Central Defence Logistics", email="procurement@cdl.gov.in", contact_no="9876543212", address="Kolkata Port Logistics Area"),
        GbltSupplierMst(supplier_id=304, supplier_name="Delta Medical Agencies", email="sales@deltamedical.in", contact_no="9876543213", address="Chennai Outpost Supply Hub"),
        GbltSupplierMst(supplier_id=305, supplier_name="Echo Allied Healthcare Corp", email="support@echoallied.com", contact_no="9876543214", address="Bengaluru High-Tech Park"),
        GbltSupplierMst(supplier_id=306, supplier_name="Apex Pharmaceuticals", email="apex@apexpharma.in", contact_no="9876543215", address="Pune Warehouse"),
        GbltSupplierMst(supplier_id=307, supplier_name="Global Med Devices Ltd.", email="sales@globalmed.in", contact_no="9876543216", address="Hyderabad Supply Hub"),
        GbltSupplierMst(supplier_id=308, supplier_name="Himalaya Health Distributors", email="support@himalayahealth.in", contact_no="9876543217", address="Dehradun Logistics Depot"),
        GbltSupplierMst(supplier_id=309, supplier_name="LifeLine Medical Services", email="contact@lifelinemed.com", contact_no="9876543218", address="Ahmedabad Distribution Centre"),
        GbltSupplierMst(supplier_id=310, supplier_name="Zenith Care Agencies", email="zenith@zenithcare.in", contact_no="9876543219", address="Jaipur Logistics Hub")
    ]
    session.add_all(suppliers)

    # 1. Generate 10 Hospitals (min 10 constraint)
    hospitals = [
        GbltHospitalMst(gnumHospitalCode=101, gstrHospitalName="Alpha Defense Hospital", gstrHospitalAddress="Base 1, Sector A", gnumContactNo="555-0101"),
        GbltHospitalMst(gnumHospitalCode=102, gstrHospitalName="Bravo Medical Center", gstrHospitalAddress="Base 2, Sector B", gnumContactNo="555-0102"),
        GbltHospitalMst(gnumHospitalCode=103, gstrHospitalName="Charlie Field Hospital", gstrHospitalAddress="Camp Charlie", gnumContactNo="555-0103"),
        GbltHospitalMst(gnumHospitalCode=104, gstrHospitalName="Delta Trauma Center", gstrHospitalAddress="HQ Delta", gnumContactNo="555-0104"),
        GbltHospitalMst(gnumHospitalCode=105, gstrHospitalName="Echo Forward Med", gstrHospitalAddress="Outpost Echo", gnumContactNo="555-0105"),
        GbltHospitalMst(gnumHospitalCode=106, gstrHospitalName="Foxtrot General Hospital", gstrHospitalAddress="Base 6, Sector F", gnumContactNo="555-0106"),
        GbltHospitalMst(gnumHospitalCode=107, gstrHospitalName="Golf Medical Base", gstrHospitalAddress="Base 7, Sector G", gnumContactNo="555-0107"),
        GbltHospitalMst(gnumHospitalCode=108, gstrHospitalName="Hotel Field Outpost", gstrHospitalAddress="Camp Hotel", gnumContactNo="555-0108"),
        GbltHospitalMst(gnumHospitalCode=109, gstrHospitalName="India Trauma Center", gstrHospitalAddress="HQ India", gnumContactNo="555-0109"),
        GbltHospitalMst(gnumHospitalCode=110, gstrHospitalName="Juliet Forward Med", gstrHospitalAddress="Outpost Juliet", gnumContactNo="555-0110")
    ]
    session.add_all(hospitals)

    # 2. Define exactly 20 Static medicines data (max 20 constraint)
    # Note: 10 of these are Paracetamol brands to meet the min 10 constraint for the paracetamol view.
    static_medicines = [
        # (id, name, qty, min_stock, hospital_code, expiry_str, batch_no, VED)
        (1, "Paracetamol Mst 305mg", 146, 50, 101, "2028-02-15", "BTCH-45560", "V"),
        (2, "Azithromycin Pro 374mg", 57, 100, 102, "2028-03-20", "BTCH-36181", "E"),
        (3, "Omeprazole Pro 355mg", 427, 100, 103, "2028-04-05", "BTCH-32169", "D"),
        (4, "Simvastatin Mst 429mg", 107, 50, 104, "2028-05-10", "BTCH-44376", "D"),
        (5, "Paracetamol Ultra 302mg", 241, 100, 105, "2028-10-05", "BTCH-58033", "V"),
        (6, "Atorvastatin Plus 416mg", 37, 150, 106, "2028-08-25", "BTCH-33791", "D"),
        (7, "Ibuprofen Mst 134mg", 213, 50, 107, "2028-09-30", "BTCH-18617", "E"),
        (8, "Paracetamol Plus 500mg", 500, 100, 108, "2030-03-30", "BTCH-86382", "V"),
        (9, "Paracetamol Pro 325mg", 120, 50, 109, "2029-01-10", "BTCH-11111", "V"),
        (10, "Paracetamol Max 650mg", 45, 100, 110, "2029-02-12", "BTCH-22222", "V"),
        (11, "Metoprolol XR 194mg", 108, 50, 101, "2029-01-20", "BTCH-34796", "E"),
        (12, "Epinephrine Ultra 492mg", 24, 150, 102, "2029-02-25", "BTCH-51413", "V"),
        (13, "Paracetamol Rapid 500mg", 8, 50, 103, "2029-05-15", "BTCH-33333", "V"),
        (14, "Paracetamol Kids 125mg", 15, 40, 104, "2029-06-20", "BTCH-44444", "V"),
        (15, "Paracetamol Extra 500mg", 220, 100, 105, "2029-07-25", "BTCH-55555", "V"),
        (16, "Bupropion Max 424mg", 793, 150, 106, "2029-06-15", "BTCH-69128", "D"),
        (17, "Ibuprofen Pro 466mg", 367, 100, 107, "2029-07-20", "BTCH-65403", "E"),
        (18, "Paracetamol Relief 250mg", 110, 100, 108, "2029-08-25", "BTCH-66666", "V"),
        (19, "Paracetamol Active 500mg", 15, 60, 109, "2029-09-30", "BTCH-77777", "V"),
        (20, "Amoxicillin Pro 388mg", 154, 100, 110, "2029-05-10", "BTCH-89335", "E")
    ]
    
    # 3. Add Drugs, Rate Contracts and Inventory records statically
    for item in static_medicines:
        id, name, qty, min_stock, hospital_code, expiry_str, batch_no, VED = item
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        
        # Add drug brand definition
        brand = HsttDrugbrandMst(
            hstnumItembrandId=id,
            gnumHospitalCode=hospital_code,
            hstnumItemId=1000 + id,
            hststrItemName=name,
            hstnumManufacturerId=1,
            hstnumDefaultRate=50.00,
            hstnumRateUnitId=1,
            hstnumApprovedType=1,
            hststrSpecification=f"Standard specifications for {name}",
            hstnumItemMake=1,
            gstrRemarks="Permanent static entry",
            gdtEffectiveFrm=datetime.strptime("2026-01-01", "%Y-%m-%d").date(),
            hststrVedCategory=VED
        )
        session.add(brand)
        
        # Add rate contract details (Suppliers linked dynamically modulo 10)
        contract = HsttRatecontractItemDtl(
            hstnumRcId=id,
            gnumHospitalCode=hospital_code,
            hstnumIsApproval=1,
            hstnumContractTypeId=1,
            hstnumItemId=1000 + id,
            hstnumItembrandId=id,
            hststrTenderNo=f"TNDR/2026/{5000+id}",
            hststrQuotationNo=f"QUOT/{10000+id}",
            hstnumSupplierId=301 + ((id - 1) % 10),
            hstnumRate=45.00
        )
        session.add(contract)
        
        # Add inventory details
        inventory = HsttInventoryDtl(
            hstnumInventoryId=id,
            gnumHospitalCode=hospital_code,
            hstnumItemId=1000 + id,
            hstnumItembrandId=id,
            hstnumStockQty=qty,
            hstnumMinStockLevel=min_stock,
            hstnumMaxStockLevel=min_stock * 3,
            hstdtExpiryDate=expiry_date,
            hststrBatchNo=batch_no
        )
        session.add(inventory)
        
    session.commit()
    
    # Create a simplified view for the AI Agent
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE VIEW vw_medicine_inventory AS
            SELECT 
                d.hststrItemName AS MedicineName,
                i.hstnumStockQty AS Quantity,
                i.hstnumMinStockLevel AS MinStock,
                i.hstdtExpiryDate AS ExpiryDate,
                i.hststrBatchNo AS BatchNo,
                d.gnumHospitalCode AS HospitalCode
            FROM hstt_inventory_dtl i
            JOIN hstt_drugbrand_mst d ON i.hstnumItembrandId = d.hstnumItembrandId
        '''))
        
        conn.execute(text('''
            CREATE VIEW vw_active_contracts AS
            SELECT 
                c.hstnumRcId AS ContractID,
                d.hststrItemName AS MedicineName,
                c.hstnumRate AS Rate,
                c.hststrTenderNo AS TenderNo,
                c.hststrQuotationNo AS QuotationNo,
                c.hstnumSupplierId AS SupplierID,
                s.supplier_name AS SupplierName,
                c.gnumHospitalCode AS HospitalCode
            FROM hstt_ratecontract_item_dtl c
            JOIN hstt_drugbrand_mst d ON c.hstnumItembrandId = d.hstnumItembrandId
            LEFT JOIN gblt_supplier_mst s ON c.hstnumSupplierId = s.supplier_id
        '''))
        
        conn.execute(text('''
            CREATE VIEW vw_registered_hospitals AS
            SELECT 
                gnumHospitalCode AS HospitalCode,
                gstrHospitalName AS HospitalName,
                gstrHospitalAddress AS Address,
                gnumContactNo AS ContactNo
            FROM gblt_hospital_mst
        '''))
        
        conn.execute(text('''
            CREATE VIEW vw_low_stock_alerts AS
            SELECT * FROM vw_medicine_inventory
            WHERE Quantity < MinStock
        '''))

        conn.execute(text('''
            CREATE VIEW vw_suppliers AS
            SELECT 
                supplier_id AS SupplierID,
                supplier_name AS SupplierName,
                email AS Email,
                contact_no AS ContactNo,
                address AS Address
            FROM gblt_supplier_mst
        '''))

        conn.execute(text('''
            CREATE VIEW vw_paracetamol_inventory AS
            SELECT * FROM vw_medicine_inventory
            WHERE MedicineName LIKE '%Paracetamol%'
        '''))

        conn.execute(text('''
            CREATE VIEW ved AS
            SELECT 
                d.hststrItemName AS MedicineName,
                i.hstnumStockQty AS Quantity,
                d.hststrVedCategory AS VEDCategory,
                CASE d.hststrVedCategory
                    WHEN 'V' THEN 'Vital'
                    WHEN 'E' THEN 'Essential'
                    WHEN 'D' THEN 'Desirable'
                END AS Criticality
            FROM hstt_inventory_dtl i
            JOIN hstt_drugbrand_mst d ON i.hstnumItembrandId = d.hstnumItembrandId
        '''))

        conn.execute(text('''
            CREATE VIEW vw_ved AS
            SELECT * FROM ved
        '''))

        conn.execute(text('''
            CREATE VIEW vw_ved_analysis AS
            SELECT * FROM ved
        '''))
        
        conn.commit()

    print("Database seeded with DVDMS schema successfully.")

if __name__ == '__main__':
    init_db()
