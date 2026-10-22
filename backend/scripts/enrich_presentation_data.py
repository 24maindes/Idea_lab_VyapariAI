"""
enrich_presentation_data.py
---------------------------
Populates realistic presentation data for VyapariAI:
1. Refined supplier market profiles (addresses in Itwari, Kalamna APMC, Cotton Market, Nagpur).
2. Proper reference commodity linkage for all products.
3. Realistic activity timeline entries spanning the past week.
4. Rich multi-lingual AI Advisor chat history (English, Hindi, Marathi).
5. Fresh anomaly and stock-level scans to illuminate dashboard metrics.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import datetime as dt
from app.database import SessionLocal
from app.models import Shop, Product, Supplier, ActivityLog, AdvisorMessage, Purchase, Sale
from app.services.anomaly_service import scan_shop
from app.services.cache import invalidate_shop

def main():
    db = SessionLocal()
    try:
        shop = db.query(Shop).first()
        if not shop:
            print("[error] No shop found in database.")
            return

        print(f"[info] Enriching data for shop: {shop.shop_name} (ID: {shop.id})")

        # 1. Update suppliers with authentic local market addresses and phones
        supplier_updates = {
            "ABC Traders": {
                "contact": "+91 98220 14589",
                "address": "Gala No. 14, Itwari Wholesale Grain Market, Nagpur - 440002"
            },
            "Sharma Foods": {
                "contact": "+91 98220 36721",
                "address": "Shop 8, APMC Kalamna Mandi, Outer Ring Road, Nagpur - 440035"
            },
            "XYZ Wholesale": {
                "contact": "+91 98220 98124",
                "address": "Bhandara Road, Golibar Square, Ganjakhet, Nagpur - 440018"
            },
            "GoodFood Co.": {
                "contact": "+91 98220 77312",
                "address": "Wholesale Shed 3, Cotton Market Square, Ghat Road, Nagpur - 440018"
            }
        }
        for s in db.query(Supplier).filter(Supplier.shop_id == shop.id).all():
            if s.name in supplier_updates:
                s.contact = supplier_updates[s.name]["contact"]
                s.address = supplier_updates[s.name]["address"]
        db.commit()
        print("[success] Supplier profiles updated with authentic local market data.")

        # 2. Ensure all products have mapped reference commodities
        for p in db.query(Product).filter(Product.shop_id == shop.id).all():
            if not p.reference_commodity:
                if "rice" in p.name.lower():
                    p.reference_commodity = "Rice"
                elif "oil" in p.name.lower():
                    p.reference_commodity = "Soyabean Oil"
                elif "atta" in p.name.lower() or "flour" in p.name.lower():
                    p.reference_commodity = "Wheat Atta"
                elif "dal" in p.name.lower():
                    p.reference_commodity = "Toor Dal"
        db.commit()
        print("[success] All product commodity references linked.")

        # 3. Add rich, realistic activity log entries spanning the past 7 days
        db.query(ActivityLog).filter(ActivityLog.shop_id == shop.id).delete()
        now = dt.datetime.now()
        activities = [
            ("purchase", "Purchased 50 kg Toor Dal from XYZ Wholesale at Rs 146.00/kg (Fair Price: Slightly High).", now - dt.timedelta(hours=2)),
            ("alert", "Price anomaly detected: Soyabean Oil purchase flagged at +24.8% over reference index.", now - dt.timedelta(hours=5)),
            ("stock", "Low stock warning: Tomato stock reached 12.0 kg (below reorder threshold of 25 kg).", now - dt.timedelta(hours=18)),
            ("sale", "Daily sales closed: Recorded 48 customer bills totaling Rs 10,420.00 across all categories.", now - dt.timedelta(days=1, hours=3)),
            ("forecast", "Automated forecast update: Holt-Winters selected for Rice (7-day expected trend: +2.4%).", now - dt.timedelta(days=1, hours=8)),
            ("recommendation", "Decision Engine triggered: Recommending BUY NOW for Toor Dal (quantity 54 kg, surge expected).", now - dt.timedelta(days=2, hours=1)),
            ("purchase", "Purchased 100 kg Wheat Atta from GoodFood Co. at Rs 35.50/kg (Fair Price: Fair).", now - dt.timedelta(days=2, hours=6)),
            ("pricing", "Selling price range updated: Suggested retail corridor for Soyabean Oil set to Rs 145.00 - Rs 158.00.", now - dt.timedelta(days=3, hours=2)),
            ("supplier", "Supplier comparison evaluated: ABC Traders identified as lowest variance vendor for Grains.", now - dt.timedelta(days=3, hours=9)),
            ("purchase", "Purchased 150 kg Rice from ABC Traders at Rs 39.80/kg (Fair Price: Great Deal).", now - dt.timedelta(days=4, hours=4)),
            ("alert", "Consensus anomaly detector flagged Sugar purchase (+28.2% vs Kalamna Mandi reference).", now - dt.timedelta(days=5, hours=2)),
            ("scan", "Automated shop scan completed across 525 recorded transactions.", now - dt.timedelta(days=6, hours=5)),
        ]
        for kind, text, created in activities:
            db.add(ActivityLog(shop_id=shop.id, kind=kind, text=text, created_at=created))
        db.commit()
        print(f"[success] {len(activities)} realistic activity timeline events populated.")

        # 4. Add rich multilingual AI Advisor conversation threads
        db.query(AdvisorMessage).filter(AdvisorMessage.shop_id == shop.id).delete()
        advisor_threads = [
            # English restock decision thread
            ("user", "Should I buy Toor Dal this week or wait for the price to drop?", "en", now - dt.timedelta(days=2, hours=4)),
            ("assistant", "Recommendation: **BUY NOW** (High Urgency).\n\n"
                          "- **Current Stock:** 6 kg (estimated ~1.8 days of cover remaining based on daily sales velocity of 3.4 kg/day).\n"
                          "- **Market Outlook:** The 7-day rolling forecast indicates wholesale prices are expected to rise by **7.4%** across regional markets.\n"
                          "- **Suggested Order:** 54 kg (includes a 1.2x surge buffer before price escalation).\n"
                          "- **Preferred Vendor:** **ABC Traders** offers the lowest historical price variance (-1.8% vs market).", "en", now - dt.timedelta(days=2, hours=3, minutes=58)),

            # Hindi supplier comparison thread
            ("user", "सोयाबीन तेल के लिए कौन सा सप्लायर सबसे सही रहेगा?", "hi", now - dt.timedelta(days=1, hours=6)),
            ("assistant", "आपके पिछले 90 दिनों के खरीद रिकॉर्ड के आधार पर:\n\n"
                          "1. **ABC Traders** सबसे किफ़ायती और स्थिर सप्लायर है (औसत भाव **₹124.50/लीटर**, बाजार भाव से 2.1% कम, स्थिरता 1.5%)।\n"
                          "2. **XYZ Wholesale** का औसत भाव ₹131.00/लीटर है और उनके भाव में 8.4% की अधिक अस्थिरता देखी गई है।\n\n"
                          "👉 **सलाह:** सोयाबीन तेल का अगला ऑर्डर **ABC Traders** को देना आपके मार्जिन के लिए सबसे बेहतर रहेगा।", "hi", now - dt.timedelta(days=1, hours=5, minutes=57)),

            # Marathi inventory & pricing thread
            ("user", "दुकानात कोणत्या वस्तूंचा साठा कमी झाला आहे आणि तूर डाळीचा विक्री भाव काय ठेवावा?", "mr", now - dt.timedelta(hours=4)),
            ("assistant", "तुमच्या दुकानाची सद्यस्थिती खालीलप्रमाणे आहे:\n\n"
                          "⚠️ **कमी साठा इशारा (Low Stock):**\n"
                          "- **टोमॅटो (Tomato):** सध्याचा साठा 12.0 किलो (किमान 25 किलो आवश्यक).\n"
                          "- **तूर डाळ (Toor Dal):** सध्याचा साठा 6.0 किलो (किमान 10 किलो आवश्यक).\n\n"
                          "💰 **तूर डाळ विक्री भाव कॉरिडोअर (Selling Price Corridor):**\n"
                          "- **खरेदी खर्च आधार:** ₹132.50 / किलो\n"
                          "- **किमान मार्जिन (Floor 8%):** ₹143.10 / किलो\n"
                          "- **शिफारस केलेला विक्री दर:** **₹148.00 ते ₹155.00 / किलो**\n"
                          "हा दर बाजारातील स्पर्धेला तोंड देत तुमचा किमान नफा सुरक्षित ठेवतो.", "mr", now - dt.timedelta(hours=3, minutes=58)),
        ]
        for role, content, lang, created in advisor_threads:
            db.add(AdvisorMessage(shop_id=shop.id, role=role, content=content, language=lang, created_at=created))
        db.commit()
        print(f"[success] {len(advisor_threads)} multilingual AI Advisor interactions added.")

        # 5. Run anomaly scan to verify alerts
        scan_res = scan_shop(db, shop)
        print(f"[success] Anomaly & stock scan finished: {scan_res}")

        # Invalidate cache so changes reflect instantly in API responses
        invalidate_shop(shop.id)
        print("[success] Cache invalidated successfully.")

    finally:
        db.close()

if __name__ == "__main__":
    main()
