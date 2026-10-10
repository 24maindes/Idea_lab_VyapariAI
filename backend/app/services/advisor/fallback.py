"""
advisor/fallback.py - a basic answer WITHOUT the AI model.

Used when Gemini cannot be reached (no key, quota, no internet). It fills fixed sentence templates (English, Hindi,
Marathi) with the same numbers the AI would have seen, so the shopkeeper still gets the key facts and the advice.
"""
VERDICT = {
    "en": {"Great deal": "great deal", "Fair": "fair price", "Slightly high": "slightly high", "Overpaying": "overpaying"},
    "hi": {"Great deal": "बहुत अच्छा सौदा", "Fair": "वाजिब भाव", "Slightly high": "थोड़ा ज़्यादा", "Overpaying": "बहुत ज़्यादा दाम दिया"},
    "mr": {"Great deal": "खूप चांगला व्यवहार", "Fair": "वाजवी भाव", "Slightly high": "थोडा जास्त", "Overpaying": "खूप जास्त भाव दिला"},
}
DIRECTION = {
    "en": {"Rising": "rising", "Falling": "falling", "Stable": "stable"},
    "hi": {"Rising": "बढ़ रहा है", "Falling": "गिर रहा है", "Stable": "स्थिर है"},
    "mr": {"Rising": "वाढत आहे", "Falling": "घटत आहे", "Stable": "स्थिर आहे"},
}
ACTION = {
    "en": {"Buy Now": "Buy now", "Buy Limited": "Buy a small quantity", "Wait": "Wait"},
    "hi": {"Buy Now": "अभी खरीदें", "Buy Limited": "थोड़ा ही खरीदें", "Wait": "रुकें"},
    "mr": {"Buy Now": "आत्ताच खरेदी करा", "Buy Limited": "थोडेच खरेदी करा", "Wait": "थांबा"},
}
T = {
    "en": {
        "buy_now": "Buy now: order {qty} {unit} of {name}.",
        "limited": "Buy a small quantity: {qty} {unit} of {name}.",
        "wait": "Wait {days} days before buying {name}.",
        "wait_plain": "No need to buy {name} now.",
        "stock": "Stock of {name}: {stock} {unit}" + ", about {days} days.",
        "stock_nodays": "Stock of {name}: {stock} {unit}.",
        "fair": "{name}: your last price was {p}, the market price was {m} ({v:+.1f}%): {verdict}.",
        "fair_nomarket": "{name}: your last price was {p}. No market price is available to compare.",
        "no_purchase": "{name}: no purchase has been recorded yet.",
        "forecast": "{name} price forecast: {now} now, {f7} in 7 days ({chg:+.1f}%, {direction}).",
        "no_forecast": "No price forecast is available for {name}.",
        "estimate": "Forecasts are estimates, not promises.",
        "supplier": "Best supplier for {name}: {s} (average {p}).",
        "no_supplier": "There is not enough supplier data for {name}.",
        "selling": "Sell {name} at about {r} (range {lo} to {hi}), margin about {m}%.",
        "no_selling": "I cannot work out a selling price for {name} yet (no cost or market price).",
        "alerts": "You have {n} unread alert(s).",
        "no_alerts": "You have no unread alerts.",
        "overview_head": "Here is what needs attention today:",
        "overview_item": "{name}: {action}{qty}.",
        "overview_low": "Low stock: {names}.",
        "overview_over": "Paying too much for: {names}.",
        "overview_none": "Nothing urgent right now.",
        "not_found": "Sorry, I could not find that product in your shop. Your products are: {names}.",
        "missing": "Some information is not available yet.",
        "basic": "Basic answer (AI is offline).",
    },
    "hi": {
        "buy_now": "अभी खरीदें: {name} {qty} {unit} मंगवाएं।",
        "limited": "थोड़ा ही खरीदें: {name} {qty} {unit}।",
        "wait": "{name} खरीदने के लिए {days} दिन रुकें।",
        "wait_plain": "अभी {name} खरीदने की ज़रूरत नहीं है।",
        "stock": "{name} का स्टॉक: {stock} {unit}, लगभग {days} दिन चलेगा।",
        "stock_nodays": "{name} का स्टॉक: {stock} {unit}।",
        "fair": "{name}: आपका पिछला भाव {p} था, बाज़ार भाव {m} ({v:+.1f}%): {verdict}।",
        "fair_nomarket": "{name}: आपका पिछला भाव {p} था। तुलना के लिए बाज़ार भाव उपलब्ध नहीं है।",
        "no_purchase": "{name}: अभी तक कोई खरीद दर्ज नहीं है।",
        "forecast": "{name} का भाव अनुमान: अभी {now}, 7 दिन में {f7} ({chg:+.1f}%, {direction})।",
        "no_forecast": "{name} के लिए भाव अनुमान उपलब्ध नहीं है।",
        "estimate": "अनुमान सिर्फ़ अंदाज़ा है, गारंटी नहीं।",
        "supplier": "{name} के लिए सबसे अच्छा सप्लायर: {s} (औसत {p})।",
        "no_supplier": "{name} के लिए सप्लायर का डेटा काफ़ी नहीं है।",
        "selling": "{name} को लगभग {r} पर बेचें (रेंज {lo} से {hi}), मार्जिन लगभग {m}%।",
        "no_selling": "{name} का बिक्री भाव अभी तय नहीं हो सकता (लागत या बाज़ार भाव नहीं है)।",
        "alerts": "आपके {n} अलर्ट अभी देखे नहीं गए हैं।",
        "no_alerts": "कोई नया अलर्ट नहीं है।",
        "overview_head": "आज इन पर ध्यान दें:",
        "overview_item": "{name}: {action}{qty}।",
        "overview_low": "कम स्टॉक: {names}।",
        "overview_over": "ज़्यादा दाम दे रहे हैं: {names}।",
        "overview_none": "अभी कुछ ज़रूरी नहीं है।",
        "not_found": "माफ़ कीजिए, यह प्रोडक्ट आपकी दुकान में नहीं मिला। आपके प्रोडक्ट: {names}।",
        "missing": "कुछ जानकारी अभी उपलब्ध नहीं है।",
        "basic": "सामान्य जवाब (AI बंद है)।",
    },
    "mr": {
        "buy_now": "आत्ताच खरेदी करा: {name} {qty} {unit} मागवा.",
        "limited": "थोडेच खरेदी करा: {name} {qty} {unit}.",
        "wait": "{name} खरेदीसाठी {days} दिवस थांबा.",
        "wait_plain": "आत्ता {name} खरेदी करण्याची गरज नाही.",
        "stock": "{name} चा साठा: {stock} {unit}, सुमारे {days} दिवस पुरेल.",
        "stock_nodays": "{name} चा साठा: {stock} {unit}.",
        "fair": "{name}: तुमचा मागील भाव {p} होता, बाजारभाव {m} ({v:+.1f}%): {verdict}.",
        "fair_nomarket": "{name}: तुमचा मागील भाव {p} होता. तुलनेसाठी बाजारभाव उपलब्ध नाही.",
        "no_purchase": "{name}: अजून कोणतीही खरेदी नोंदलेली नाही.",
        "forecast": "{name} भाव अंदाज: आत्ता {now}, 7 दिवसांत {f7} ({chg:+.1f}%, {direction}).",
        "no_forecast": "{name} साठी भाव अंदाज उपलब्ध नाही.",
        "estimate": "अंदाज हा फक्त अंदाज आहे, खात्री नाही.",
        "supplier": "{name} साठी सर्वोत्तम पुरवठादार: {s} (सरासरी {p}).",
        "no_supplier": "{name} साठी पुरवठादाराची माहिती पुरेशी नाही.",
        "selling": "{name} सुमारे {r} ला विका (श्रेणी {lo} ते {hi}), मार्जिन सुमारे {m}%.",
        "no_selling": "{name} चा विक्री भाव अजून ठरवता येत नाही (खरेदी किंमत किंवा बाजारभाव नाही).",
        "alerts": "तुमचे {n} अलर्ट अजून पाहिलेले नाहीत.",
        "no_alerts": "कोणताही नवीन अलर्ट नाही.",
        "overview_head": "आज या गोष्टींकडे लक्ष द्या:",
        "overview_item": "{name}: {action}{qty}.",
        "overview_low": "कमी साठा: {names}.",
        "overview_over": "जास्त भाव देत आहात: {names}.",
        "overview_none": "सध्या काहीही तातडीचे नाही.",
        "not_found": "क्षमस्व, हे उत्पादन तुमच्या दुकानात सापडले नाही. तुमची उत्पादने: {names}.",
        "missing": "काही माहिती अजून उपलब्ध नाही.",
        "basic": "साधे उत्तर (AI बंद आहे).",
    },
}


