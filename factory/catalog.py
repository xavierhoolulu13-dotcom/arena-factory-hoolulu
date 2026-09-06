from __future__ import annotations

from dataclasses import dataclass

from factory.config import CONTRACT


@dataclass(frozen=True)
class Offer:
    sku: str
    name: str
    price: int
    tier: str
    pitch: str
    deliverable: str


OFFERS: dict[str, Offer] = {
    "free-site": Offer(
        sku="free-site",
        name="Free Website",
        price=0,
        tier="entry",
        pitch="A live site for your shop this week. Hook offer — we prove the work, then you keep us.",
        deliverable="One-page Hawaii business site with click-to-call, hours, and Google map.",
    ),
    "souper-bot": Offer(
        sku="souper-bot",
        name="Souper Agent Bot",
        price=197,
        tier="core",
        pitch="24/7 AI chatbot on your site that books jobs while you are on the tools.",
        deliverable="Branded chat agent, FAQ brain, lead capture to your phone.",
    ),
    "starter": Offer(
        sku="starter",
        name="Starter Pack",
        price=297,
        tier="core",
        pitch="Web + local SEO so Honolulu customers actually find you.",
        deliverable="Site, Google Business cleanup, 5 keyword pages, call tracking.",
    ),
    "pro": Offer(
        sku="pro",
        name="Pro Build",
        price=497,
        tier="premium",
        pitch="Full funnel + booking. Ads, site, and calendar that close while you sleep.",
        deliverable="Funnel, booking automation, follow-up texts, review engine.",
    ),
    "kkos": Offer(
        sku="kkos",
        name="KK OS Setup",
        price=997,
        tier="premium",
        pitch="The whole business OS — leads, sales, delivery, money. We install it, you run it.",
        deliverable="KK OS install, agent wiring, pipeline, and 14-day operator training.",
    ),
}

# Frozen contract catalog must match local offers.
for row in CONTRACT["catalog"]:
    assert row["sku"] in OFFERS, row["sku"]


PAYMENT_INSTRUCTIONS = (
    "Cash App $xksh808dsh · PayPal xksh808dsh@gmail.com · "
    "Telegram @xksh808 for receipt. Delivery starts after Xavier verifies payment."
)

PLATFORMS = (
    "instagram",
    "tiktok",
    "facebook",
    "x",
    "linkedin",
    "whatsapp",
    "google_business",
)

HASHTAGS = (
    "#808business #Honolulu #HawaiiSmallBusiness #Hoolulu "
    "#XKSH808 #LocalFirst #Oahu #SupportLocal808"
)


def recommend_sku(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ("os", "operating system", "everything", "full system", "automation stack")):
        return "kkos"
    if any(k in t for k in ("funnel", "booking", "calendar", "ads", "automation")):
        return "pro"
    if any(k in t for k in ("seo", "google", "rank", "website +", "web +")):
        return "starter"
    if any(k in t for k in ("chatbot", "chat bot", "ai bot", "souper", "24/7", "after hours")):
        return "souper-bot"
    if any(k in t for k in ("free", "just a site", "landing page", "cheap")):
        return "free-site"
    return "starter"


def upsell_sku(sku: str) -> str | None:
    ladder = ["free-site", "souper-bot", "starter", "pro", "kkos"]
    if sku not in ladder:
        return "starter"
    idx = ladder.index(sku)
    if idx >= len(ladder) - 1:
        return None
    return ladder[idx + 1]
