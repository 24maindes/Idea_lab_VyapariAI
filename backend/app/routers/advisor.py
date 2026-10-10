"""
routers/advisor.py - the AI Business Advisor (RAG).

POST   /api/advisor/chat        {message, language, productId?} -> {answer, language, usedFallback, grounded, sources, matchedProducts}
GET    /api/advisor/history     ?limit=30
DELETE /api/advisor/history

THE PIPELINE (also the text for the report):
 0. GUARDS      message length (max 500 characters), per-user rate limit (20 / minute), medical or legal questions are refused.
 1. UNDERSTAND  entities.py finds which products and which topics the question is about (English / Hindi / Marathi).
 2. RETRIEVE    retrieval.py runs structured SQL/Pandas based services on THIS shop's data (cached 60 seconds).
 3. AUGMENT     prompt.py puts those real numbers (compact JSON) and strict rules into the prompt.
 4. GENERATE    gemini_client.py asks Gemini (temperature 0.2) to answer ONLY from that context, in the chosen language.
 5. CHECK       grounding.py: every price-like number in the answer must exist in the context (1 % tolerance).
                If not: ask once more with a stricter instruction; if still wrong: use the offline answer.
 6. FALL BACK   if Gemini is unavailable, fallback.py builds a basic template answer from the same numbers.
 7. EXPLAIN     the answer is returned with "sources": the exact facts used, so the shopkeeper can check them.
"""
import logging
import statistics
import time
from collections import deque
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_shop
from app.models import AdvisorMessage, Product, Shop
from app.routers.auth import get_current_user
from app.schemas import CamelModel
from app.services.advisor import entities, fallback, gemini_client, grounding, prompt, retrieval
from app.services.cache import get_or_set
from app.services.rate_limit import SlidingWindowLimiter

router = APIRouter(prefix="/api/advisor", tags=["advisor"])
log = logging.getLogger("vyapari.advisor")

MAX_MESSAGE_CHARS = 500
RATE_LIMIT = SlidingWindowLimiter(max_calls=20, window_seconds=60)
SLOW_SECONDS = 8.0                       # if the MEDIAN of the last 20 answers is slower than this, send smaller contexts
_timings: deque = deque(maxlen=20)
STRICT_SUFFIX = ("\n\nSTRICT MODE: your previous answer contained price numbers that are not in the CONTEXT ({bad}). "
                 "Answer again. Use ONLY numbers that appear in the CONTEXT. If you are not sure about a price, do not mention a price.")


class ChatRequest(CamelModel):
    message: str = Field(min_length=1)                       # length is checked below so the error message is friendly
    language: Literal["en", "hi", "mr"] | None = None
    product_id: int | None = None


