# Design — Campus Customs

I restyled the site so it feels smoother and looks more like Yale. Colors and fonts are based on campuscustoms.com.

## What I changed and why it helps

### 1. Motion for smoothness
**What:** When a shopper goes to a new page, the new page fades in out of a soft blur (about half a second) instead of snapping in. Buttons, cards, and sizes also ease between states instead of jumping. If someone has "reduce motion" turned on in their device, the animation is off.

**Why it helps customers stick around and buy:** Shoppers click through many product pages. A quick blur-in makes each click feel like the same site continuing, not a hard reload, so it feels fast and polished and they keep browsing. The same easing on the size buttons and Add to cart shows right away that a click worked.

### 2. Colors more like Yale
**What:** The base is now white with Yale blue, using the navy and light blue from campuscustoms.com. Black and pink stay only for small details: the selected size, pressed buttons, the current-page underline, keyboard focus, sold-out markers, and the chat tape measure.

| Role | Color |
|---|---|
| Buttons, links, prices | Yale blue `#00356b` |
| Text, footer | Navy `#0c233f` (from campuscustoms.com) |
| Hovers, tags | Light blue `#7ba0c5` (from campuscustoms.com) |
| Page | White `#ffffff` |
| Clicked, selected, focus | Black `#0a0a0a` and pink `#ff4fa3` |

**Fonts:** Archivo Narrow for text and headings, Raleway for intro text and small labels, the same two fonts campuscustoms.com uses.

**Why it helps customers stick around and buy:** The people buying are Yale students, parents, and alumni, and blue and white is what they already wear and recognize. A site that looks like Yale feels like official, licensed merchandise, so shoppers trust it enough to check out. Because pink is now rare, it shows the shopper what they just picked: the chosen size or the button they pressed.

### 3. White backgrounds on product photos
**What:** 74 of the 102 product photos had a black background or black bars down the sides. I changed that black to white, so the shirts and hoodies sit directly on the white page. The original photos are untouched; the site uses the new copies in `data/products_white/`.

**Why it helps customers stick around and buy:** On a white page, black photo boxes look like holes and make the product grid uneven. With matching backgrounds, the product is what stands out, and shoppers can compare 102 items quickly and see each item clearly on its page. A clean, consistent grid also looks like a real store, which builds trust.
