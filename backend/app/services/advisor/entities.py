"""
advisor/entities.py - understand WHAT the shopkeeper is asking about.

  match_products(message, products)  -> which of the shop's products are mentioned (English / Hindi / Marathi)
  detect_topics(message)             -> what they want to know (price fairness, buy decision, forecast ...)

No AI is used here: it is plain dictionary lookup, so it is fast, free and easy to explain.

TO ADD A NEW NAME FOR A PRODUCT: add it to the right list in PRODUCT_ALIASES below (any script, any spelling).
TO SUPPORT A NEW PRODUCT: add a new group {"key": [aliases...]}. A product belongs to a group when the group key
appears in the product's name (e.g. key "oil" matches "Soyabean Oil" and "Mustard Oil") or when the product's
own name is one of the aliases.

HOW WORDS ARE COMPARED
  * lower-cased, Latin accents removed (café -> cafe); Devanagari letters are kept intact
  * chandrabindu and anusvara are treated as the same (गेहूँ = गेहूं), nukta variants are folded
  * Latin aliases must match a WHOLE word (so "rice" is not found inside "price", "tel" not inside "hotel")
  * Devanagari aliases may match the START of a word, because Hindi and Marathi add endings: तांदळाचा starts with तांदळ
"""
import re
import unicodedata

# group key -> aliases. Latin spellings are lower case. Devanagari stems are given where the word changes with endings.
PRODUCT_ALIASES: dict[str, list[str]] = {
    "rice": ["rice", "chawal", "chaawal", "chawl", "tandul", "tandool", "bhat", "चावल", "तांदूळ", "तांदळ", "भात"],
    "wheat atta": ["atta", "aata", "wheat flour", "wheat", "gehu", "gehun", "gahu", "gehu ka atta", "peeth", "pith",
                   "आटा", "गेहूं", "गेहू", "गहू", "गव्हाचे पीठ", "गव्हाच", "पीठ"],
    "sugar": ["sugar", "cheeni", "chini", "shakkar", "shakar", "sakhar", "साखर", "चीनी", "शक्कर", "चिनी"],
    "toor dal": ["toor dal", "tur dal", "toor", "tuar dal", "arhar", "arhar dal", "tur", "तूर दाल", "तूर डाळ", "तुर डाळ", "तूर", "अरहर", "तुर"],
    "moong dal": ["moong dal", "mung dal", "moong", "mung", "मूग डाळ", "मूंग दाल", "मूंग", "मूग"],
    "chana": ["chana", "chickpea", "harbhara", "चना", "हरभरा"],
    "oil": ["oil", "tel", "teil", "tail", "तेल"],
    "soyabean oil": ["soyabean oil", "soybean oil", "soya oil", "soyabean", "soybean", "सोयाबीन तेल", "सोयाबीन"],
    "mustard oil": ["mustard oil", "sarson ka tel", "sarso tel", "mustard", "sarson", "सरसों का तेल", "सरसों", "मोहरी"],
    "salt": ["salt", "namak", "meeth", "mith", "mitha", "नमक", "मीठ"],
    "onion": ["onion", "pyaz", "pyaaj", "kanda", "kaanda", "प्याज", "प्याज़", "कांदा", "कांद्य", "कांदे"],
    "potato": ["potato", "aloo", "alu", "batata", "bataata", "आलू", "बटाटा", "बटाट"],
    "tomato": ["tomato", "tamatar", "tamatar", "tomatar", "टमाटर", "टोमॅटो", "टोमाटो"],
    "milk": ["milk", "doodh", "dudh", "dud", "दूध", "दुध"],
    "tea": ["tea", "chai", "chaha", "चाय", "चहा"],
    "paneer": ["paneer", "पनीर"],
}

