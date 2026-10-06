"""Safety checks that run on the server, in code, before and after the model.

The prompt (prompts/prompt.md) tells the agent the safety rules, but a rule written in a prompt can be
ignored. These helpers make the most important ones true no matter what the model does:

  redact_sensitive()  removes card numbers, card security codes and expiry dates, passwords, gift card
                      codes, and bank details from what a shopper types. It runs BEFORE the message
                      reaches the model, the saved chat history, or the audit trail, so the agent never
                      sees the details, can't use them, and can't store them.
  comments_on_body()  spots a reply that comments on the shopper's body (too big, too small, weight...).
  scrub_for_log()     the same removal plus shortening, for anything written to the audit trail.
"""

import re

# ---- sensitive details a shopper might type ----

# 13 to 19 digits, with single spaces or dashes allowed between them. Only counts as a card if it passes the Luhn check,
# so order numbers, phone numbers, and measurements are left alone.
_CARD_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")

_PATTERNS = [
    ("card security code", re.compile(r"\b(?:cvv2?|cvc2?|cid|security code|card code)\b\W{0,12}\d{3,4}\b", re.I)),
    ("card expiry date", re.compile(
        r"\b(?:exp(?:iry|iration|ires)?(?: date)?|valid (?:thru|through)|good thru)\b\W{0,6}\d{1,2}\s*[/-]\s*\d{2,4}\b", re.I)),
    ("password", re.compile(r"\b(?:password|passcode|passwd|pwd|pw|pin)\s*(?:is|was|:|=)\s*\S+", re.I)),
    ("gift card code", re.compile(r"\bgift[ -]?card\b[^\n]{0,30}?(?:code|number|#|:)\W*[A-Za-z0-9-]{8,}", re.I)),
    ("bank account details", re.compile(
        r"\b(?:routing|account|acct|iban)\s*(?:number|no\.?|#)?\s*(?:is|:|=)?\s*[A-Z0-9][A-Z0-9 -]{6,}\d", re.I)),
]


def _luhn_ok(digits: str) -> bool:
    """The check-digit test every real card number passes."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    """Return (text with sensitive details replaced by "[removed: ...]", the kinds that were found)."""
    kinds: list[str] = []

    def mark(kind: str) -> str:
        if kind not in kinds:
            kinds.append(kind)
        return f"[removed: {kind}]"

    def card(match: re.Match) -> str:
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            return mark("card number") + (" " if match.group().endswith((" ", "-")) else "")
        return match.group()

    text = _CARD_NUMBER.sub(card, text)
    for kind, pattern in _PATTERNS:
        text = pattern.sub(lambda m, k=kind: mark(k), text)
    return text, kinds


def scrub_for_log(value: object, limit: int = 160) -> str:
    """Text that is safe and short enough for the audit trail: sensitive details removed, then shortened."""
    text, _ = redact_sensitive(str(value))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---- no comments on a shopper's body ----

_BODY_COMMENT = re.compile(
    r"\byou(?:'re|’re| are| look| seem| might be| may be| aren't| aren’t| are not)\s+(?:not |necessarily |really |a bit |a little |quite |very |so )*(?:too )?"
    r"(?:big|small|large|tiny|fat|thin|heavy|skinny|tall|short|overweight|underweight|obese|petite)\b"
    r"|\byour (?:body|weight|figure|build|waist|hips?|height|frame) (?:is|are|seems?|looks?|would)\b"
    r"|\b(?:overweight|underweight|obese|skinny|chubby)\b",
    re.I,
)


def comments_on_body(text: str) -> bool:
    return _BODY_COMMENT.search(text) is not None


BODY_FALLBACK = (
    "I can only talk about how our clothes fit. Tell me your chest measurement or the size you usually wear, "
    "and whether you want fitted, perfect sizing, or oversized, and I'll check the size chart and our stock."
)

# ---- telling the shopper why something was removed ----

_ALREADY_WARNED = re.compile(r"(?:don[’']?t|do not|never|please not|best not|avoid)[^.]{0,40}\bshar", re.I)
SENSITIVE_NOTICE = (
    "Please don't share card details or passwords in this chat. Use the Log In page for your account "
    "and the checkout page for payment."
)


def ensure_warning(reply: str, removed: list[str]) -> str:
    """If sensitive details were removed from the shopper's message, make sure the reply tells them not to share them."""
    if removed and not _ALREADY_WARNED.search(reply):
        return f"{reply} {SENSITIVE_NOTICE}".strip()
    return reply
