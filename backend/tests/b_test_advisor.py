"""Advisor: entity matching, topics, fallback answers, retrieval context and the chat API (Gemini is always mocked)."""
import datetime as dt
import json
from types import SimpleNamespace as P

import pytest

from app.services.advisor import entities, fallback, gemini_client, prompt, retrieval
from conftest import TODAY

NAMES = ["Rice", "Wheat Atta", "Sugar", "Toor Dal", "Soyabean Oil", "Mustard Oil", "Salt", "Onion", "Potato", "Tomato", "Milk"]
PRODUCTS = [P(id=i, name=n) for i, n in enumerate(NAMES, 1)]


def names(q):
    return [p.name for p in entities.match_products(q, PRODUCTS)]


# ---------------------------------------------------------------- product matching
@pytest.mark.parametrize("question, expected", [
    ("Is the price of rice fair?", ["Rice"]),
    ("RICE", ["Rice"]),
    ("Should I buy toor dal and sugar?", ["Toor Dal", "Sugar"]),
    ("chawal ka bhav kya hai", ["Rice"]),
    ("चावल का भाव सही है?", ["Rice"]),
    ("तांदळाचा भाव वाढेल का?", ["Rice"]),                    # Marathi ending -चा
    ("tandul kiti ne ghyava?", ["Rice"]),
    ("गेहूं का आटा खरीदूं?", ["Wheat Atta"]),
    ("गेहूँ का आटा", ["Wheat Atta"]),                         # chandrabindu variant
    ("pyaz kitna bacha", ["Onion"]), ("कांद्याचा भाव", ["Onion"]), ("kanda", ["Onion"]),
    ("aloo", ["Potato"]), ("बटाट्याचा", ["Potato"]), ("tamatar", ["Tomato"]), ("टोमॅटो", ["Tomato"]),
    ("doodh", ["Milk"]), ("दूध", ["Milk"]), ("namak", ["Salt"]), ("मीठ", ["Salt"]),
    ("shakkar", ["Sugar"]), ("साखर आणि दूध", ["Sugar", "Milk"]),
    ("arhar dal", ["Toor Dal"]),
])
def test_product_matching(question, expected):
    assert names(question) == expected


def test_matching_is_whole_word_for_latin():
    assert names("what is the price today") == []                 # "rice" is inside "price" but must not match
    assert names("hotel and hospital") == []                       # "tel" is inside "hotel"
    assert names("a plateful of saltine") == []
    assert names("rices") == ["Rice"]                              # plural is fine


def test_matching_ignores_case_and_latin_accents():
    assert names("PYAZ") == ["Onion"] and names("Café RICE") == ["Rice"]


def test_specific_oil_beats_generic_oil_word():
    assert names("soyabean oil price") == ["Soyabean Oil"]
    assert names("mustard oil") == ["Mustard Oil"]
    assert sorted(names("oil kitna bacha")) == ["Mustard Oil", "Soyabean Oil"]     # ambiguous word -> both
    assert names("तेल")  and set(names("tel ka bhav")) == {"Mustard Oil", "Soyabean Oil"}


def test_the_products_own_name_always_matches():
    custom = [P(id=1, name="Basmati Premium"), P(id=2, name="Rice")]
    assert [p.name for p in entities.match_products("basmati premium rate", custom)] == ["Basmati Premium"]


def test_unrelated_text_matches_nothing():
    assert names("hello how are you") == [] and names("") == [] and names("   ") == []


# ---------------------------------------------------------------- topics
@pytest.mark.parametrize("question, topic", [
    ("Is this price fair?", "price_fairness"), ("am I overpaying", "price_fairness"), ("मैं ज्यादा दाम दे रहा हूं", "price_fairness"),
    ("बाजार भाव वाजवी आहे का", "price_fairness"),
    ("Should I buy now?", "buy_decision"), ("kitna kharidu", "buy_decision"), ("खरेदी करू का", "buy_decision"), ("कब खरीदूं", "buy_decision"),
    ("will the price go up next week?", "forecast"), ("bhav badhega kya", "forecast"), ("भाव वाढेल का", "forecast"), ("अगले हफ्ते भाव बढ़ेगा", "forecast"),
    ("how much stock is left", "stock"), ("kitna bacha hai", "stock"), ("साठा किती शिल्लक", "stock"), ("स्टॉक कितना है", "stock"),
    ("which supplier is cheapest", "supplier"), ("सबसे सस्ता सप्लायर", "supplier"), ("सर्वात स्वस्त पुरवठादार", "supplier"),
    ("what selling price for 15% margin", "selling_price"), ("कितने में बेचूं", "selling_price"), ("नफा किती", "selling_price"), ("vikri bhav", "selling_price"),
    ("any alerts?", "alerts"), ("अलर्ट", "alerts"), ("इशारा", "alerts"),
])
def test_topic_detection(question, topic):
    assert topic in entities.detect_topics(question)