# topic -> keywords (English, Hindi/Marathi in Devanagari, and Latin transliteration)
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "price_fairness": ["fair", "overpay", "overpaying", "overcharg", "too high", "too much", "expensive", "cheap", "paid", "worth",
                       "good price", "fair price", "market price", "pricey", "rate", "price", "prices",
                       "sahi bhav", "sahi daam", "mehenga", "mehnga", "mahag", "mahaag", "jyada", "zyada", "jast", "vajvi", "bhav theek",
                       "वाजवी", "महाग", "महंगा", "ज्यादा", "सही भाव", "सही दाम", "भाव ठीक", "भाव", "दाम", "किमत", "किंमत", "भावात"],
    "buy_decision": ["buy", "order", "purchase", "stock up", "restock", "reorder", "when to", "wait", "kharid", "kharidu",
                     "kharedi", "kharid karu", "kharidna", "lena", "lu", "ghyaycha", "ghyava", "thamb",
                     "खरीद", "खरेदी", "खरीदूं", "खरीदना", "लेना", "मंगाना", "मागवू", "घ्यावा", "घ्यायचा", "थांब", "रुक"],
    "forecast": ["forecast", "predict", "will the price", "next week", "next days", "going up", "go up", "go down", "increase", "decrease",
                 "rise", "fall", "trend", "future", "tomorrow", "badhega", "badhel", "vadhel", "vadhnar", "kam hoga", "kami hoil", "utarega",
                 "बढ़ेगा", "बढेगा", "वाढेल", "वाढणार", "कमी होईल", "कम होगा", "अनुमान", "पुढच्या आठवड्यात", "अगले हफ्ते", "आगे", "उतरेल"],
    "stock": ["stock", "inventory", "left", "remaining", "how much", "run out", "running out", "enough", "days of",
              "kitna bacha", "kitna hai", "shillak", "saatha", "satha", "bacha",
              "स्टॉक", "साठा", "शिल्लक", "बचा", "कितना", "किती", "बाकी"],
    "supplier": ["supplier", "vendor", "cheapest supplier", "which supplier", "wholesaler", "dealer",
                 "सप्लायर", "पुरवठादार", "सप्लाई", "विक्रेता", "व्यापारी", "सबसे सस्ता", "सर्वात स्वस्त", "सस्ता", "स्वस्त", "sasta", "swast"],
    "selling_price": ["selling price", "sell at", "sell for", "margin", "profit", "mrp", "retail price", "what price should i sell",
                      "bechna", "bechu", "vikri", "vikri bhav", "nafa", "fayda", "phayda",
                      "बेचना", "बेचूं", "विक्री", "विकू", "नफा", "फायदा", "मार्जिन", "मुनाफा", "भाव ठेवू", "कितने में बेचू", "किती ला विकू"],
    "alerts": ["alert", "warning", "unusual", "abnormal", "notification", "suspicious", "ishara", "suchana",
               "अलर्ट", "सूचना", "इशारा", "चेतावनी", "असामान्य"],
}

# words that signal a question about the whole shop (not one product)
OVERVIEW_WORDS = ["today", "everything", "overall", "all products", "all items", "my shop", "my store", "whole shop", "this week",
                  "what should i buy", "which products", "what to buy", "summary", "overview", "aaj", "sab", "sabhi", "sarv", "saglya",
                  "आज", "सब", "सभी", "सर्व", "सगळ्या", "दुकान", "दुकानात"]

PRODUCT_TOPICS = {"price_fairness", "forecast", "stock", "supplier", "selling_price", "buy_decision"}


# ---------------------------------------------------------------- normalisation
def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or unicodedata.category(ch) in ("Mn", "Mc") or ch == "'"


def normalize(text: str) -> str:
    """Lower-case, strip LATIN accents only, fold Devanagari variants, keep letters and spaces."""
    text = unicodedata.normalize("NFC", text).casefold()
    out = []
    for ch in unicodedata.normalize("NFKD", text):
        if unicodedata.category(ch) == "Mn" and out and out[-1].isascii():
            continue                                               # an accent on a Latin letter
        out.append(ch)
    text = unicodedata.normalize("NFC", "".join(out))
    text = text.replace("ँ", "ं").replace("़", "")                  # chandrabindu -> anusvara, drop nukta
    text = re.sub(r"[“”\"'`’]", "", text)
    return text


def tokenize(text: str) -> list[str]:
    tokens, cur = [], []
    for ch in normalize(text):
        if _is_word_char(ch):
            cur.append(ch)
        elif cur:
            tokens.append("".join(cur)); cur = []
    if cur:
        tokens.append("".join(cur))
    return tokens