def _g(x) -> str:
    return f"{x:g}"


def _rs(x, unit=None) -> str:
    return f"₹{x:g}" + (f"/{unit}" if unit else "")


def not_found_answer(product_names: list[str], language: str) -> str:
    t = T.get(language, T["en"])
    return t["not_found"].format(names=", ".join(product_names) if product_names else "-")


def _product_lines(p: dict, topics: set[str], t: dict, lang: str) -> list[str]:
    name, unit = p["name"], p["unit"]
    fp, fc, rec, sp = p["fairPrice"], p["forecast"], p["purchaseRecommendation"], p["sellingPrice"]
    general = "general" in topics or "buy_decision" in topics
    lines: list[str] = []

    if general:
        q = _g(rec["quantity"]) if rec["quantity"] else ""
        if rec["action"] == "Buy Now":
            lines.append(t["buy_now"].format(name=name, qty=q, unit=unit))
        elif rec["action"] == "Buy Limited":
            lines.append(t["limited"].format(name=name, qty=q, unit=unit))
        elif rec["checkAgainInDays"]:
            lines.append(t["wait"].format(name=name, days=rec["checkAgainInDays"]))
        else:
            lines.append(t["wait_plain"].format(name=name))
    if general or "stock" in topics:
        if p["daysOfStockLeft"] is not None:
            lines.append(t["stock"].format(name=name, stock=_g(p["stock"]), unit=unit, days=_g(p["daysOfStockLeft"])))
        else:
            lines.append(t["stock_nodays"].format(name=name, stock=_g(p["stock"]), unit=unit))
    if general or "price_fairness" in topics:
        if fp["lastPurchasePrice"] is None:
            lines.append(t["no_purchase"].format(name=name))
        elif fp["marketPrice"] is None or fp["variancePct"] is None:
            lines.append(t["fair_nomarket"].format(name=name, p=_rs(fp["lastPurchasePrice"], unit)))
        else:
            lines.append(t["fair"].format(name=name, p=_rs(fp["lastPurchasePrice"], unit), m=_rs(fp["marketPrice"], unit), v=fp["variancePct"],
                                          verdict=VERDICT[lang][fp["verdict"]]))
    if general or "forecast" in topics:
        if fc:
            lines.append(t["forecast"].format(name=name, now=_rs(fc["priceNow"]), f7=_rs(fc["priceIn7Days"]), chg=fc["changePct"],
                                              direction=DIRECTION[lang][fc["direction"]]))
            lines.append(t["estimate"])
        else:
            lines.append(t["no_forecast"].format(name=name))
    if "supplier" in topics:
        best = next((s for s in p["suppliers"] if s["bestValue"]), None) or (p["suppliers"][0] if p["suppliers"] else None)
        lines.append(t["supplier"].format(name=name, s=best["supplier"], p=_rs(best["avgPrice"], unit)) if best else t["no_supplier"].format(name=name))
    if "selling_price" in topics:
        if sp["recommended"] is None:
            lines.append(t["no_selling"].format(name=name))
        else:
            lines.append(t["selling"].format(name=name, r=_rs(sp["recommended"], unit), lo=_rs(sp["rangeLow"]), hi=_rs(sp["rangeHigh"]),
                                             m=_g(sp["expectedMarginPct"]) if sp["expectedMarginPct"] is not None else "-"))
    if "alerts" in topics:
        n = len(p["unreadAlerts"])
        lines.append(t["alerts"].format(n=n) if n else t["no_alerts"])
    return lines


