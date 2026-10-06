# Usability improvements — Campus Customs

(Drafted before building and updated at the end to match what was actually built.)

## 1. Sold-out sizes stay clickable

**What I added:** On a product page, a sold-out size is a normal clickable button with a dashed pink outline, not a disabled grey one. Clicking it shows **SOLD OUT — XL isn't available right now. Still in stock: S, M, L, XXL.** under the sizes, and the "Add to cart" button turns into a disabled "Sold out". Which sizes are sold out comes from the `inventory` table, not from the code. The site had no cart, so I added a small one (Add to cart button, Cart link in the nav bar, a cart page) that refuses sold-out sizes.

**Why it helps:** A shopper looking at a dead grey "XL" can't tell if it's sold out or if the site is broken, and may leave. Now they see "SOLD OUT" plus the sizes still available, so they can switch to another size and still buy.

## 2. Google Map in About Us

**What I added:** An embedded Google Map for 57 Broadway, New Haven, CT 06511 at the top of the About Us page, with the address and a "Get directions" link under it. It uses the plain Google embed (no API key) and resizes to fit phones (about 260px tall, no sideways scrolling). I couldn't see the pin itself in my test browser because it can't load outside websites, but the embed address checks out.

**Why it helps:** Students, visiting parents, and alumni on game weekends can see how far the shop is from campus and tap through for directions, instead of copying the address into a maps app.

## 3. Sizing guide

**What I added:** The No Boundaries × Walmart "What's my new size?" chart is stored as data (`backend/size_chart.json`) and the chatbot looks up a chest measurement or a usual size on it. Every size answer says the chart comes from that source, was made for another brand, may be inaccurate for Campus Customs items, and is only a rough guide. If the chart doesn't cover something (like a 70 inch chest), it says so and gives no size.

**Why it helps:** People buying online can't try things on, so "I'm usually a medium, what should I get?" or "what size is a 34 inch chest?" is the question most likely to stop a purchase. A quick answer with an honest warning can save a sale and a return.

## 4. Fit check

**What I added:** When someone asks about size, the chatbot asks if they want fitted (one size down), perfect sizing (their exact size), or oversized (one size up), then picks that size from the chart and checks it in `inventory`. If it's sold out, it says so and suggests the closest size that's in stock. It can also look up whether an item is fitted, regular, or oversized, but no item has that information yet (I added an empty `fit` column), so for now the bot says "I don't have fit information for this item" instead of guessing.

**Why it helps:** Many Yale students want a baggy hoodie but a snug tee, so one "your size is M" answer isn't enough. Checking stock in the same answer stops the bot from sending someone to a size they can't buy, and the business can fill in the `fit` column over time to make the advice better.