def _is_devanagari(s: str) -> bool:
    return any("\u0900" <= c <= "\u097f" for c in s)


def _token_matches(alias_token: str, token: str) -> bool:
    """Latin alias = the whole word (or its plural). Devanagari alias = the word may continue (Hindi/Marathi endings)."""
    if _is_devanagari(alias_token):
        return len(alias_token) >= 2 and token.startswith(alias_token)
    return token in (alias_token, alias_token + "s", alias_token + "es")


def _find_phrase(phrase: str, tokens: list[str]) -> int | None:
    """Index of the first token where the (one or more word) phrase starts, else None."""
    a_tokens = tokenize(phrase)
    n = len(a_tokens)
    if n == 0:
        return None
    for i in range(len(tokens) - n + 1):
        if all(_token_matches(a, t) for a, t in zip(a_tokens, tokens[i:i + n])):
            return i
    return None


GENERIC_GROUPS = {"oil"}          # words like "oil" / "tel" fit every oil product, so a specific oil name wins over them


def _groups_for(product_name: str) -> list[str]:
    """Alias groups that belong to a product name."""
    name = normalize(product_name)
    return [key for key, aliases in PRODUCT_ALIASES.items() if key in name or any(normalize(a) == name for a in aliases)]


def match_products(message: str, products: list) -> list:
    """
    Products mentioned in the message (Product rows with .id and .name), in the order they are mentioned.
    The product's own name always counts too, whatever language the shop typed it in.
    """
    tokens = tokenize(message)
    hits: list[tuple[int, bool, object]] = []                 # (position, matched by a specific alias?, product)
    for p in products:
        specific_pos, generic_pos = None, None
        specific_phrases = [p.name] + [a for g in _groups_for(p.name) if g not in GENERIC_GROUPS for a in PRODUCT_ALIASES[g]]
        generic_phrases = [a for g in _groups_for(p.name) if g in GENERIC_GROUPS for a in PRODUCT_ALIASES[g]]
        for phrase in specific_phrases:
            i = _find_phrase(phrase, tokens)
            if i is not None:
                specific_pos = i if specific_pos is None else min(specific_pos, i)
        for phrase in generic_phrases:
            i = _find_phrase(phrase, tokens)
            if i is not None:
                generic_pos = i if generic_pos is None else min(generic_pos, i)
        if specific_pos is not None:
            hits.append((specific_pos, True, p))
        elif generic_pos is not None:
            hits.append((generic_pos, False, p))
    if any(is_specific for _, is_specific, _ in hits):        # "soyabean oil price": do not also return Mustard Oil
        hits = [h for h in hits if h[1]]
    hits.sort(key=lambda h: h[0])
    return [p for _, _, p in hits]


# ---------------------------------------------------------------- topics
def detect_topics(message: str) -> set[str]:
    norm = normalize(message)
    tokens = tokenize(message)
    topics = set()
    for topic, words in TOPIC_KEYWORDS.items():
        for w in words:
            wn = normalize(w)
            if " " in wn:
                if wn in norm:                                  # multi-word phrase
                    topics.add(topic); break
            elif _is_devanagari(wn):
                if any(t.startswith(wn) for t in tokens):
                    topics.add(topic); break
            else:
                if wn in tokens or (len(wn) >= 5 and any(t.startswith(wn) for t in tokens)):
                    topics.add(topic); break
    # a question about the SELLING price is not a question about the purchase price
    if "selling_price" in topics and "price_fairness" in topics and not any(w in norm for w in ("fair", "overpay", "paid", "supplier")):
        topics.discard("price_fairness")
    return topics or {"general"}


def is_overview_question(message: str) -> bool:
    norm = normalize(message)
    tokens = tokenize(message)
    for w in OVERVIEW_WORDS:
        wn = normalize(w)
        if " " in wn:
            if wn in norm:
                return True
        elif _is_devanagari(wn):
            if any(t.startswith(wn) for t in tokens):
                return True
        elif wn in tokens:
            return True
    return False