def test_selling_price_question_is_not_a_purchase_price_question():
    t = entities.detect_topics("what price should I sell rice at, what margin")
    assert "selling_price" in t and "price_fairness" not in t


def test_no_keywords_gives_general():
    assert entities.detect_topics("hello") == {"general"}


def test_overview_detection():
    assert entities.is_overview_question("what should I buy today?") and entities.is_overview_question("आज क्या खरीदूं")
    assert not entities.is_overview_question("price of rice")


# ---------------------------------------------------------------- prompt
def test_prompt_contains_rules_context_language_and_history():
    ctx = {"products": [{"name": "Rice"}], "missing": ["No forecast"]}
    system, contents = prompt.build_messages(ctx, "How is rice?", "mr", [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}] * 4)
    assert "ONLY from the CONTEXT" in system and "Marathi" in system and '"name":"Rice"' in system and "No forecast" in system
    assert len(contents) == 5 and contents[-1] == {"role": "user", "parts": [{"text": "How is rice?"}]}      # last 4 + the question
    assert contents[1]["role"] == "model"


# ---------------------------------------------------------------- gemini client (no network)
def test_missing_key_raises_clean_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "x")
    with pytest.raises(gemini_client.AdvisorUnavailable, match="GEMINI_API_KEY"):
        gemini_client.generate("s", [])
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("GEMINI_MODEL")
    with pytest.raises(gemini_client.AdvisorUnavailable, match="GEMINI_MODEL"):
        gemini_client.generate("s", [])


def test_network_failure_is_retried_once_then_clean_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "bad-key")
    monkeypatch.setenv("GEMINI_MODEL", "some-model")
    calls = []
    import google.genai as g

    class Boom:
        def __init__(self, *a, **k): self.models = self
        def generate_content(self, **k):
            calls.append(1)
            raise ConnectionError("no internet")
    monkeypatch.setattr(g, "Client", Boom)
    with pytest.raises(gemini_client.AdvisorUnavailable, match="ConnectionError"):
        gemini_client.generate("s", [{"role": "user", "parts": [{"text": "hi"}]}])
    assert len(calls) == 2                                          # first try + exactly one retry


# ---------------------------------------------------------------- fallback (pure)
def sample_ctx(action="Buy Now", quantity=120.0, with_forecast=True, with_market=True):
    return {"products": [{
        "name": "Rice", "unit": "kg", "stock": 20.0, "reorderLevel": 10, "avgDailySales": 10.0, "daysOfStockLeft": 2.0,
        "fairPrice": {"lastPurchasePrice": 48.0, "lastPurchaseDate": "2026-09-30", "marketPrice": 42.0 if with_market else None,
                      "variancePct": 14.3 if with_market else None, "verdict": "Overpaying" if with_market else None, "potentialSavings180d": 300.0},
        "forecast": {"priceNow": 42.0, "priceIn7Days": 44.0, "changePct": 4.8, "direction": "Rising", "modelMape": 0.6, "modelName": "linear"} if with_forecast else None,
        "purchaseRecommendation": {"action": action, "quantity": quantity if action != "Wait" else 0, "checkAgainInDays": 5 if action == "Wait" else None, "reasons": ["r"], "confidence": "High"},
        "sellingPrice": {"recommended": 47.0, "rangeLow": 45.5, "rangeHigh": 49.0, "expectedMarginPct": 12.0, "currentPrice": 48.0, "warnings": []},
        "suppliers": [{"supplier": "ABC Traders", "avgPrice": 41.0, "stability": "Stable", "avgVsMarketPct": -2.0, "purchases": 8, "bestValue": True}],
        "unreadAlerts": ["Rice bought at Rs 58 is 38% above market"], "lastPurchases": []}],
        "missing": [], "topics": []}


def has_devanagari(s):
    return any("\u0900" <= c <= "\u097f" for c in s)


@pytest.mark.parametrize("lang", ["en", "hi", "mr"])
def test_fallback_buy_now_has_action_quantity_and_numbers(lang):
    a = fallback.fallback_answer(sample_ctx(), {"buy_decision"}, lang)
    assert "120" in a and "Rice" in a and "₹48" in a and "₹42" in a and "+14.3%" in a and "20" in a
    assert has_devanagari(a) == (lang != "en")
    assert a.splitlines()[0] != "" and a.strip().endswith(fallback.T[lang]["basic"].strip())


@pytest.mark.parametrize("lang", ["en", "hi", "mr"])
def test_fallback_other_topics(lang):
    ctx = sample_ctx()
    assert "₹44" in fallback.fallback_answer(ctx, {"forecast"}, lang) and "4.8" in fallback.fallback_answer(ctx, {"forecast"}, lang)
    assert "ABC Traders" in fallback.fallback_answer(ctx, {"supplier"}, lang)
    s = fallback.fallback_answer(ctx, {"selling_price"}, lang)
    assert "₹47" in s and "₹45.5" in s and "12" in s
    assert "1" in fallback.fallback_answer(ctx, {"alerts"}, lang)


