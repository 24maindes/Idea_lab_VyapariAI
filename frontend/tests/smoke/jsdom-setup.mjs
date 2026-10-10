// must be imported FIRST: React DOM checks for a browser at import time
import { JSDOM } from "jsdom";
const dom = new JSDOM('<!doctype html><div id="host"></div>', { url: "http://localhost:5173/", pretendToBeVisual: true });
Object.assign(globalThis, {
  window: dom.window, document: dom.window.document, localStorage: dom.window.localStorage, sessionStorage: dom.window.sessionStorage,
  HTMLElement: dom.window.HTMLElement, SVGElement: dom.window.SVGElement, Node: dom.window.Node,
  getComputedStyle: dom.window.getComputedStyle, MutationObserver: dom.window.MutationObserver,
});
Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
globalThis.ResizeObserver = class { observe(){} unobserve(){} disconnect(){} };
globalThis.__dom = dom;

// jsdom has no layout engine: provide the few browser functions the app calls
dom.window.HTMLElement.prototype.scrollIntoView = function () {};