def fallback_answer(context: dict, topics: set[str], language: str) -> str:
    lang = language if language in T else "en"
    t = T[lang]
    lines: list[str] = []

    if context.get("products"):
        for p in context["products"][:2]:                      # keep the offline answer short
            lines += _product_lines(p, topics, t, lang)
    else:
        ov = context["overview"]
        if "alerts" in topics and ov["unreadAlerts"] is not None and topics <= {"alerts"}:
            n = len(ov["unreadAlerts"])
            lines.append(t["alerts"].format(n=n) if n else t["no_alerts"])
        else:
            items = ov["topRecommendations"]
            urgent = [r for r in items if r["action"] != "Wait"]
            if urgent or ov["lowStock"] or ov["overpayingProducts"]:
                lines.append(t["overview_head"])
                for r in urgent:
                    qty = f" {_g(r['quantity'])} {r['unit']}" if r["quantity"] else ""
                    lines.append(t["overview_item"].format(name=r["product"], action=ACTION[lang][r["action"]], qty=qty if lang == "en" else qty))
                if ov["lowStock"]:
                    lines.append(t["overview_low"].format(names=", ".join(x["name"] for x in ov["lowStock"])))
                if ov["overpayingProducts"]:
                    lines.append(t["overview_over"].format(names=", ".join(ov["overpayingProducts"])))
            else:
                lines.append(t["overview_none"])

    # the "some information is missing" note only matters when the answer used prices, forecasts or advice
    if context.get("missing") and topics & {"general", "buy_decision", "forecast", "price_fairness", "selling_price"}:
        lines.append(t["missing"])
    lines.append(t["basic"])
    return "\n".join(lines)


REFUSAL = {
    "en": "Sorry, I cannot give medical or legal advice. I can help you with buying, prices and stock for your shop.",
    "hi": "माफ़ कीजिए, मैं स्वास्थ्य या कानूनी सलाह नहीं दे सकता। मैं आपकी दुकान की खरीद, भाव और स्टॉक में मदद कर सकता हूं।",
    "mr": "क्षमस्व, मी वैद्यकीय किंवा कायदेशीर सल्ला देऊ शकत नाही. मी तुमच्या दुकानाची खरेदी, भाव आणि साठा यामध्ये मदत करू शकतो.",
}
HORIZON_NOTE = {
    "en": "I can only forecast prices for the next 7 to 14 days, not for a longer time.",
    "hi": "मैं सिर्फ़ अगले 7 से 14 दिनों का भाव अनुमान बता सकता हूं, इससे लंबे समय का नहीं।",
    "mr": "मी फक्त पुढील 7 ते 14 दिवसांचा भाव अंदाज सांगू शकतो, त्यापेक्षा जास्त काळाचा नाही.",
}


def refusal_answer(language: str) -> str:
    return REFUSAL.get(language, REFUSAL["en"])


def horizon_note(language: str) -> str:
    return HORIZON_NOTE.get(language, HORIZON_NOTE["en"])