def _lean() -> bool:
    return len(_timings) >= 5 and statistics.median(_timings) > SLOW_SECONDS


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop), user=Depends(get_current_user)):
    started = time.perf_counter()

    # ---- 0. guards
    message = grounding.sanitize(payload.message, limit=10_000)
    if not message:
        raise HTTPException(status_code=422, detail="Please type a question")
    if len(message) > MAX_MESSAGE_CHARS:
        raise HTTPException(status_code=422, detail=f"Please keep your question under {MAX_MESSAGE_CHARS} characters (you wrote {len(message)}).")
    allowed, retry = RATE_LIMIT.check(user.id)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many questions. Please wait {retry} seconds and try again.")

    language = payload.language or shop.language or "en"
    if language not in ("en", "hi", "mr"):
        language = "en"

    products = db.execute(select(Product).where(Product.shop_id == shop.id).order_by(Product.name)).scalars().all()
    if payload.product_id is not None and not any(p.id == payload.product_id for p in products):
        raise HTTPException(status_code=404, detail="Product not found")

    answer, used_fallback, grounded, sources, matched = None, False, True, [], []

    if grounding.is_out_of_scope(message):                    # medical / legal: refuse without calling the AI
        answer = fallback.refusal_answer(language)
    else:
        # ---- 1. understand
        matched = entities.match_products(message, products)
        if payload.product_id is not None:
            chosen = next(p for p in products if p.id == payload.product_id)
            matched = [chosen] + [p for p in matched if p.id != chosen.id]
        topics = entities.detect_topics(message)

        history = db.execute(select(AdvisorMessage).where(AdvisorMessage.shop_id == shop.id).order_by(AdvisorMessage.id.desc()).limit(4)).scalars().all()
        history_msgs = [{"role": m.role, "content": grounding.sanitize(m.content, 600)} for m in reversed(history)]

        if not matched and not entities.is_overview_question(message):       # follow-up such as "and the price?"
            for m in reversed(history_msgs):
                if m["role"] == "user":
                    matched = entities.match_products(m["content"], products)
                    if matched:
                        break

        asks_about_product = topics & entities.PRODUCT_TOPICS
        if not matched and asks_about_product and not entities.is_overview_question(message):
            answer = fallback.not_found_answer([p.name for p in products], language)
        else:
            # ---- 2. retrieve (cached for 60 seconds per shop, products and topics)
            t0 = time.perf_counter()
            beyond = grounding.asks_beyond_horizon(message)
            notes = ["The user asks about a period longer than 14 days. Explain that forecasts exist only for 7-14 days, then give the 7-day forecast."] if beyond else []
            lean = _lean()
            key = ("advisor-ctx", tuple(p.id for p in matched), tuple(sorted(topics)), lean, beyond)
            context = get_or_set(shop.id, key, 60, lambda: retrieval.build_context(db, shop, matched, topics, lean=lean, notes=notes))
            sources = retrieval.sources_from_context(context, topics)
            t_retrieve = time.perf_counter() - t0

            # ---- 3-5. generate + check
            t1 = time.perf_counter()
            try:
                system, contents = prompt.build_messages(context, grounding.sanitize(message, MAX_MESSAGE_CHARS), language, history_msgs)
                answer = gemini_client.generate(system, contents)
                bad = grounding.ungrounded_numbers(answer, context)
                if bad:
                    grounding.log_failure(message, answer, bad, attempt=1, final=False)
                    answer = gemini_client.generate(system + STRICT_SUFFIX.format(bad=", ".join(f"{b:g}" for b in bad)), contents)
                    bad = grounding.ungrounded_numbers(answer, context)
                    if bad:                                                   # still not grounded -> never show it
                        grounding.log_failure(message, answer, bad, attempt=2, final=True)
                        answer, used_fallback, grounded = fallback.fallback_answer(context, topics, language), True, False
            except gemini_client.AdvisorUnavailable as e:
                log.warning("Advisor fallback used: %s", e)
                answer, used_fallback = fallback.fallback_answer(context, topics, language), True
            t_llm = time.perf_counter() - t1
            if beyond and used_fallback:
                answer = fallback.horizon_note(language) + "\n" + answer

            total = time.perf_counter() - started
            if not used_fallback:
                _timings.append(total)                        # only real AI answers say something about AI speed
            log.info("advisor timing: retrieve=%.0fms llm=%.0fms total=%.0fms fallback=%s lean=%s", t_retrieve * 1000, t_llm * 1000, total * 1000, used_fallback, lean)

    db.add(AdvisorMessage(shop_id=shop.id, role="user", content=message[:MAX_MESSAGE_CHARS], language=language))
    db.add(AdvisorMessage(shop_id=shop.id, role="assistant", content=answer, language=language))
    db.commit()
    return {"answer": answer, "language": language, "usedFallback": used_fallback, "grounded": grounded, "sources": sources,
            "matchedProducts": [{"id": p.id, "name": p.name} for p in matched]}


@router.get("/history")
def history(limit: int = Query(30, ge=1, le=200), db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    rows = db.execute(select(AdvisorMessage).where(AdvisorMessage.shop_id == shop.id)
                      .order_by(AdvisorMessage.id.desc()).limit(limit)).scalars().all()
    return [{"id": m.id, "role": m.role, "content": m.content, "language": m.language,
             "createdAt": m.created_at.isoformat() if m.created_at else None} for m in reversed(rows)]     # oldest first


@router.delete("/history", status_code=204)
def clear_history(db: Session = Depends(get_db), shop: Shop = Depends(get_current_shop)):
    db.execute(delete(AdvisorMessage).where(AdvisorMessage.shop_id == shop.id))
    db.commit()
