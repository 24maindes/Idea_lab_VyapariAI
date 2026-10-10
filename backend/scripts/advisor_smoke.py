"""
advisor_smoke.py - ask the advisor 18 questions against the running demo shop and print the answers.

    1. start the backend:   python -m uvicorn app.main:app
    2. run:                 python scripts/advisor_smoke.py            (from the backend folder)
Set GEMINI_API_KEY and GEMINI_MODEL in backend/.env (or the environment of the SERVER) to see real AI answers;
without them you see the offline fallback answers ("usedFallback": true).
"""
import json
import os
import sys
import urllib.request

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")
EMAIL, PASSWORD = "demo@vyapariai.com", "demo1234"

QUESTIONS = [
    # 5 English
    ("en", "Is the price I paid for rice fair?"), ("en", "Should I buy sugar now?"), ("en", "Will the price of onion go up next week?"),
    ("en", "How much toor dal stock is left?"), ("en", "What selling price should I keep for milk?"),
    # 5 Hindi
    ("hi", "चावल का भाव सही है?"), ("hi", "क्या मुझे अभी चीनी खरीदनी चाहिए?"), ("hi", "प्याज का भाव अगले हफ्ते बढ़ेगा क्या?"),
    ("hi", "तूर दाल का स्टॉक कितना बचा है?"), ("hi", "दूध कितने में बेचूं?"),
    # 5 Marathi
    ("mr", "तांदळाचा भाव वाजवी आहे का?"), ("mr", "आत्ता साखर खरेदी करू का?"), ("mr", "कांद्याचा भाव पुढच्या आठवड्यात वाढेल का?"),
    ("mr", "तूर डाळीचा साठा किती शिल्लक आहे?"), ("mr", "दुधाला किती भाव ठेवू?"),
    # 3 without a product
    ("en", "What should I buy today?"), ("hi", "आज किन चीजों पर ध्यान देना है?"), ("mr", "आज काय खरेदी करू?"),
]


def call(path, body=None, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> None:
    try:
        token = call("/api/auth/login", {"email": EMAIL, "password": PASSWORD})["access_token"]
    except Exception as e:
        sys.exit(f"Could not log in as the demo user ({e}). Is the server running and the demo data seeded?")
    fallback_count = 0
    for i, (lang, q) in enumerate(QUESTIONS, 1):
        r = call("/api/advisor/chat", {"message": q, "language": lang}, token)
        fallback_count += r["usedFallback"]
        print(f"\n[{i:02}] ({lang}) {q}")
        print(f"     products: {[p['name'] for p in r['matchedProducts']]}   usedFallback: {r['usedFallback']}")
        print("     " + r["answer"].replace("\n", "\n     "))
        for s in r["sources"][:3]:
            print(f"       - {s['label']}: {s['value']}")
    print(f"\nDone. {len(QUESTIONS)} questions, {fallback_count} answered by the offline fallback.")


if __name__ == "__main__":
    main()
