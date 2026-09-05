# Arena Factory Hoolulu

Autonomous 808 revenue factory for XKSH808 Digital Services Hawaii.

**Kai** promotes the offers on social. **Cass** sells. **Echo**, **Pono**, and **Aloha** run the rest of the pipeline. **Watch** is the only agent allowed to ping Xavier — and only on **HIGH** or **CRITICAL**.

```
Discover → Attract → Capture → Qualify → Pitch → Close → Verify → Deliver → Retain
   Echo       Kai       Echo      Echo     Cass    Cass   Xavier    Pono     Aloha
```

You do not get a ping because a post went out, a lead went warm, or a follow-up was queued. You get a ping when money needs human eyes, someone wants a refund, legal heat shows up, or the factory is on fire.

## One command

```bash
./hoolulu
```

Command center: **http://localhost:8080**

```bash
python -m factory tick      # one pipeline cycle
python -m factory status    # KPIs + open pings
```

No API key required. The factory runs fully offline with the local generator. Optional LLM keys live in `.env.example`.

## Agents

| Agent | Role | Pings Xavier? |
|-------|------|----------------|
| **Kai** | Social promoter — IG, TikTok, Facebook, X, LinkedIn, WhatsApp, Google Business | Never |
| **Echo** | Lead engine — ingest, score hot/warm/cold, recommend offer | Never |
| **Cass** | Sales closer — pitch, downsell, open pending payment | Never |
| **Pono** | Delivery — blocked until payment is human-verified | Never |
| **Aloha** | Retention — nudges and upsells | Never |
| **Watch** | Monitor + escalation gate | **HIGH / CRITICAL only** |

## Zero-trust money

Cass can open a **pending** payment. Cass cannot mark it complete. Pono will not deliver on pending. Xavier hits **I verified the money** in the command center. That is a HIGH ping by design.

## Catalog

| Offer | Price | Tier |
|-------|------:|------|
| Free Website | $0 | entry |
| Souper Agent Bot | $197 | core |
| Starter Pack | $297 | core |
| Pro Build | $497 | premium |
| KK OS Setup | $997 | premium |

## Escalation policy

Frozen in [`core/FROZEN_CONTRACT.json`](core/FROZEN_CONTRACT.json).

- **Silent** — `low`, `medium` (posts, scores, pitches, nudges)
- **Ping** — `high`, `critical` (payment verify, refund, chargeback, legal, hostile, safety)

## Tests

```bash
python -m pytest
```
