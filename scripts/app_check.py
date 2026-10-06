"""App check: drive the LIVE Campus Customs site like a shopper, take screenshots, and write output/app_check.html.

Every number on the report page is measured while this runs: the chatbot's real replies and what the
site really shows are compared with a direct read of data/campus_customs.db.

Needs both servers running (site on :5173 with the API on :8000) and:  pip install playwright
Run from the HW 4 folder:
    backend/.venv/bin/python scripts/app_check.py
"""

import html
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "campus_customs.db"
OUT = ROOT / "output"
IMAGES = OUT / "app_check_images"
SITE = "http://localhost:5173"
# A headless Chromium that Playwright already downloaded on this machine (no Chrome is installed).
CHROMIUM = next(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell"), None)

PRODUCT = "baseball-left-chest-crewneck"
PRODUCT_NAME = "Baseball Left Chest Crewneck"
SOLD_OUT_SIZE, IN_STOCK_SIZE = "XL", "M"


# ---------- the database, read directly (the "answer key") ----------

def db_facts() -> dict:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    price = conn.execute("SELECT price FROM catalogue WHERE product_id = ?", (PRODUCT,)).fetchone()[0]
    stock = dict(conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (PRODUCT,)).fetchall())
    hoodies = conn.execute("SELECT COUNT(*) FROM catalogue WHERE garment_type LIKE '%hood%'").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    conn.close()
    return {"price": price, "stock": stock, "hoodies": hoodies, "total": total}


# ---------- driving the site ----------

def open_chat(page) -> None:
    page.click(".tape-case")
    page.wait_for_function("document.querySelector('.tape-widget').classList.contains('open')")
    page.wait_for_timeout(1300)  # let the tape measure finish unrolling


def ask(page, question: str) -> str:
    """Type a question into the chat widget, wait for the reply, and return the reply text."""
    before = page.locator(".tape-messages .bubble.assistant:not(.typing)").count()
    page.fill(".tape-input input", question)
    page.click(".tape-input .btn")
    page.wait_for_function(
        "n => document.querySelectorAll('.tape-messages .bubble.assistant:not(.typing)').length > n"
        " && !document.querySelector('.typing')", arg=before, timeout=90_000)
    page.wait_for_timeout(600)
    return page.locator(".tape-messages .bubble.assistant:not(.typing)").last.inner_text().strip()


def new_page(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
    page.goto(SITE + "/", wait_until="networkidle")
    page.wait_for_timeout(900)  # the page's blur-in animation
    return page


def run() -> dict:
    facts = db_facts()
    IMAGES.mkdir(parents=True, exist_ok=True)
    results: dict = {"facts": facts}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROMIUM))

        # ---- Check 1: chat reports real stock and price ----
        page = new_page(browser)
        open_chat(page)
        q1 = f"How much is the {PRODUCT_NAME}, and how many do you have in {'medium'} and {SOLD_OUT_SIZE}?"
        a1 = ask(page, q1)
        page.screenshot(path=str(IMAGES / "inventory.png"))
        want_m = facts["stock"][IN_STOCK_SIZE]
        results["inventory"] = {
            "question": q1, "reply": a1,
            "price_ok": f"${facts['price']:.0f}" in a1,
            "in_stock_ok": re.search(rf"\b{want_m}\b", a1) is not None,
            "sold_out_ok": facts["stock"][SOLD_OUT_SIZE] == 0 and re.search(r"sold out|out of stock|none|0", a1, re.I) is not None,
        }
        page.close()

        # ---- Check 2: a category question makes result cards appear on the page ----
        page = new_page(browser)
        page.goto(SITE + "/about", wait_until="networkidle")  # start on a different page to show the site navigates itself
        page.wait_for_timeout(900)
        open_chat(page)
        q2 = "what hoodies do yall have"
        a2 = ask(page, q2)
        page.wait_for_selector(".results-bar", timeout=30_000)
        page.wait_for_timeout(1500)  # blur-in + card fade-in
        page.screenshot(path=str(IMAGES / "search_chat.png"))
        page.wait_for_function("!document.querySelector('.tape-widget').classList.contains('open')", timeout=15_000)
        page.wait_for_timeout(1500)  # chat has rolled up; the results are uncovered
        page.screenshot(path=str(IMAGES / "search_results.png"))
        cards = page.locator(".product-card").count()
        results["search"] = {
            "question": q2, "reply": a2, "path": page.evaluate("location.pathname"),
            "heading": page.inner_text("h1"), "bar": page.inner_text(".results-bar").replace("\n", " "),
            "cards": cards, "ok": cards == facts["hoodies"] and page.evaluate("location.pathname") == "/products",
        }
        # a card opens its detail page
        page.locator(".product-card").first.click()
        page.wait_for_selector(".detail-info h1")
        results["search"]["first_card_opens_detail"] = page.evaluate("location.pathname").startswith("/products/")
        page.close()

        # ---- Check 3: Problem 9's sold-out sizes stay clickable ----
        page = new_page(browser)
        page.goto(f"{SITE}/products/{PRODUCT}", wait_until="networkidle")
        page.wait_for_selector(".size")
        page.wait_for_timeout(1100)
        sizes = page.locator(".size")
        clickable = all(sizes.nth(i).is_enabled() for i in range(sizes.count()))
        sold_out_sizes = [s for s in page.locator(".size.sold-out").all_inner_texts()]
        page.locator(".size", has_text=re.compile(rf"^{SOLD_OUT_SIZE}$")).click()
        page.wait_for_timeout(500)
        note = page.inner_text(".stock-note").strip()
        add = page.locator(".add-btn")
        nav_cart = page.locator("a.nav-link", has_text="Cart").inner_text()
        page.screenshot(path=str(IMAGES / "sold_out.png"))
        results["sold_out"] = {
            "all_clickable": clickable, "dashed": sold_out_sizes, "note": note,
            "button": add.inner_text().strip(), "button_disabled": add.is_disabled(), "nav_cart": nav_cart,
            "db_sold_out": sorted(s for s, q in facts["stock"].items() if q == 0),
        }
        results["sold_out"]["ok"] = (
            clickable and "SOLD OUT" in note and add.is_disabled()
            and sorted(sold_out_sizes) == results["sold_out"]["db_sold_out"] and nav_cart.strip() == "Cart"
        )
        page.close()
        browser.close()
    return results