def test_fallback_wait_and_limited():
    assert "Wait 5 days" in fallback.fallback_answer(sample_ctx("Wait"), {"buy_decision"}, "en")
    assert "small quantity" in fallback.fallback_answer(sample_ctx("Buy Limited", 20.0), {"buy_decision"}, "en")
    assert "5 दिन" in fallback.fallback_answer(sample_ctx("Wait"), {"buy_decision"}, "hi")
    assert "5 दिवस" in fallback.fallback_answer(sample_ctx("Wait"), {"buy_decision"}, "mr")


def test_fallback_handles_missing_data_without_crashing():
    a = fallback.fallback_answer(sample_ctx(with_forecast=False, with_market=False), {"general"}, "en")
    assert "No price forecast" in a and "No market price" in a
    c = sample_ctx()
    c["products"][0]["fairPrice"]["lastPurchasePrice"] = None
    assert "no purchase" in fallback.fallback_answer(c, {"price_fairness"}, "en").lower()


def test_fallback_overview_and_not_found():
    ov = {"overview": {"topRecommendations": [{"product": "Rice", "action": "Buy Now", "quantity": 50.0, "unit": "kg", "reason": "x"}],
                       "lowStock": [{"name": "Tomato"}], "unreadAlerts": ["a", "b"], "overpayingProducts": ["Milk"]}, "missing": []}
    a = fallback.fallback_answer(ov, {"general"}, "en")
    assert "Rice" in a and "50" in a and "Tomato" in a and "Milk" in a
    quiet = {"overview": {"topRecommendations": [], "lowStock": [], "unreadAlerts": [], "overpayingProducts": []}, "missing": []}
    assert "Nothing urgent" in fallback.fallback_answer(quiet, {"general"}, "en")
    assert "Rice, Milk" in fallback.not_found_answer(["Rice", "Milk"], "en") and has_devanagari(fallback.not_found_answer(["Rice"], "mr"))


# ---------------------------------------------------------------- API with a real shop (Gemini mocked)
@pytest.fixture()
def adv(client, shop_with_data, monkeypatch):
    d = shop_with_data
    for i in range(6):
        client.post("/api/purchases", headers=d["headers"], json={"productId": d["product"]["id"], "supplierId": d["supplier"]["id"],
                    "quantity": 20, "unitPrice": 41.0, "purchaseDate": (TODAY - dt.timedelta(days=40 - 7 * i)).isoformat()})
    for i in range(10):
        client.post("/api/sales", headers=d["headers"], json={"productId": d["product"]["id"], "quantity": 8, "saleDate": (TODAY - dt.timedelta(days=i)).isoformat()})
    seen = {}

    def fake_generate(system, contents):
        seen["system"], seen["contents"] = system, contents
        return "Buy now. This is a mocked AI answer."
    monkeypatch.setattr(gemini_client, "generate", fake_generate)
    d["seen"] = seen
    return d


def chat(client, d, message, **kw):
    return client.post("/api/advisor/chat", headers=d["headers"], json={"message": message, **kw})


def test_chat_uses_gemini_and_returns_sources(client, adv):
    r = chat(client, adv, "Is the price of rice fair?", language="en")
    assert r.status_code == 200
    b = r.json()
    assert b["answer"].startswith("Buy now") and b["usedFallback"] is False and b["language"] == "en"
    assert b["matchedProducts"] == [{"id": adv["product"]["id"], "name": "Rice"}]
    labels = {s["label"]: s["value"] for s in b["sources"]}
    assert labels["Last purchase price"].startswith("Rs 41/kg") and "Market price on that day" in labels and "Stock now" in labels
    ctx = json.loads(adv["seen"]["system"].split("CONTEXT (JSON, real data of this shop):")[1])
    assert ctx["products"][0]["name"] == "Rice" and ctx["products"][0]["stock"] == 40.0 and len(ctx["products"][0]["lastPurchases"]) == 6
    assert ctx["dataDate"] and "missing" in ctx
    assert len(json.dumps(ctx, ensure_ascii=False)) <= retrieval.MAX_CHARS


