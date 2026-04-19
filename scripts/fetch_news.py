#!/usr/bin/env python3
"""
Asia Digital Governance Knowledge Graph — Daily Auto-Update Script
=================================================================
Queries Google News RSS for 8 Asian countries on Digital / DPI / AI topics,
generates an interactive D3.js knowledge graph, and writes index.html.

Run locally:   python scripts/fetch_news.py
Runs via:      GitHub Actions cron (see .github/workflows/daily-update.yml)
Output:        index.html  (served by GitHub Pages)
"""

import feedparser
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

# ─────────────────────────────────────────────────────────────────────────────
# COUNTRY QUERY CONFIG
# ─────────────────────────────────────────────────────────────────────────────
COUNTRIES = {
    "India": {
        "color": "#FF7043",
        "queries": [
            "India digital public infrastructure DPI 2026",
            "India Aadhaar Digital ID biometric UIDAI",
            "India artificial intelligence MeitY governance 2026",
            "India digital data exchange bureaucrats",
        ],
    },
    "Indonesia": {
        "color": "#26C6DA",
        "queries": [
            "Indonesia digital ID IKD digital transformation",
            "Indonesia artificial intelligence AI governance policy",
            "Indonesia SATUSEHAT data exchange digital",
            "Indonesia digital economy Jakarta Post Kompas",
        ],
    },
    "Bangladesh": {
        "color": "#42A5F5",
        "queries": [
            "Bangladesh digital governance AI policy 2026",
            "Bangladesh political instability digital election",
            "Bangladesh digital infrastructure DPI",
        ],
    },
    "Philippines": {
        "color": "#66BB6A",
        "queries": [
            "Philippines PhilSys national digital ID 2026",
            "Philippines digital public infrastructure AI",
            "Philippines data exchange PhilHealth eGovPH",
        ],
    },
    "Thailand": {
        "color": "#FFCA28",
        "queries": [
            "Thailand digital economy artificial intelligence 2026",
            "Thailand digital ID digital governance DGA",
            "Thailand AI cloud Microsoft Google investment",
        ],
    },
    "Sri Lanka": {
        "color": "#AB47BC",
        "queries": [
            "Sri Lanka digital ID SL-UDI ICTA 2026",
            "Sri Lanka digital transformation data exchange NDX",
            "Sri Lanka AI digital governance budget",
        ],
    },
    "Nepal": {
        "color": "#8BC34A",
        "queries": [
            "Nepal digital public infrastructure World Bank 2026",
            "Nepal digital ID Nagarik app governance",
            "Nepal AI digital transformation ADB",
        ],
    },
    "PNG": {
        "color": "#FFA726",
        "queries": [
            "Papua New Guinea digital ID SevisPass 2026",
            "Papua New Guinea digital transformation AI DICT",
            "PNG digital governance DPI data exchange SevisDEx",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# THEME CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────
THEME_COLORS = {
    "Digital ID":            "#e91e8c",
    "DPI":                   "#4fc3f7",
    "AI":                    "#81c784",
    "Data Exchange":         "#ffb74d",
    "Political Instability": "#ef5350",
    "Digital Leaders":       "#ce93d8",
}

THEME_KEYWORDS = {
    "Digital ID": [
        "digital id", "digital identity", "biometric id", "national id",
        "aadhaar", "philsys", "sevispass", "ikd", "sl-udi", "nagarik",
        "e-id", " eid ", "identity card", "digital passport", "foundational id",
    ],
    "AI": [
        "artificial intelligence", " ai ", "machine learning", "deepfake",
        "llm", "generative ai", "ai policy", "ai governance", "ai strategy",
        "ai roadmap", "automation", "ai regulation", "ai adoption",
    ],
    "Data Exchange": [
        "data exchange", "interoperability", "satusehat", "data sharing",
        "sevisdex", "ndx", "data platform", "open data", "data infrastructure",
        "api integration", "data governance",
    ],
    "Political Instability": [
        "political instability", "political crisis", "election", "protest",
        "government collapse", "coup", "unrest", "turmoil", "interim government",
        "uprising", "political uncertainty", "political transition",
    ],
    "Digital Leaders": [
        "minister appointed", "secretary appointed", "bureaucrat",
        "director general", "ceo appointed", "uidai ceo", "meity secretary",
        "dict chief", "dga chief", "digital minister", "digital czar",
    ],
    "DPI": [
        "digital public infrastructure", "dpi", "india stack",
        "digital economy", "e-government", "digital transformation",
        "govtech", "government digital", "digital platform", "digital service",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# SEED ARTICLES  (curated fallback — used when live fetch returns < 3 articles)
# ─────────────────────────────────────────────────────────────────────────────
SEED_ARTICLES = [
    # INDIA
    {"id":"s_ind1","country":"India","theme":"Digital ID","date":"2026-02-15",
     "title":"India Showcases AI-Ready Digital Identity Infrastructure at Global Summit",
     "summary":"UIDAI rolls out AI biometric deduplication platform (Feb 2026). Aadhaar covers 1.44B residents; 2,707 crore authentications in 2024–25. India signs DPI MoUs with 24 countries.",
     "source":"ID Tech Wire","url":"https://idtechwire.com/india-showcases-ai-ready-digital-identity-infrastructure-at-global-summit/"},
    {"id":"s_ind2","country":"India","theme":"DPI","date":"2026-03-19",
     "title":"India Stack 2026: What Is Digital Public Infrastructure?",
     "summary":"India's four-layer DPI — Aadhaar, UPI, DigiLocker, Account Aggregator — covers 1.44B residents. IMF cites India as the leading example of digital infrastructure globally.",
     "source":"India Policy Hub","url":"https://indiapolicyhub.in/2026/03/19/india-stack-digital-governance-india-dpi-explained/"},
    {"id":"s_ind3","country":"India","theme":"DPI","date":"2026-03-10",
     "title":"India's Digital Infrastructure Goes Global — What Kind of Power Is It Building?",
     "summary":"India has inked DPI-sharing agreements with 24 nations in SE Asia, Caribbean, Africa and Latin America, raising data-sovereignty questions.",
     "source":"Tech Policy Press","url":"https://www.techpolicy.press/indias-digital-infrastructure-is-going-global-what-kind-of-power-is-it-building/"},
    {"id":"s_ind4","country":"India","theme":"AI","date":"2026-03-20",
     "title":"India Turns to AI Infrastructure for Data-Driven Governance",
     "summary":"IndiaAI Mission secures 10,000+ GPUs; 67 foundational model proposals reviewed. AIKosh open-data platform and voice LLMs for India's diverse languages launched.",
     "source":"Voice & Data","url":"https://www.voicendata.com/artificialintelligence/india-turns-to-ai-infrastructure-for-data-driven-governance-11247785"},
    {"id":"s_ind5","country":"India","theme":"AI","date":"2026-01-07",
     "title":"The Man Who Made India Digital Isn't Done Yet — Nilekani on AI + Aadhaar",
     "summary":"MIT Technology Review profiles Nandan Nilekani's vision for personal AI agents for every Indian using Aadhaar as the authentication backbone.",
     "source":"MIT Technology Review","url":"https://www.technologyreview.com/2026/01/07/1129748/aadhaar-nandan-nilekani-india-digital-biometric-identity-data/"},
    {"id":"s_ind6","country":"India","theme":"Digital Leaders","date":"2026-03-01",
     "title":"Key Bureaucrats: Bhuvnesh Kumar (UIDAI), Abhishek Singh (IndiaAI), S. Krishnan (MeitY)",
     "summary":"Bhuvnesh Kumar (IAS) appointed UIDAI CEO. Abhishek Singh (MeitY/NIC) heads $1.2B IndiaAI Mission. S. Krishnan champions Viksit Bharat 2047 DPI vision.",
     "source":"Analytics India Magazine","url":"https://analyticsindiamag.com/ai-highlights/indias-100-most-influential-people-in-ai/"},
    # INDONESIA
    {"id":"s_idn1","country":"Indonesia","theme":"Digital ID","date":"2026-02-10",
     "title":"Indonesia Aims to Boost IKD Digital ID Uptake — Only 17M of 270M Covered",
     "summary":"Identitas Kependudukan Digital (IKD) issued to just 17 million Indonesians, far below targets. Govt pledges simplified verification and broader public-service integration in 2026.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202502/indonesia-aims-to-boost-digital-id-uptake-in-bid-for-greater-efficiency"},
    {"id":"s_idn2","country":"Indonesia","theme":"AI","date":"2025-07-15",
     "title":"Indonesia's AI National Roadmap: Sovereign Digital Future by 2030",
     "summary":"Indonesia publishes AI National Roadmap White Paper (Jul 2025). Ranks #1 in SE Asia for AI investment ($4.6B, 2020–2024). Sector-specific AI regulations planned for finance and healthcare.",
     "source":"PS Engage","url":"https://ps-engage.com/indonesias-ai-national-roadmap-white-paper-paving-the-way-toward-a-smarter-and-sovereign-digital-future/"},
    {"id":"s_idn3","country":"Indonesia","theme":"DPI","date":"2026-04-03",
     "title":"Indonesia Digital Transformation Market 2026: $29B and Growing at 19% CAGR",
     "summary":"Indonesia digital transformation market grows from $24.4B (2025) to $29B (2026), forecast $69.6B by 2031. Microsoft, Google and AWS all expanding data-centre capacity.",
     "source":"Digital in Asia","url":"https://digitalinasia.com/2026/04/03/indonesia-digital-market-overview-2026/"},
    {"id":"s_idn4","country":"Indonesia","theme":"Data Exchange","date":"2025-12-10",
     "title":"SATUSEHAT: Indonesia's National Health Data Exchange Becomes Mandatory",
     "summary":"SATUSEHAT interoperability compliance is now a decisive criterion in government health IT procurement. National data exchange sits at the core of Indonesia's DPI ambitions for 2026.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202512/indonesia-plans-major-digital-infrastructure-investments-to-boost-economy"},
    {"id":"s_idn5","country":"Indonesia","theme":"Digital Leaders","date":"2024-10-20",
     "title":"Minister Meutya Hafid Reshapes Indonesia's Digital Agenda After Budi Arie Exit",
     "summary":"Meutya Hafid replaces Budi Arie Setiadi as Communications Minister, refocusing on child online safety and combating gambling while AI and DPI investments continue.",
     "source":"Jakarta Globe","url":"https://jakartaglobe.id/tech/new-communication-minister-meutya-hafid-focuses-on-protecting-children-and-combating-online-gambling"},
    # BANGLADESH
    {"id":"s_bgd1","country":"Bangladesh","theme":"Political Instability","date":"2026-04-01",
     "title":"AI and Synthetic Reality Shaped Bangladesh's 2026 Election",
     "summary":"72 documented cases of AI-manipulated content during the 12 Feb 2026 election. Deepfake videos of exiled PM Hasina circulated widely. Bangladesh's first AI-saturated election.",
     "source":"Global Voices","url":"https://globalvoices.org/2026/04/01/how-artificial-intelligence-and-synthetic-reality-shaped-bangladeshs-2026-election/"},
    {"id":"s_bgd2","country":"Bangladesh","theme":"Political Instability","date":"2026-02-10",
     "title":"How External Digital Actors Are Influencing Bangladesh's Political Discourse",
     "summary":"Foreign digital interference tracked ahead of 2026 election. Interim govt under Muhammad Yunus tries to build digital guardrails after Hasina-era Digital Security Act abuses.",
     "source":"Global Policy Journal","url":"https://www.globalpolicyjournal.com/blog/10/02/2026/how-external-digital-actors-are-influencing-bangladeshs-political-discourse-ahead"},
    {"id":"s_bgd3","country":"Bangladesh","theme":"AI","date":"2026-02-09",
     "title":"Bangladesh National AI Policy 2026–2030: Bold Start, Weak Implementation",
     "summary":"Risk-based regulatory framework, ban on mass surveillance and mandatory algorithmic impact assessments drafted. But oversight body (NDGIA) not yet operational.",
     "source":"Policy Magazine (Canada)","url":"https://www.policymagazine.ca/bangladeshs-ai-moment-testing-the-implementation-gap/"},
    {"id":"s_bgd4","country":"Bangladesh","theme":"DPI","date":"2026-02-15",
     "title":"Bangladesh Election 2026 Reveals a Transformed Political Landscape",
     "summary":"Chatham House: 18 months of Yunus interim govt preceded Feb 2026 elections. Digital governance reforms — including repeal of the Digital Security Act — tested amid fragile transition.",
     "source":"Chatham House","url":"https://www.chathamhouse.org/2026/02/bangladesh-election-reveals-transformed-political-landscape"},
    {"id":"s_bgd5","country":"Bangladesh","theme":"Digital Leaders","date":"2026-03-01",
     "title":"Yunus Government Pushes Digital Reforms; Digital Security Act Repealed",
     "summary":"Interim PM Yunus-led govt repeals Digital Security Act, launches AI policy consultations and seeks to re-establish Bangladesh as a credible digital governance actor in the region.",
     "source":"The Daily Star","url":"https://www.thedailystar.net/business/column/news/how-ready-bangladesh-era-ai-4063926"},
    # PHILIPPINES
    {"id":"s_phl1","country":"Philippines","theme":"Digital ID","date":"2026-03-15",
     "title":"Philippines Reaches 84 Million Digital IDs — 73% National Adoption Rate",
     "summary":"PhilSys National ID reaches 84M registrations (March 2026). 73% adoption rate. President champions Digital ID for inclusive public services across 7,000+ islands.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202503/philippines-reaches-84-million-digital-ids-amid-dpi-rollout"},
    {"id":"s_phl2","country":"Philippines","theme":"Data Exchange","date":"2026-04-08",
     "title":"Philippines Plans Healthcare Data Exchange via PhilSys-PhilHealth Integration",
     "summary":"PhilHealth and PSA sign MoU (April 2026) to integrate PhilSys into healthcare claims verification. AI-assisted validation and liveness checks added to prevent fraud.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202604/philippines-plans-id-verification-for-healthcare-with-philsys-integration"},
    {"id":"s_phl3","country":"Philippines","theme":"DPI","date":"2025-03-20",
     "title":"Philippines Hosts MOSIP Connect 2025; Advances Open-Source DPI Strategy",
     "summary":"Philippines hosted MOSIP Connect in Manila. eGovPH Super App provides one-stop government services platform. Philippines positions as SE Asia leader in open-source DPI.",
     "source":"UNESCAP CRVS","url":"https://crvs.unescap.org/news/philippines-president-champions-digital-id-inclusive-public-services"},
    {"id":"s_phl4","country":"Philippines","theme":"AI","date":"2026-02-20",
     "title":"How the Philippines Hit 73% Digital ID Adoption via AI-Backed Biometrics",
     "summary":"PhilSys uses AI-backed biometric deduplication and third-party liveness checks. Multi-layer AI fraud detection ensures certificates released only to rightful owners.",
     "source":"Dock.io","url":"https://www.dock.io/post/how-the-philippines-hit-73-digital-id-adoption"},
    {"id":"s_phl5","country":"Philippines","theme":"Digital Leaders","date":"2026-03-01",
     "title":"PSA and PhilSys: Driving National ID Rollout as DPI Backbone",
     "summary":"Philippine Statistics Authority (PSA) leads PhilSys expansion. President Marcos champions presenceless, paperless and cashless digital economy.",
     "source":"PhilSys Official","url":"https://philsys.gov.ph/psa-national-id-continues-to-enable-improved-delivery-of-services-to-the-public/"},
    # THAILAND
    {"id":"s_tha1","country":"Thailand","theme":"AI","date":"2026-03-20",
     "title":"Thailand Accelerates AI with $1B Cloud Investments from Microsoft and Google",
     "summary":"Microsoft pledges $1B+ for cloud/AI in Thailand; Google Cloud opens Bangkok region. Thailand AI market forecast at $1.16B (2025), growing 26% annually through 2031.",
     "source":"Noah News","url":"https://noah-news.com/thailand-accelerates-digital-push-with-1-billion-cloud-and-ai-investments-amidst-regulatory-overhaul/"},
    {"id":"s_tha2","country":"Thailand","theme":"DPI","date":"2026-04-06",
     "title":"Thailand Digital Economy Forecast to Grow 4.2% in 2026 — Double GDP Rate",
     "summary":"Thai digital economy to reach 5.6 trillion baht (~$171B) in 2026. All public agencies mandated to complete digital transition by 2026. State agency IT spending to hit 30% by 2027.",
     "source":"The Nation Thailand","url":"https://www.nationthailand.com/business/economy/40057845"},
    {"id":"s_tha3","country":"Thailand","theme":"AI","date":"2026-03-10",
     "title":"Thailand Outlines National AI Strategy: 10M AI Users, 90K Professionals Targeted",
     "summary":"National AI Plan (2022–2027) targets 10M AI users, 90K professionals and 50K developers. Ministry of Digital Economy releases draft AI law principles for consultation.",
     "source":"The Nation Thailand","url":"https://www.nationthailand.com/business/tech/40049494"},
    {"id":"s_tha4","country":"Thailand","theme":"Digital Leaders","date":"2026-03-01",
     "title":"DGA CEO Sak Segkhoonthod Drives Thailand's Government AI Transformation",
     "summary":"Digital Government Agency (DGA) CEO outlines Thailand's government AI roadmap with automated public service delivery and cloud-first strategy.",
     "source":"GovInsider Asia","url":"https://govinsider.asia/intl-en/article/thailand-accelerates-cloud-and-ai-adoption-to-transform-public-services"},
    # SRI LANKA
    {"id":"s_lka1","country":"Sri Lanka","theme":"Digital ID","date":"2026-02-15",
     "title":"Sri Lanka's SL-UDI Digital ID Launching Q3 2026 — In Final Procurement Stage",
     "summary":"Sri Lanka Unique Digital Identity (SL-UDI) funded by Rs 10.4B Indian grant. MSI procurement to conclude imminently. President confirms Q3 2026 first-ID distribution.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202602/sri-lanka-digital-id-launching-in-q3-this-year"},
    {"id":"s_lka2","country":"Sri Lanka","theme":"Data Exchange","date":"2026-02-05",
     "title":"Sri Lanka National Data Exchange (NDX) to Connect Digital ID and Public Services",
     "summary":"NDX platform will link SL-UDI to all e-government services. Data exchange can begin within 3–6 months under new data protection laws.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202502/sri-lanka-national-data-exchange-to-connect-digital-id-and-public-services"},
    {"id":"s_lka3","country":"Sri Lanka","theme":"DPI","date":"2025-11-20",
     "title":"Sri Lanka Invests $120M in Digital Transformation — 2026 Budget",
     "summary":"35.6 billion LKR (~$120M) pledged in 2026 budget. Rs. 750M for new AI data centre. Lanka Government Cloud upgrade and digital interface development included.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202511/sri-lanka-earmarks-millions-to-accelerate-digital-transformation-in-2026-budget"},
    {"id":"s_lka4","country":"Sri Lanka","theme":"Digital Leaders","date":"2026-03-10",
     "title":"Sri Lanka Deputy Minister Confirms SL-UDI in Final Stage; ICTA Leads Project",
     "summary":"Deputy Minister of Digital Economy confirms SL-UDI in final stage. ICTA oversees project with India-funded technical assistance and ADB support.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202603/sri-lanka-digital-id-project-in-final-stage-digital-economy-deputy-minister"},
    # NEPAL
    {"id":"s_npl1","country":"Nepal","theme":"DPI","date":"2026-02-09",
     "title":"World Bank Approves $50M for Nepal's Digital Public Infrastructure",
     "summary":"World Bank ($50M lead) + ADB ($40M) fund Nepal's DPI: new national ID system, government-wide data exchange, integrated social registry, digital locker and citizen portal.",
     "source":"World Bank / Biometric Update","url":"https://www.biometricupdate.com/202602/world-bank-approves-50m-for-nepals-dpi-including-new-national-identity-system"},
    {"id":"s_npl2","country":"Nepal","theme":"Digital ID","date":"2026-03-23",
     "title":"Nepal's Nagarik App Rolled Out — But Government Offices Still Demand Paper",
     "summary":"Despite digital ID app launch, institutions keep demanding physical copies. Core obstacle is outdated laws and inconsistent institutional mandates, not the technology.",
     "source":"Kathmandu Post","url":"https://kathmandupost.com/national/2026/03/23/nepal-built-a-digital-identity-app-so-why-do-government-offices-still-want-the-paper"},
    {"id":"s_npl3","country":"Nepal","theme":"Data Exchange","date":"2026-02-20",
     "title":"Nepal Links Citizenship and National ID Databases — First Interoperability Milestone",
     "summary":"Nepal establishes interoperability between CCMIS and NIMIS. Pre-enrollment for national ID eliminated. Secure government-wide data exchange planned.",
     "source":"ID Tech Wire","url":"https://idtechwire.com/nepal-establishes-interoperability-between-citizenship-and-national-id-systems/"},
    {"id":"s_npl4","country":"Nepal","theme":"AI","date":"2026-03-15",
     "title":"Nepal-India Tech Forum 2026: AI and Digital Infrastructure Cooperation",
     "summary":"Nepal and India hold Tech Forum 2026 in New Delhi to advance AI investment, digital identity interoperability and bilateral digital infrastructure cooperation.",
     "source":"Rising Nepal Daily","url":"https://risingnepaldaily.com/news/76316"},
    # PNG
    {"id":"s_png1","country":"PNG","theme":"Digital ID","date":"2026-03-01",
     "title":"PNG's SevisPass Digital ID Launches March 2026 — Mandatory for Govt Contractors",
     "summary":"SevisPass digital ID launched March 2026. Cabinet-approved National Digital Identity Policy 2025 mandates SevisPass for all business entities in govt procurement bids.",
     "source":"DICT PNG (Official)","url":"https://www.ict.gov.pg/89962/"},
    {"id":"s_png2","country":"PNG","theme":"Data Exchange","date":"2025-08-15",
     "title":"PNG Launches SevisDEx — National Data Exchange Connecting Full DPI Ecosystem",
     "summary":"SevisDEx connects SevisPass (identity), SevisPay (payments), SevisWallet and SevisPortal into an integrated DPI ecosystem.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202508/png-to-launch-data-exchange-platform-for-digital-id-system-in-2026"},
    {"id":"s_png3","country":"PNG","theme":"AI","date":"2026-03-15",
     "title":"PNG Must Build Digital Foundations to Lead AI Economy — DICT Chief",
     "summary":"PNG immigration authority deploys AI document verification — visa processing cut from days to minutes. DICT releases Draft National Sovereign Digital Transformation and AI Strategy.",
     "source":"The PNG Sun","url":"https://www.thepngsun.com/png-must-build-digital-foundations-to-lead-ai-economy-matainaho/"},
    {"id":"s_png4","country":"PNG","theme":"DPI","date":"2026-03-10",
     "title":"PNG DPI Rollout: Digital ID for KYC, Remote Bank Account Opening Piloted",
     "summary":"PNG pilots remote KYC using SevisPass for online bank account applications. AI adoption framework based on modular, interoperable DPI architecture.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202603/next-steps-in-papua-new-guineas-dpi-rollout-include-digital-id-for-kyc-ai-adoption"},
    {"id":"s_png5","country":"PNG","theme":"Digital Leaders","date":"2026-03-05",
     "title":"DICT PNG: Draft National Sovereign Digital Transformation and AI Strategy Released",
     "summary":"PNG's Department of ICT opens public consultation on sovereign AI strategy. Framework aims for trusted, coordinated, fiscally sustainable digital transformation.",
     "source":"DICT PNG (Official)","url":"https://www.ict.gov.pg/png-releases-draft-national-sovereign-digital-transformation-and-ai-strategy-for-public-consultation/"},
    {"id":"s_png6","country":"PNG","theme":"Digital ID","date":"2026-04-05",
     "title":"PNG Expands Mandatory Digital ID to All Businesses Taking Government Contracts",
     "summary":"From April 2026, every business entity in state tenders must use SevisPass for digital authentication on all procurement submissions.",
     "source":"Biometric Update","url":"https://www.biometricupdate.com/202604/png-expands-mandatory-digital-id-to-businesses-taking-govt-contracts"},
]

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def detect_theme(text: str) -> str:
    """Classify text into one of 6 themes using keyword matching."""
    tl = text.lower()
    scores = {t: sum(1 for k in kws if k in tl) for t, kws in THEME_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "DPI"


def clean_html(raw: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_recent(entry, days: int = 8) -> bool:
    """Return True if the RSS entry was published within the last N days."""
    p = entry.get("published_parsed")
    if not p:
        return True
    pub = datetime(*p[:6], tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - pub).days <= days


# ─────────────────────────────────────────────────────────────────────────────
# NEWS FETCHING
# ─────────────────────────────────────────────────────────────────────────────
def fetch_country(country: str, cfg: dict) -> list:
    """Fetch up to 6 recent articles for a country via Google News RSS."""
    articles, seen = [], set()
    for query in cfg["queries"]:
        if len(articles) >= 6:
            break
        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={quote(query)}&hl=en-US&gl=US&ceid=US:en"
        )
        try:
            feed = feedparser.parse(rss_url)
            time.sleep(1.5)          # polite crawl delay
            for entry in feed.entries:
                if len(articles) >= 6:
                    break
                title = clean_html(entry.get("title", "")).strip()
                if not title or title in seen:
                    continue
                if not is_recent(entry, days=8):
                    continue
                seen.add(title)
                summary = clean_html(entry.get("summary", title))[:320]
                pub_date = ""
                if entry.get("published_parsed"):
                    pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
                articles.append({
                    "id":      f"{country[:3].lower()}{len(articles)+1}",
                    "country": country,
                    "theme":   detect_theme(title + " " + summary),
                    "title":   title[:110],
                    "summary": summary,
                    "source":  entry.get("source", {}).get("title", "Google News"),
                    "url":     entry.get("link", "#"),
                    "date":    pub_date,
                })
        except Exception as exc:
            print(f"  ⚠  Error fetching '{query}': {exc}")
    return articles


def fetch_all_news() -> list:
    """Fetch news for all 8 countries, supplementing with seed data if sparse."""
    all_articles = []
    for country, cfg in COUNTRIES.items():
        print(f"  → {country}", flush=True)
        live = fetch_country(country, cfg)
        # Supplement with seed articles when live fetch is sparse
        if len(live) < 3:
            seeds = [a for a in SEED_ARTICLES if a["country"] == country]
            need  = min(6 - len(live), len(seeds))
            live += seeds[:need]
            if need:
                print(f"    (+ {need} seed articles as supplement)")
        print(f"    {len(live)} articles total")
        all_articles.extend(live)
    return all_articles


# ─────────────────────────────────────────────────────────────────────────────
# COUNTRY SUMMARIES
# ─────────────────────────────────────────────────────────────────────────────
def generate_country_summaries(all_articles: list) -> dict:
    """Build a one-paragraph summary per country from fetched article titles."""
    summaries = {}
    for country in COUNTRIES:
        arts = [a for a in all_articles if a["country"] == country]
        if not arts:
            summaries[country] = f"No recent digital governance news found for {country} this week."
            continue
        themes = sorted({a["theme"] for a in arts})
        theme_str = " · ".join(themes)
        headlines = " ".join(f"• {a['title']}." for a in arts[:4])
        summaries[country] = (
            f"This week's key themes: {theme_str}. "
            f"Top stories: {headlines}"
        )
    return summaries


# ─────────────────────────────────────────────────────────────────────────────
# HTML GENERATION
# ─────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Asia Digital Governance — Knowledge Graph | __WEEK_LABEL__</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0d1117;color:#e6edf3;display:flex;flex-direction:column;height:100vh;overflow:hidden}
#header{background:linear-gradient(135deg,#161b22 0%,#0d1117 100%);border-bottom:1px solid #30363d;padding:10px 20px;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;gap:12px}
#header h1{font-size:17px;color:#58a6ff;font-weight:700;white-space:nowrap}
.hm{font-size:11px;color:#8b949e;line-height:1.6}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;background:#1f6feb22;border:1px solid #1f6feb55;color:#58a6ff;font-size:10px;font-weight:600;white-space:nowrap}
#content{display:flex;flex:1;overflow:hidden}
#gc{flex:1;position:relative;overflow:hidden}
#sb{width:370px;background:#161b22;border-left:1px solid #30363d;overflow-y:auto;flex-shrink:0}
#sbh{padding:14px 16px;background:#1c2128;border-bottom:1px solid #30363d;position:sticky;top:0;z-index:10}
#sbh h2{font-size:14px;font-weight:600;color:#e6edf3}
#sbh p{font-size:11px;color:#8b949e;margin-top:3px}
.cs{border-bottom:1px solid #21262d}
.ch{padding:11px 16px;cursor:pointer;display:flex;align-items:center;gap:9px;transition:background .15s;user-select:none}
.ch:hover{background:#1c2128}
.cd{width:11px;height:11px;border-radius:50%;flex-shrink:0}
.cn{font-size:13px;font-weight:600}
.ac{font-size:10px;color:#8b949e;margin-left:auto;white-space:nowrap}
.chv{color:#8b949e;font-size:11px;margin-left:4px;transition:transform .2s}
.ch.open .chv{transform:rotate(180deg)}
.nl{padding:0 16px 10px;display:none}
.nl.visible{display:block}
.ni{padding:9px 0;border-bottom:1px solid #21262d}
.ni:last-child{border-bottom:none}
.tb{display:inline-block;padding:2px 7px;border-radius:8px;font-size:10px;font-weight:600;margin-bottom:5px}
.nt{font-size:12px;color:#c9d1d9;line-height:1.45;margin-bottom:5px;font-weight:500}
.ns{font-size:11px;color:#8b949e;line-height:1.55;margin-bottom:6px}
.nr{font-size:10px;color:#6e7681;margin-bottom:3px}
.nl a{font-size:11px;color:#58a6ff;text-decoration:none;word-break:break-all}
.nl a:hover{text-decoration:underline}
#filters{position:absolute;top:14px;left:14px;display:flex;flex-wrap:wrap;gap:5px;max-width:480px;z-index:10}
.fb{padding:4px 10px;border-radius:12px;border:1px solid #30363d;background:rgba(13,17,23,.85);color:#8b949e;font-size:11px;cursor:pointer;transition:all .18s;backdrop-filter:blur(8px);font-family:inherit}
.fb:hover{border-color:#58a6ff;color:#c9d1d9}
.fb.active{background:#1f6feb;border-color:#388bfd;color:#fff}
#legend{position:absolute;bottom:14px;left:14px;background:rgba(22,27,34,.92);border:1px solid #30363d;border-radius:8px;padding:11px 14px;backdrop-filter:blur(10px);z-index:10}
#legend h4{font-size:10px;color:#8b949e;margin-bottom:7px;text-transform:uppercase;letter-spacing:.6px}
.li{display:flex;align-items:center;gap:7px;margin-bottom:4px}
.ld{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.ll{font-size:11px;color:#c9d1d9}
#inst{position:absolute;bottom:14px;right:14px;background:rgba(22,27,34,.92);border:1px solid #30363d;border-radius:8px;padding:10px 13px;font-size:10px;color:#8b949e;line-height:1.7;backdrop-filter:blur(10px);z-index:10}
#inst strong{color:#c9d1d9}
#tt{position:fixed;background:rgba(13,17,23,.97);border:1px solid #30363d;border-radius:8px;padding:10px 13px;font-size:12px;max-width:300px;pointer-events:none;z-index:9999;display:none;line-height:1.5;box-shadow:0 4px 24px rgba(0,0,0,.5)}
#tt .ttt{font-weight:600;color:#e6edf3;margin-bottom:4px;font-size:12px}
#tt .ttb{font-size:10px;margin-bottom:5px}
#tt .tts{color:#8b949e;font-size:11px}
#tt .tth{color:#58a6ff;font-size:10px;margin-top:6px;font-style:italic}
svg text{user-select:none}
#rb{position:absolute;top:14px;right:14px;padding:5px 12px;border-radius:12px;border:1px solid #30363d;background:rgba(13,17,23,.85);color:#8b949e;font-size:11px;cursor:pointer;font-family:inherit;backdrop-filter:blur(8px);z-index:10;transition:all .18s}
#rb:hover{border-color:#58a6ff;color:#c9d1d9}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:#161b22}
::-webkit-scrollbar-thumb{background:#30363d;border-radius:3px}
.upd{position:absolute;bottom:14px;right:220px;font-size:10px;color:#484f58;z-index:10;background:rgba(13,17,23,.7);padding:4px 8px;border-radius:6px;backdrop-filter:blur(4px)}
#mob-drawer{display:none;position:fixed;bottom:0;left:0;right:0;background:#161b22;border-top:1px solid #30363d;border-radius:16px 16px 0 0;transform:translateY(100%);transition:transform .35s cubic-bezier(.32,.72,0,1);z-index:600;max-height:72vh;flex-direction:column;overflow:hidden}
#mob-drawer.open{transform:translateY(0)}
#drawer-pill-row{padding:10px 0 4px;display:flex;flex-direction:column;align-items:center;cursor:pointer;flex-shrink:0}
#drawer-pill{width:36px;height:4px;background:#30363d;border-radius:2px;margin-bottom:6px}
#drawer-title{font-size:13px;font-weight:700;padding:4px 16px 10px;border-bottom:1px solid #21262d;flex-shrink:0;width:100%}
#drawer-body{overflow-y:auto;flex:1;padding:0 16px 32px;-webkit-overflow-scrolling:touch}
#mob-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:599}
#mob-news-panel{display:none;position:fixed;inset:0;background:#0d1117;z-index:550;overflow-y:auto;padding-bottom:60px;-webkit-overflow-scrolling:touch}
#mob-news-panel.visible{display:block}
#mob-tabs{display:none;position:fixed;bottom:0;left:0;right:0;background:#161b22;border-top:1px solid #30363d;z-index:700;height:52px;justify-content:space-around;align-items:stretch}
.mtab{flex:1;background:none;border:none;color:#8b949e;font-size:11px;font-weight:600;cursor:pointer;font-family:inherit;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;transition:color .15s;border-top:2px solid transparent}
.mtab.active{color:#58a6ff;border-top-color:#58a6ff}
.mtab-icon{font-size:17px}
@media(max-width:768px){
body{height:100svh}
#header{padding:8px 12px;flex-wrap:wrap;gap:4px}
#header h1{font-size:13px}
.hm{font-size:10px}
.hm:last-child{display:none}
#sb{display:none}
#legend{display:none}
#inst{display:none}
#rb{display:none}
.upd{display:none}
#gc{height:calc(100svh - 52px - 52px)}
#filters{flex-wrap:nowrap;overflow-x:auto;max-width:calc(100vw - 20px);-webkit-overflow-scrolling:touch;scrollbar-width:none;padding-bottom:2px;top:10px;left:10px}
#filters::-webkit-scrollbar{display:none}
.fb{white-space:nowrap;flex-shrink:0}
#mob-drawer{display:flex}
#mob-tabs{display:flex}
}
</style>
</head>
<body>
<div id="header">
  <div>
    <h1>&#127758; Asia Digital Governance &mdash; Knowledge Graph</h1>
    <div class="hm">Weekly News Update &nbsp;|&nbsp; <strong style="color:#c9d1d9" id="wl">__WEEK_LABEL__</strong> &nbsp;|&nbsp; Digital ID &middot; DPI &middot; AI &middot; Data Exchange &middot; Political Instability &middot; Digital Leaders</div>
  </div>
  <div class="hm" style="text-align:right;flex-shrink:0">
    <span class="badge">8 Countries</span>&nbsp;
    <span class="badge">__ARTICLE_COUNT__ Articles</span>&nbsp;
    <span class="badge">Live Updates</span><br>
    <span style="font-size:10px">Reuters &middot; AP &middot; BBC &middot; Jakarta Post &middot; Kompas &middot; Bisnis Indonesia &middot; Biometric Update &middot; + more</span>
  </div>
</div>
<div id="content">
  <div id="gc">
    <svg id="graph"></svg>
    <div id="filters">
      <button class="fb active" data-theme="all" onclick="filterTheme('all',this)">All Themes</button>
      <button class="fb" data-theme="Digital ID" onclick="filterTheme('Digital ID',this)" style="border-color:#e91e8c44">Digital ID</button>
      <button class="fb" data-theme="DPI" onclick="filterTheme('DPI',this)" style="border-color:#4fc3f744">DPI</button>
      <button class="fb" data-theme="AI" onclick="filterTheme('AI',this)" style="border-color:#81c78444">AI</button>
      <button class="fb" data-theme="Data Exchange" onclick="filterTheme('Data Exchange',this)" style="border-color:#ffb74d44">Data Exchange</button>
      <button class="fb" data-theme="Political Instability" onclick="filterTheme('Political Instability',this)" style="border-color:#ef535044">Political Instability</button>
      <button class="fb" data-theme="Digital Leaders" onclick="filterTheme('Digital Leaders',this)" style="border-color:#ce93d844">Digital Leaders</button>
    </div>
    <button id="rb" onclick="resetView()">&#8635; Reset</button>
    <div id="legend">
      <h4>Theme Legend</h4>
      <div class="li"><div class="ld" style="background:#e91e8c"></div><span class="ll">Digital ID</span></div>
      <div class="li"><div class="ld" style="background:#4fc3f7"></div><span class="ll">Digital Public Infrastructure</span></div>
      <div class="li"><div class="ld" style="background:#81c784"></div><span class="ll">Artificial Intelligence</span></div>
      <div class="li"><div class="ld" style="background:#ffb74d"></div><span class="ll">Data Exchange</span></div>
      <div class="li"><div class="ld" style="background:#ef5350"></div><span class="ll">Political Instability</span></div>
      <div class="li"><div class="ld" style="background:#ce93d8"></div><span class="ll">Digital Leaders</span></div>
      <div style="margin-top:7px;padding-top:7px;border-top:1px solid #21262d">
        <div class="li"><div class="ld" style="background:#58a6ff;width:18px;height:18px"></div><span class="ll">Country Node</span></div>
        <div class="li"><div class="ld" style="background:#555;width:9px;height:9px"></div><span class="ll">Article (click = open URL)</span></div>
      </div>
    </div>
    <div id="inst"><strong>How to use:</strong><br>Scroll to zoom &nbsp;|&nbsp; Drag to move<br>&#128309; Click <strong>country</strong> &rarr; expand sidebar<br>&#128311; Click <strong>article node</strong> &rarr; open URL<br>Filter buttons &rarr; show by theme</div>
    <div class="upd">Last updated: __UPDATE_TIME__</div>
  </div>
  <div id="sb">
    <div id="sbh"><h2>Country News Details</h2><p>Click a country node or expand below</p></div>
  </div>
</div>
<div id="mob-overlay" onclick="closeMobDrawer()"></div>
<div id="mob-drawer">
  <div id="drawer-pill-row" onclick="closeMobDrawer()"><div id="drawer-pill"></div></div>
  <div id="drawer-title"></div>
  <div id="drawer-body"></div>
</div>
<div id="mob-news-panel">
  <div style="padding:14px 16px;position:sticky;top:0;background:#0d1117;border-bottom:1px solid #30363d;z-index:10;display:flex;align-items:center;gap:10px">
    <span style="font-size:16px">&#128240;</span>
    <div><div style="font-size:14px;font-weight:700;color:#e6edf3">All News</div>
    <div style="font-size:10px;color:#8b949e;margin-top:1px">8 countries &middot; tap article to open source</div></div>
  </div>
  <div id="mob-news-body"></div>
</div>
<div id="mob-tabs">
  <button class="mtab active" id="mtab-graph" onclick="switchMobTab('graph')"><span class="mtab-icon">&#127760;</span>Graph</button>
  <button class="mtab" id="mtab-news" onclick="switchMobTab('news')"><span class="mtab-icon">&#128240;</span>All News</button>
</div>
<div id="tt"></div>
<script>
// ════════════════════════════════════════════════════════════════
// DATA  (auto-injected daily by scripts/fetch_news.py)
// ════════════════════════════════════════════════════════════════
/*__DATA_INJECT__*/
// ════════════════════════════════════════════════════════════════
// GRAPH SETUP
// ════════════════════════════════════════════════════════════════
const countries = COUNTRIES;

const gNodes = [{id:'_c',label:'Asia\\nDigital\\n2026',type:'center',r:28}];
countries.forEach(c => gNodes.push({id:c,label:c,type:'country',color:COUNTRY_COLORS[c],r:20,country:c}));
ARTICLES.forEach(a => gNodes.push({
  id:a.id, label:a.title.slice(0,35)+(a.title.length>35?'\\u2026':''),
  fullTitle:a.title, type:'news', color:THEME_COLORS[a.theme],
  theme:a.theme, country:a.country, summary:a.summary,
  url:a.url, source:a.source, date:a.date||'', r:8
}));

const gLinks=[];
countries.forEach(c => gLinks.push({source:'_c',target:c,lt:'country'}));
ARTICLES.forEach(a => gLinks.push({source:a.country,target:a.id,lt:'news'}));

const gc=document.getElementById('gc');
let W=gc.clientWidth, H=gc.clientHeight;
const svg=d3.select('#graph').attr('width',W).attr('height',H);
const defs=svg.append('defs');
const gf=defs.append('filter').attr('id','glow');
gf.append('feGaussianBlur').attr('stdDeviation','3.5').attr('result','coloredBlur');
const fm=gf.append('feMerge');
fm.append('feMergeNode').attr('in','coloredBlur');
fm.append('feMergeNode').attr('in','SourceGraphic');

const sim=d3.forceSimulation(gNodes)
  .force('link',d3.forceLink(gLinks).id(d=>d.id).distance(d=>d.lt==='country'?155:75).strength(d=>d.lt==='country'?.9:.7))
  .force('charge',d3.forceManyBody().strength(d=>d.type==='center'?-1200:d.type==='country'?-400:-60))
  .force('center',d3.forceCenter(W/2,H/2))
  .force('collision',d3.forceCollide(d=>d.r+7));

const g=svg.append('g');
const zoomBeh=d3.zoom().scaleExtent([.25,4]).on('zoom',e=>g.attr('transform',e.transform));
svg.call(zoomBeh);

const lnk=g.append('g').selectAll('line').data(gLinks).join('line')
  .attr('stroke',d=>d.lt==='country'?'#30363d':'#21262d')
  .attr('stroke-width',d=>d.lt==='country'?1.5:.8)
  .attr('stroke-opacity',.75);

const nd=g.append('g').selectAll('g').data(gNodes).join('g')
  .attr('cursor',d=>d.type==='news'?'pointer':d.type==='country'?'pointer':'default')
  .call(d3.drag()
    .on('start',(e,d)=>{if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y})
    .on('drag', (e,d)=>{d.fx=e.x;d.fy=e.y})
    .on('end',  (e,d)=>{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null}));

nd.append('circle')
  .attr('r',d=>d.r)
  .attr('fill',d=>d.type==='center'?'#1f6feb':d.color)
  .attr('stroke',d=>d.type==='center'?'#388bfd':d.type==='country'?d.color:d.color+'88')
  .attr('stroke-width',d=>d.type==='country'?2.5:1)
  .attr('fill-opacity',d=>d.type==='news'?.72:.9)
  .style('filter',d=>d.type!=='news'?'url(#glow)':'none');

nd.filter(d=>d.type==='country'||d.type==='center')
  .append('text').attr('text-anchor','middle')
  .attr('dy',d=>d.type==='center'?'0.35em':'-27px')
  .attr('font-size',d=>d.type==='center'?'10px':'11px')
  .attr('font-weight','700').attr('fill','#e6edf3')
  .attr('pointer-events','none')
  .text(d=>d.type==='center'?'\\uD83C\\uDF0F Asia 2026':d.label);

nd.filter(d=>d.type==='news')
  .append('circle').attr('r',2.5).attr('fill','#fff').attr('fill-opacity',.4).attr('pointer-events','none');

const tte=document.getElementById('tt');
nd.filter(d=>d.type==='news')
  .on('mouseover',(e,d)=>{
    tte.style.display='block';
    tte.innerHTML=`<div class="ttt">${d.fullTitle}</div>
      <div class="ttb"><span style="display:inline-block;padding:2px 7px;border-radius:6px;background:${THEME_COLORS[d.theme]}22;color:${THEME_COLORS[d.theme]};border:1px solid ${THEME_COLORS[d.theme]}55;font-size:10px;font-weight:600">${d.theme}</span>
      <span style="font-size:10px;color:#8b949e;margin-left:6px">${d.country} &middot; ${d.source}</span></div>
      <div class="tts">${d.summary}</div>
      <div class="tth">&#128279; Click to open source URL</div>`;
  })
  .on('mousemove',e=>{
    tte.style.left=Math.min(e.clientX+14,window.innerWidth-310)+'px';
    tte.style.top=Math.min(e.clientY-8,window.innerHeight-220)+'px';
  })
  .on('mouseout',()=>{tte.style.display='none'})
  .on('click',(e,d)=>window.open(d.url,'_blank'));

nd.filter(d=>d.type==='country')
  .on('click',(e,d)=>{
    if(window.innerWidth<=768){openMobDrawer(d.id);}
    else{hlCountry(d.id);showSbCountry(d.id);}
  });

sim.on('tick',()=>{
  lnk.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
     .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
  nd.attr('transform',d=>`translate(${d.x},${d.y})`);
});

function filterTheme(theme,btn){
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  nd.selectAll('circle:first-child').attr('fill-opacity',d=>{
    if(theme==='all') return d.type==='news'?.72:.9;
    if(d.type==='center'||d.type==='country') return .9;
    return d.theme===theme?.95:.08;
  });
  lnk.attr('stroke-opacity',d=>{
    if(theme==='all') return .75;
    if(d.lt==='country') return .4;
    const t=gNodes.find(n=>n.id===(typeof d.target==='object'?d.target.id:d.target));
    return t&&t.theme===theme?.9:.05;
  });
}

function hlCountry(cid){
  nd.selectAll('circle:first-child').attr('fill-opacity',d=>{
    if(d.type==='center') return .9;
    if(d.type==='country') return d.id===cid?1:.3;
    return d.country===cid?.95:.08;
  });
  lnk.attr('stroke-opacity',d=>{
    const s=typeof d.source==='object'?d.source.id:d.source;
    const t=typeof d.target==='object'?d.target.id:d.target;
    return(s===cid||t===cid)?.95:.05;
  });
}

function resetView(){
  document.querySelectorAll('.fb').forEach(b=>b.classList.remove('active'));
  document.querySelector('.fb[data-theme="all"]').classList.add('active');
  nd.selectAll('circle:first-child').attr('fill-opacity',d=>d.type==='news'?.72:.9);
  lnk.attr('stroke-opacity',.75);
  svg.transition().duration(600).call(zoomBeh.transform,d3.zoomIdentity);
}

function buildSidebar(){
  let html=document.getElementById('sbh').outerHTML;
  countries.forEach(c=>{
    const arts=ARTICLES.filter(a=>a.country===c);
    const col=COUNTRY_COLORS[c];
    const ov=COUNTRY_SUMMARIES[c]||'';
    html+=`<div class="cs" id="sec-${c}">
      <div class="ch" id="hdr-${c}" onclick="togC('${c}')">
        <div class="cd" style="background:${col}"></div>
        <span class="cn" style="color:${col}">${c}</span>
        <span class="ac">${arts.length} articles</span>
        <span class="chv">&#9660;</span>
      </div>
      <div class="nl" id="nl-${c}">
        ${ov?`<div style="padding:10px 0 12px;font-size:11px;color:#8b949e;line-height:1.6;border-bottom:1px solid #21262d;margin-bottom:8px">
          <strong style="color:#c9d1d9;display:block;margin-bottom:4px">&#128240; This Week in ${c}</strong>${ov}
        </div>`:''}
        ${arts.map(a=>`<div class="ni">
          <span class="tb" style="background:${THEME_COLORS[a.theme]}18;color:${THEME_COLORS[a.theme]};border:1px solid ${THEME_COLORS[a.theme]}44">${a.theme}</span>
          ${a.date?`<span style="font-size:10px;color:#6e7681;margin-left:6px">${a.date}</span>`:''}
          <div class="nt">${a.title}</div>
          <div class="ns">${a.summary}</div>
          <div class="nr">Source: <strong>${a.source}</strong></div>
          <a href="${a.url}" target="_blank" rel="noopener">&#128279; Open article &rarr;</a>
        </div>`).join('')}
      </div>
    </div>`;
  });
  document.getElementById('sb').innerHTML=html;
}

function togC(c){
  const nl=document.getElementById('nl-'+c);
  const hd=document.getElementById('hdr-'+c);
  const v=nl.classList.toggle('visible');
  hd.classList.toggle('open',v);
}

function showSbCountry(c){
  countries.forEach(x=>{
    const nl=document.getElementById('nl-'+x);
    const hd=document.getElementById('hdr-'+x);
    if(nl) nl.classList.remove('visible');
    if(hd) hd.classList.remove('open');
  });
  const nl=document.getElementById('nl-'+c);
  const hd=document.getElementById('hdr-'+c);
  if(nl){nl.classList.add('visible');nl.scrollIntoView({behavior:'smooth',block:'nearest'})}
  if(hd) hd.classList.add('open');
}

buildSidebar();

// ── MOBILE ──────────────────────────────────────────────────
function openMobDrawer(cid){
  const arts=ARTICLES.filter(a=>a.country===cid);
  const col=COUNTRY_COLORS[cid];
  const ov=COUNTRY_SUMMARIES[cid]||'';
  document.getElementById('drawer-title').innerHTML=
    `<span style="display:inline-block;width:10px;height:10px;background:${col};border-radius:50%;margin-right:7px;vertical-align:middle"></span>`+
    `<span style="color:${col}">${cid}</span>`+
    `<span style="font-size:10px;color:#8b949e;margin-left:8px">${arts.length} articles this week</span>`;
  document.getElementById('drawer-body').innerHTML=
    (ov?`<div style="padding:10px 0 12px;font-size:11px;color:#8b949e;line-height:1.6;border-bottom:1px solid #21262d;margin-bottom:8px"><strong style="color:#c9d1d9;display:block;margin-bottom:4px">&#128240; This Week</strong>${ov}</div>`:'')+
    arts.map(a=>`<div style="padding:10px 0;border-bottom:1px solid #21262d">
      <span style="display:inline-block;padding:2px 7px;border-radius:8px;font-size:10px;font-weight:600;background:${THEME_COLORS[a.theme]}18;color:${THEME_COLORS[a.theme]};border:1px solid ${THEME_COLORS[a.theme]}44">${a.theme}</span>
      ${a.date?`<span style="font-size:10px;color:#6e7681;margin-left:6px">${a.date}</span>`:''}
      <div style="font-size:12px;color:#c9d1d9;margin:6px 0 4px;line-height:1.45;font-weight:500">${a.title}</div>
      <div style="font-size:11px;color:#8b949e;line-height:1.5;margin-bottom:6px">${a.summary}</div>
      <a href="${a.url}" target="_blank" rel="noopener" style="font-size:12px;color:#58a6ff;text-decoration:none;font-weight:500">&#128279; Open source &#8594;</a>
    </div>`).join('');
  document.getElementById('mob-drawer').classList.add('open');
  document.getElementById('mob-overlay').style.display='block';
}
function closeMobDrawer(){
  document.getElementById('mob-drawer').classList.remove('open');
  document.getElementById('mob-overlay').style.display='none';
}
function switchMobTab(tab){
  document.querySelectorAll('.mtab').forEach(b=>b.classList.remove('active'));
  document.getElementById('mtab-'+tab).classList.add('active');
  const p=document.getElementById('mob-news-panel');
  if(tab==='news'){p.classList.add('visible');buildMobNewsList();}
  else p.classList.remove('visible');
}
function buildMobNewsList(){
  const body=document.getElementById('mob-news-body');
  if(body.dataset.built)return;
  body.dataset.built='1';
  body.innerHTML=COUNTRIES.map(c=>{
    const arts=ARTICLES.filter(a=>a.country===c);
    const col=COUNTRY_COLORS[c];
    return`<div style="border-bottom:2px solid #21262d"><div style="padding:12px 16px 0">
      <div style="font-size:14px;font-weight:700;color:${col};display:flex;align-items:center;gap:7px;margin-bottom:8px">
        <span style="display:inline-block;width:10px;height:10px;background:${col};border-radius:50%"></span>${c}
        <span style="font-size:10px;color:#6e7681;font-weight:400">${arts.length} articles</span></div>
      ${arts.map(a=>`<div style="padding:9px 0;border-top:1px solid #21262d">
        <span style="display:inline-block;padding:2px 7px;border-radius:8px;font-size:10px;font-weight:600;background:${THEME_COLORS[a.theme]}18;color:${THEME_COLORS[a.theme]};border:1px solid ${THEME_COLORS[a.theme]}44">${a.theme}</span>
        ${a.date?`<span style="font-size:10px;color:#6e7681;margin-left:5px">${a.date}</span>`:''}
        <div style="font-size:12px;color:#c9d1d9;margin:5px 0 4px;line-height:1.45;font-weight:500">${a.title}</div>
        <div style="font-size:11px;color:#8b949e;line-height:1.5;margin-bottom:5px">${a.summary.slice(0,160)}${a.summary.length>160?'\\u2026':''}</div>
        <a href="${a.url}" target="_blank" rel="noopener" style="font-size:12px;color:#58a6ff;text-decoration:none">&#128279; Open &#8594;</a>
      </div>`).join('')}
    </div></div>`;
  }).join('');
}
// Swipe-down to close drawer
(function(){
  let sy=0;
  const el=document.getElementById('mob-drawer');
  el.addEventListener('touchstart',e=>{sy=e.touches[0].clientY;},{passive:true});
  el.addEventListener('touchend',e=>{if(e.changedTouches[0].clientY-sy>60)closeMobDrawer();},{passive:true});
})();

window.addEventListener('resize',()=>{
  W=gc.clientWidth;H=gc.clientHeight;
  svg.attr('width',W).attr('height',H);
  sim.force('center',d3.forceCenter(W/2,H/2)).alpha(.2).restart();
});
</script>
</body>
</html>"""


def generate_html(articles: list, summaries: dict, week_label: str, update_time: str) -> str:
    """Inject live data into the HTML template and return complete page."""
    country_colors = {c: v["color"] for c, v in COUNTRIES.items()}
    data_block = (
        f"const ARTICLES = {json.dumps(articles, ensure_ascii=False)};\n"
        f"const THEME_COLORS = {json.dumps(THEME_COLORS)};\n"
        f"const COUNTRY_COLORS = {json.dumps(country_colors)};\n"
        f"const COUNTRIES = {json.dumps(list(COUNTRIES.keys()))};\n"
        f"const COUNTRY_SUMMARIES = {json.dumps(summaries, ensure_ascii=False)};\n"
        f"const UPDATE_TIME = {json.dumps(update_time)};\n"
        f"const WEEK_LABEL = {json.dumps(week_label)};\n"
    )
    html = HTML_TEMPLATE.replace("/*__DATA_INJECT__*/", data_block)
    html = html.replace("__WEEK_LABEL__", week_label)
    html = html.replace("__ARTICLE_COUNT__", str(len(articles)))
    html = html.replace("__UPDATE_TIME__", update_time)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    now        = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_label  = f"Week of {week_start.strftime('%b %d')} \u2013 {now.strftime('%b %d, %Y')}"
    update_time = now.strftime("%B %d, %Y \u2014 %H:%M UTC")

    print("\n\U0001F30F Asia Digital Governance Knowledge Graph \u2014 Daily Update")
    print(f"   {update_time}\n")

    # Fetch live news
    all_articles = fetch_all_news()

    # Fallback: if overall fetch is very sparse, use all seeds
    if len(all_articles) < 15:
        print("\n\u26A0  Very few live articles fetched. Using full seed dataset as fallback.")
        all_articles = SEED_ARTICLES[:]

    print(f"\n\u2713 Total: {len(all_articles)} articles across {len(COUNTRIES)} countries")

    # Build country summaries
    summaries = generate_country_summaries(all_articles)

    # Generate HTML
    print("\u2192 Generating index.html ...")
    html = generate_html(all_articles, summaries, week_label, update_time)

    # Write output
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    idx_path = os.path.join(out_dir, "index.html")
    njk_path = os.path.join(out_dir, ".nojekyll")

    with open(idx_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    with open(njk_path, "w") as fh:
        pass  # empty sentinel for GitHub Pages

    print(f"\u2713 Done!  {idx_path}")
    print(f"   Size: {len(html)//1024} KB  |  Articles: {len(all_articles)}")


if __name__ == "__main__":
    main()
