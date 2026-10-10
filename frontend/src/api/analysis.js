// src/api/analysis.js
// Calls to the fair-price analysis endpoints. All HTTP goes through apiFetch (token + base URL + errors).
import { apiFetch } from "./client";

// One summary row per product (dropdown + table)
export const getFairPriceSummary = () => apiFetch("/api/analysis/fair-price");

// Full detail for one product: stats, reference line, purchase dots, supplier breakdown
export const getFairPriceDetail = (productId, days = 180) =>
  apiFetch(`/api/analysis/fair-price/${productId}?days=${days}`);

// Quick check "is this price fair?"  ->  { hasMarketData, referencePrice, variancePct, verdict, message }
// Used by the purchase form (Day 3). date is optional (YYYY-MM-DD).
export const checkPrice = ({ productId, price, date }) => {
  const params = new URLSearchParams({ productId, price });
  if (date) params.set("date", date);
  return apiFetch(`/api/analysis/fair-price/check?${params.toString()}`);
};