def test_context_never_includes_other_shops_data(client, adv, register_user, create_shop):
    chat(client, adv, "rice stock", language="en")
    shop1_prompt = adv["seen"]["system"]                                     # what shop 1's AI saw
    assert "ABC Traders" in shop1_prompt and "41" in shop1_prompt

    h2 = register_user("b@test.com")
    create_shop(h2)
    client.post("/api/products", headers=h2, json={"name": "Rice", "unit": "kg", "openingStock": 3})
    client.post("/api/advisor/chat", headers=h2, json={"message": "rice stock", "language": "en"})
    shop2_prompt = adv["seen"]["system"]                                     # what shop 2's AI saw
    ctx2 = json.loads(shop2_prompt.split("CONTEXT (JSON, real data of this shop):")[1])
    assert ctx2["products"][0]["stock"] == 3.0 and ctx2["products"][0]["lastPurchases"] == []
    assert "ABC Traders" not in shop2_prompt and "Test Store" not in shop2_prompt.replace(ctx2["shop"]["name"], "")
    # and the other way round
    assert '"stock":3.0' not in shop1_prompt and [m["role"] for m in client.get("/api/advisor/history", headers=adv["headers"]).json()] == ["user", "assistant"]


@pytest.mark.parametrize("lang", ["en", "hi", "mr"])
def test_fallback_when_gemini_is_unavailable(client, adv, monkeypatch, lang):
    def down(system, contents):
        raise gemini_client.AdvisorUnavailable("GEMINI_API_KEY is not set")
    monkeypatch.setattr(gemini_client, "generate", down)
    b = chat(client, adv, "Should I buy rice?", language=lang).json()
    assert b["usedFallback"] is True and b["answer"] and has_devanagari(b["answer"]) == (lang != "en")
    assert len(b["sources"]) >= 3


def test_unknown_product_gets_polite_not_found(client, adv):
    adv["seen"].clear()
    b = chat(client, adv, "What is the price of saffron?", language="en").json()
    assert "could not find that product" in b["answer"] and "Rice" in b["answer"] and b["matchedProducts"] == [] and b["sources"] == []
    assert adv["seen"] == {}                                                 # the AI was not even called
    hi = chat(client, adv, "केसर का भाव क्या है", language="hi").json()
    assert has_devanagari(hi["answer"])


def test_overview_questions_without_product_use_the_shop_overview(client, adv):
    chat(client, adv, "What should I buy today?", language="en")
    ctx = json.loads(adv["seen"]["system"].split("CONTEXT (JSON, real data of this shop):")[1])
    assert "overview" in ctx and "products" not in ctx and ctx["overview"]["topRecommendations"]


def test_product_id_preselects_the_product(client, adv):
    b = chat(client, adv, "Is it fair?", language="en", productId=adv["product"]["id"]).json()
    assert b["matchedProducts"][0]["name"] == "Rice"
    assert chat(client, adv, "hi", productId=99999).status_code == 404


def test_language_defaults_to_the_shop_language(client, adv):
    client.put("/api/shop", headers=adv["headers"], json={"language": "mr"})
    assert chat(client, adv, "rice stock").json()["language"] == "mr"
    assert "Marathi" in adv["seen"]["system"]


@pytest.mark.parametrize("body", [{"message": ""}, {"message": "x" * 501}, {"message": "hi", "language": "fr"}])
def test_chat_validation(client, adv, body):
    assert client.post("/api/advisor/chat", headers=adv["headers"], json=body).status_code == 422


def test_history_save_order_and_clear(client, adv):
    chat(client, adv, "rice stock", language="en")
    chat(client, adv, "rice price", language="en")
    h = client.get("/api/advisor/history", headers=adv["headers"]).json()
    assert [m["role"] for m in h] == ["user", "assistant", "user", "assistant"] and h[0]["content"] == "rice stock"
    assert len(client.get("/api/advisor/history?limit=2", headers=adv["headers"]).json()) == 2
    assert client.delete("/api/advisor/history", headers=adv["headers"]).status_code == 204
    assert client.get("/api/advisor/history", headers=adv["headers"]).json() == []


def test_previous_messages_are_sent_as_history(client, adv):
    chat(client, adv, "rice stock", language="en")
    chat(client, adv, "and the price?", language="en")
    contents = adv["seen"]["contents"]
    assert len(contents) == 3 and contents[0]["role"] == "user" and contents[1]["role"] == "model" and contents[-1]["parts"][0]["text"] == "and the price?"


def test_chat_needs_login(client):
    assert client.post("/api/advisor/chat", json={"message": "hi"}).status_code == 401
    assert client.get("/api/advisor/history").status_code == 401


def test_context_is_trimmed_to_the_budget():
    ctx = {"products": [{"lastPurchases": [{"date": "2026-01-01", "supplier": "S" * 40, "quantity": 1, "unitPrice": 1.0}] * 10,
                         "suppliers": [{"supplier": "S" * 60, "avgPrice": 1.0, "stability": "Stable", "avgVsMarketPct": 1, "purchases": 3, "bestValue": False}] * 40,
                         "purchaseRecommendation": {"reasons": ["x" * 400] * 5}} for _ in range(3)], "missing": []}
    assert len(json.dumps(retrieval._trim(ctx), ensure_ascii=False)) <= retrieval.MAX_CHARS
