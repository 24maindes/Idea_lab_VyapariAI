// Browser-like smoke test of the REAL React app against a RUNNING backend (jsdom, no real browser needed).
//   1. start the backend with the demo data      2. npm run test:smoke
// It logs in as the demo user, opens every page and checks the key texts, asks the advisor a question,
// opens the CSV import window, and checks the "session expired" flow and logout.
import "./jsdom-setup.mjs";
import React, { act } from "react";
import { createRoot } from "react-dom/client";
import App from "../../src/App.jsx";

const dom = globalThis.__dom;
const wait = (ms) => act(async () => { await new Promise((r) => setTimeout(r, ms)); });
const text = () => document.body.textContent.replace(/\s+/g, " ");
const here = () => dom.window.location.pathname;
let failures = 0;
const check = (ok, name, extra = "") => { if (!ok) failures += 1; console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  -> " + extra : ""}`); };
const setInput = (el, v) => { Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set.call(el, v); el.dispatchEvent(new window.Event("input", { bubbles: true })); };
const submit = (form) => form.dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));

let root;
async function boot(path, token) {
  if (root) await act(async () => root.unmount());
  localStorage.clear(); sessionStorage.clear();
  if (token) localStorage.setItem("vyapariToken", token);
  dom.window.history.pushState({}, "", path);
  document.body.innerHTML = '<div id="root"></div>';
  root = createRoot(document.getElementById("root"));
  await act(async () => { root.render(React.createElement(App)); });
  await wait(900);
}
// poll until every needle is on the page (the simulated browser is slow when the machine is busy), at most `limit` ms
const waitFor = async (needles, limit = 15000) => {
  const start = Date.now();
  while (Date.now() - start < limit) {
    if (needles.every((n) => text().includes(n))) return true;
    await wait(300);
  }
  return false;
};
const go = async (path, ms = 1800) => {
  await act(async () => { dom.window.history.pushState({}, "", path); dom.window.dispatchEvent(new dom.window.PopStateEvent("popstate")); });
  await wait(ms);
};

// 1. logged out
await boot("/dashboard");
check(here() === "/login", "logged out /dashboard goes to /login", here());

// 2. real login through the page
const ins = document.querySelectorAll("input");
await act(async () => { setInput(ins[0], "demo@vyapariai.com"); setInput(ins[1], "demo1234"); });
await act(async () => { submit(document.querySelector("form")); });
await wait(2500);
check(here() === "/dashboard", "demo login lands on the dashboard", here());
check(text().includes("Sharma General Store"), "shop name from the API is shown");
const token = localStorage.getItem("vyapariToken");

// 3. every page
const PAGES = [
  ["/dashboard", ["Total Products", "What to buy", "Recent Activity", "Price Trend"]],
  ["/products", ["Add Product", "Toor Dal", "Import CSV"]],
  ["/suppliers", ["ABC Traders", "Add Supplier", "Compare"]],
  ["/purchases", ["New Purchase", "Recent Purchases", "Import CSV"]],
  ["/sales", ["Record Sale", "Today's Sales", "Last 30 days"]],
  ["/inventory", ["Total stock value", "Days of cover"]],
  ["/price-analysis", ["All Products", "Your Last Price", "Potential Savings"]],
  ["/forecast", ["Price history and forecast", "Model comparison", "Retrain models"]],
  ["/alerts", ["Scan now", "Mark all read"]],
  ["/recommendations", ["What to buy", "Buy"]],
  ["/advisor", ["AI Business Advisor"]],
  ["/settings", ["Business rules", "Change password"]],
];
for (const [path, needles] of PAGES) {
  await go(path, 300);
  await waitFor(needles);
  const t = text();
  const missing = needles.filter((n) => !t.includes(n));
  check(here() === path && missing.length === 0 && !t.includes("Something went wrong"), `page ${path}`, missing.length ? "missing: " + missing.join(", ") + " | page text: " + t.slice(0, 260) : t.includes("Something went wrong") ? "error box shown" : "");
}

// 4. sidebar badge and alerts
check(!!document.querySelector('aside a[href="/alerts"] span[aria-label]'), "sidebar shows the unread alerts badge");

// 5. suppliers compare tab
await go("/suppliers");
await act(async () => { [...document.querySelectorAll("button")].find((b) => b.textContent === "Compare").click(); });
check(await waitFor(["Average price by supplier"]), "supplier comparison tab loads");

// 6. recommendations: selling price tab
await go("/recommendations");
await act(async () => { [...document.querySelectorAll("button")].find((b) => b.textContent === "What to sell at").click(); });
check(await waitFor(["Recommended range", "Target margin"]), "recommendations: selling-price tab");

// 7. advisor chat (offline fallback unless the server has a Gemini key)
await go("/advisor", 1200);
const box = document.querySelector('input[maxlength="1000"]');
await act(async () => { setInput(box, "Is the price I paid for rice fair?"); });
await act(async () => { submit(document.querySelector("form")); });
check(await waitFor(["Sources used"]) && text().includes("Is the price I paid for rice fair?"), "advisor answers with sources", /Basic answer/.test(text()) ? "(offline fallback)" : "(AI)");

// 8. CSV import window
await go("/purchases", 1200);
await act(async () => { [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Import CSV")).click(); });
check(await waitFor(["Import purchases from CSV", "Check file"], 5000), "CSV import window opens");

// 9. logout then session-expired flow
await boot("/dashboard", token);
await act(async () => { document.querySelector('button[title="Log out"]').click(); });
await wait(400);
check(here() === "/login" && !localStorage.getItem("vyapariToken"), "logout returns to /login and clears the token");
await boot("/dashboard", "garbage.token.value");
check(here() === "/login", "invalid token ends on /login", here());
check(text().includes("Session expired"), "login page explains: session expired");

console.log(failures === 0 ? "\nALL SMOKE CHECKS PASSED" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