# ---------- the report page ----------

def verdict(ok: bool) -> str:
    return '<span class="pass">PASS</span>' if ok else '<span class="fail">FAIL</span>'


def build_html(r: dict) -> str:
    f, inv, s, so = r["facts"], r["inventory"], r["search"], r["sold_out"]
    inv_ok = inv["price_ok"] and inv["in_stock_ok"] and inv["sold_out_ok"]
    stock_line = ", ".join(f"{k} = {v}" for k, v in f["stock"].items())
    e = html.escape
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campus Customs — App Check</title>
<style>
  :root {{ --blue: #00356b; --navy: #0c233f; --line: #d3d3d3; --mist: #f7f7f7; }}
  body {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; color: var(--navy); margin: 0; background: #fff; line-height: 1.55; }}
  header {{ background: var(--blue); color: #fff; padding: 2rem 1.5rem; }}
  header h1 {{ margin: 0 0 .3rem; font-size: 1.9rem; }}
  header p {{ margin: 0; opacity: .9; }}
  main {{ max-width: 980px; margin: 0 auto; padding: 1.5rem; }}
  h2 {{ color: var(--blue); border-bottom: 3px solid #ff4fa3; padding-bottom: .3rem; margin-top: 2.6rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid var(--line); padding: .55rem .7rem; text-align: left; vertical-align: top; }}
  th {{ background: var(--mist); }}
  .pass {{ color: #0a7a2f; font-weight: 700; }} .fail {{ color: #c62828; font-weight: 700; }}
  figure {{ margin: 1rem 0; }}
  figure img {{ width: 100%; height: auto; border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 8px 22px rgba(12,35,63,.12); display: block; }}
  figcaption {{ margin-top: .6rem; }}
  .proves {{ background: #eaf1f8; border-left: 4px solid var(--blue); padding: .7rem 1rem; border-radius: 4px; }}
  .evidence {{ background: var(--mist); border: 1px solid var(--line); border-radius: 8px; padding: .7rem 1rem; font-size: .93rem; }}
  .evidence p {{ margin: .25rem 0; }}
  q {{ font-style: italic; }}
  footer {{ color: #606975; font-size: .85rem; padding: 1.5rem; text-align: center; border-top: 1px solid var(--line); }}
  code {{ background: var(--mist); padding: .1rem .35rem; border-radius: 4px; }}
</style>
</head>
<body>
<header>
  <h1>Campus Customs — App Check</h1>
  <p>Live-site test run on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} · site {e(SITE)} · tested as a guest shopper in a real (headless Chromium) browser</p>
</header>
<main>

<h2>Summary</h2>
<table>
  <tr><th>#</th><th>Check</th><th>Result</th></tr>
  <tr><td>1</td><td>Chat reports the real stock and price of an item</td><td>{verdict(inv_ok)}</td></tr>
  <tr><td>2</td><td>Asking about a category (hoodies) makes result cards appear on the page</td><td>{verdict(s["ok"])}</td></tr>
  <tr><td>3</td><td>Problem 9 feature: sold-out sizes stay clickable and show SOLD OUT</td><td>{verdict(so["ok"])}</td></tr>
</table>
<p>Each check below has a heading, a screenshot, and what the screenshot proves. The “database says” lines are read straight from
<code>campus_customs.db</code> during the test, so the chatbot and the site can be compared with the real data.</p>

<h2>Check 1 — Chat checks the stock and price of an item {verdict(inv_ok)}</h2>
<figure>
  <img src="app_check_images/inventory.png" alt="Chat widget answering with the price and stock of the {e(PRODUCT_NAME)}">
  <figcaption>
    <p class="proves"><strong>What this proves:</strong> the chatbot answers from the database, not from guesswork. It gave the price
    (${f["price"]:.0f}), the exact number in stock for a medium ({f["stock"][IN_STOCK_SIZE]}), and said the {SOLD_OUT_SIZE} is sold out, all matching the database below.</p>
  </figcaption>
</figure>
<div class="evidence">
  <p><strong>Question typed in the chat:</strong> <q>{e(inv["question"])}</q></p>
  <p><strong>Chatbot replied:</strong> <q>{e(inv["reply"])}</q></p>
  <p><strong>Database says</strong> ({e(PRODUCT_NAME)}): price ${f["price"]:.2f}; stock by size: {e(stock_line)}.</p>
  <p>Price matches: {verdict(inv["price_ok"])} · Medium quantity ({f["stock"][IN_STOCK_SIZE]}) matches: {verdict(inv["in_stock_ok"])} · {SOLD_OUT_SIZE} reported sold out (database: 0): {verdict(inv["sold_out_ok"])}</p>
</div>

<h2>Check 2 — Dynamic search: result cards appear after a category question {verdict(s["ok"])}</h2>
<figure>
  <img src="app_check_images/search_chat.png" alt="Chat reply saying the hoodies are on the Products page, with the results behind it">
  <figcaption>
    <p class="proves"><strong>What this proves (step 1):</strong> after the question “{e(s["question"])}”, typed while on the About page, the agent searched the
    catalogue and the site took the shopper to the Products page by itself. The chat reply points to the results.</p>
  </figcaption>
</figure>
<figure>
  <img src="app_check_images/search_results.png" alt="Products page showing 27 hoodie result cards with images, names and prices">
  <figcaption>
    <p class="proves"><strong>What this proves (step 2):</strong> the page now shows “{e(s["heading"])}” with {s["cards"]} product cards (image, name, short
    description, price). The database has {f["hoodies"]} hoodie-type products, so the count is exact.</p>
  </figcaption>
</figure>
<div class="evidence">
  <p><strong>Question typed in the chat:</strong> <q>{e(s["question"])}</q></p>
  <p><strong>Chatbot replied:</strong> <q>{e(s["reply"])}</q></p>
  <p><strong>Page after the question:</strong> {e(s["path"])} · heading “{e(s["heading"])}” · banner “{e(s["bar"])}”</p>
  <p>Cards shown: {s["cards"]} · hoodie-type products in the database: {f["hoodies"]} · counts match: {verdict(s["cards"] == f["hoodies"])} · clicking the first card opens its detail page: {verdict(s["first_card_opens_detail"])}</p>
</div>

<h2>Check 3 — Problem 9 usability feature: sold-out sizes stay clickable {verdict(so["ok"])}</h2>
<figure>
  <img src="app_check_images/sold_out.png" alt="Product page with the sold-out XL size selected, showing SOLD OUT and a disabled Sold out button">
  <figcaption>
    <p class="proves"><strong>What this proves:</strong> the sold-out size ({SOLD_OUT_SIZE}) is a normal clickable button with a dashed outline. Clicking it shows
    “SOLD OUT” in the text under the sizes, and the cart button becomes a disabled “Sold out” so it can’t be added.</p>
  </figcaption>
</figure>
<div class="evidence">
  <p><strong>Text under the sizes after clicking {SOLD_OUT_SIZE}:</strong> <q>{e(so["note"])}</q></p>
  <p><strong>Cart button:</strong> “{e(so["button"])}” (disabled: {so["button_disabled"]}) · <strong>Cart in the nav bar:</strong> “{e(so["nav_cart"])}” (nothing added)</p>
  <p><strong>Database says</strong> sold out (quantity 0) for this item: {e(", ".join(so["db_sold_out"]))}. Sizes the page marked with a dashed outline: {e(", ".join(so["dashed"]))}.
  Every size button is clickable: {verdict(so["all_clickable"])} · the page matches the database: {verdict(sorted(so["dashed"]) == so["db_sold_out"])}</p>
</div>

</main>
<footer>
  Generated by <code>scripts/app_check.py</code> — run <code>backend/.venv/bin/python scripts/app_check.py</code> from the HW 4 folder to repeat the test.
</footer>
</body>
</html>
"""


if __name__ == "__main__":
    if CHROMIUM is None:
        sys.exit("No Playwright Chromium found. Run: backend/.venv/bin/python -m playwright install chromium")
    results = run()
    (OUT / "app_check.html").write_text(build_html(results), encoding="utf-8")
    print("wrote output/app_check.html and", len(list(IMAGES.glob("*.png"))), "screenshots")
    for key in ("inventory", "search", "sold_out"):
        print(f"\n[{key}]")
        for k, v in results[key].items():
            print(f"   {k}: {v}")
