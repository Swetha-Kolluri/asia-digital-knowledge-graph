#!/usr/bin/env python3
"""
DPI News Asia Pacific — Daily Auto-Update Script
=================================================
Queries Google News RSS for 8 Asian countries on Digital / DPI / AI topics,
generates a news bulletin HTML page, and writes index.html.

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
<title>DPI News Asia Pacific | __WEEK_LABEL__</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{--gold:#c9a84c;--gold-light:#e8c96a;--bg:#0a0a0a;--card:#0e0e0e;--border:#1c1c1c;--border-light:#2a2a2a;--text:#e8e8e8;--text-dim:#888;--text-muted:#555;--serif:'Playfair Display',Georgia,serif;--sans:'Inter',system-ui,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:15px;line-height:1.6;min-height:100vh}
.masthead{background:#000;border-bottom:1px solid var(--border);padding:28px 24px 20px;text-align:center}
.masthead-eyebrow{font-size:10px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:var(--gold);margin-bottom:10px}
.masthead-title{font-family:var(--serif);font-size:clamp(2rem,5vw,3.5rem);font-weight:700;color:#fff;line-height:1.1}
.masthead-title .accent{color:var(--gold)}
.masthead-meta{margin-top:12px;display:flex;justify-content:center;align-items:center;gap:20px;flex-wrap:wrap}
.masthead-meta span{font-size:11px;color:var(--text-muted);letter-spacing:.5px}
.masthead-meta .pipe{color:var(--border-light)}
.live-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#4caf50;margin-right:5px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.ribbon{background:var(--gold);padding:7px 0;overflow:hidden;white-space:nowrap}
.ribbon-inner{display:inline-block;animation:marquee 30s linear infinite;color:#000;font-size:11px;font-weight:600;letter-spacing:2px;text-transform:uppercase}
@keyframes marquee{from{transform:translateX(100vw)}to{transform:translateX(-100%)}}
.tabs-wrap{position:sticky;top:0;z-index:100;background:rgba(10,10,10,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);overflow-x:auto;scrollbar-width:none}
.tabs-wrap::-webkit-scrollbar{display:none}
.tabs{display:flex;align-items:center;padding:0 16px;gap:2px;min-width:max-content}
.tab{padding:14px 16px;font-size:12px;font-weight:500;color:var(--text-muted);cursor:pointer;border:none;background:none;border-bottom:2px solid transparent;transition:all .2s;white-space:nowrap;font-family:var(--sans)}
.tab:hover{color:var(--text)}
.tab.active{color:var(--gold);border-bottom-color:var(--gold)}
.main{max-width:1280px;margin:0 auto;padding:32px 20px 60px}
.country-divider{display:flex;align-items:center;gap:16px;margin:48px 0 28px}
.country-divider:first-child{margin-top:0}
.country-divider h2{font-family:var(--serif);font-size:1.5rem;font-weight:600;color:#fff;white-space:nowrap}
.country-divider .flag{font-size:1.4rem}
.country-divider .line{flex:1;height:1px;background:linear-gradient(to right,var(--border-light),transparent)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
@media(max-width:1024px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;overflow:hidden;display:flex;flex-direction:column;transition:border-color .2s,transform .2s;cursor:pointer}
.card:hover{border-color:var(--border-light);transform:translateY(-2px)}
.card.featured{grid-column:span 2;flex-direction:row}
@media(max-width:600px){.card.featured{grid-column:span 1;flex-direction:column}}
.thumb{position:relative;overflow:hidden;flex-shrink:0}
.card:not(.featured) .thumb{height:160px}
.card.featured .thumb{width:260px;min-height:220px}
@media(max-width:1024px){.card.featured .thumb{width:200px}}
@media(max-width:600px){.card.featured .thumb{width:100%;height:180px}}
.thumb-bg{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:2.8rem;position:relative}
.thumb-bg::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(0,0,0,.3),rgba(0,0,0,.6))}
.thumb-flag{position:absolute;bottom:8px;right:10px;font-size:1.1rem;z-index:1;filter:drop-shadow(0 1px 3px rgba(0,0,0,.8))}
.card-body{padding:18px 20px 20px;display:flex;flex-direction:column;gap:10px;flex:1}
.card-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.badge{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;padding:3px 8px;border-radius:3px;border:1px solid currentColor}
.card-country{font-size:11px;color:var(--text-muted);font-weight:500}
.card-date{font-size:11px;color:var(--text-muted);margin-left:auto}
.card-headline{font-family:var(--serif);font-size:1.05rem;font-weight:600;color:#fff;line-height:1.4}
.card.featured .card-headline{font-size:1.25rem}
.card-summary{font-size:13px;color:var(--text-dim);line-height:1.65;flex:1}
.card-source{font-size:11px;color:var(--text-muted)}
.card-link{display:inline-flex;align-items:center;gap:5px;color:var(--gold);font-size:12px;font-weight:600;text-decoration:none;letter-spacing:.3px;transition:color .2s;margin-top:4px}
.card-link:hover{color:var(--gold-light)}
.card-link svg{width:12px;height:12px}
.sources-section{border-top:1px solid var(--border);margin-top:64px;padding-top:40px;padding-bottom:40px}
.sources-section h3{font-family:var(--serif);font-size:1.1rem;font-weight:600;color:var(--gold);margin-bottom:20px;text-align:center}
.sources-grid{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:900px;margin:0 auto}
.source-tag{font-size:11px;color:var(--text-muted);border:1px solid var(--border);border-radius:4px;padding:5px 12px}
.footer-copy{text-align:center;margin-top:28px;font-size:11px;color:var(--text-muted)}
.empty{text-align:center;padding:60px 20px;color:var(--text-muted)}
.empty h3{font-family:var(--serif);font-size:1.3rem;margin-bottom:8px;color:var(--text-dim)}
.theme-digital-id{color:#a78bfa;border-color:#a78bfa}
.theme-dpi{color:#60a5fa;border-color:#60a5fa}
.theme-ai{color:#34d399;border-color:#34d399}
.theme-data-exchange{color:#fbbf24;border-color:#fbbf24}
.theme-political{color:#f87171;border-color:#f87171}
.theme-digital-leaders{color:#c084fc;border-color:#c084fc}
.theme-digital{color:#38bdf8;border-color:#38bdf8}
</style>
</head>
<body>
<header class="masthead">
  <div class="masthead-eyebrow">Digital Public Infrastructure &middot; Weekly Intelligence</div>
  <h1 class="masthead-title">DPI News <span class="accent">Asia Pacific</span></h1>
  <div class="masthead-meta">
    <span id="weekLabel">__WEEK_LABEL__</span>
    <span class="pipe">|</span>
    <span><span class="live-dot"></span>Auto-updated daily</span>
    <span class="pipe">|</span>
    <span id="articleCount">__ARTICLE_COUNT__ articles this week</span>
  </div>
</header>
<div class="ribbon">
  <span class="ribbon-inner">Digital Identity &nbsp;&middot;&nbsp; DPI &nbsp;&middot;&nbsp; Artificial Intelligence &nbsp;&middot;&nbsp; Data Exchange &nbsp;&middot;&nbsp; Political Instability &nbsp;&middot;&nbsp; Digital Leaders &nbsp;&middot;&nbsp; Digital Identity &nbsp;&middot;&nbsp; DPI &nbsp;&middot;&nbsp; Artificial Intelligence &nbsp;&middot;&nbsp; Data Exchange &nbsp;&middot;&nbsp; Political Instability &nbsp;&middot;&nbsp; Digital Leaders &nbsp;&middot;&nbsp;</span>
</div>
<nav class="tabs-wrap"><div class="tabs" id="tabs"></div></nav>
<main class="main" id="main"></main>
<div class="main sources-section" id="sources"></div>
<script>
/*__DATA_INJECT__*/
const COUNTRY_FLAGS = {"India":"\\uD83C\\uDDEE\\uD83C\\uDDF3","Indonesia":"\\uD83C\\uDDEE\\uD83C\\uDDE9","Bangladesh":"\\uD83C\\uDDE7\\uD83C\\uDDE9","Philippines":"\\uD83C\\uDDF5\\uD83C\\uDDED","Thailand":"\\uD83C\\uDDF9\\uD83C\\uDDED","Sri Lanka":"\\uD83C\\uDDF1\\uD83C\\uDDF0","Nepal":"\\uD83C\\uDDF3\\uD83C\\uDDF5","PNG":"\\uD83C\\uDDF5\\uD83C\\uDDEC"};
const THEME_GRADS = {"Digital ID":"linear-gradient(135deg,#4c1d95,#7c3aed)","DPI":"linear-gradient(135deg,#1e3a5f,#2563eb)","AI":"linear-gradient(135deg,#064e3b,#10b981)","Data Exchange":"linear-gradient(135deg,#78350f,#d97706)","Political Instability":"linear-gradient(135deg,#7f1d1d,#dc2626)","Digital Leaders":"linear-gradient(135deg,#581c87,#9333ea)","Digital":"linear-gradient(135deg,#0c4a6e,#0284c7)"};
const THEME_ICONS = {"Digital ID":"\\uD83E\\uDEAA","DPI":"\\uD83C\\uDFD7\\uFE0F","AI":"\\uD83E\\uDD16","Data Exchange":"\\uD83D\\uDD04","Political Instability":"\\u26A0\\uFE0F","Digital Leaders":"\\uD83D\\uDC64","Digital":"\\uD83D\\uDCBB"};
const THEME_CLS = {"Digital ID":"theme-digital-id","DPI":"theme-dpi","AI":"theme-ai","Data Exchange":"theme-data-exchange","Political Instability":"theme-political","Digital Leaders":"theme-digital-leaders","Digital":"theme-digital"};
const COUNTRY_TABS = [{id:"all",label:"All Countries",flag:"\\uD83C\\uDF0F"}].concat(COUNTRIES.map(c=>({id:c,label:c,flag:COUNTRY_FLAGS[c]||"\\uD83C\\uDF0F"})));
const SOURCES_LIST = ["Reuters","Associated Press (AP)","BBC","Jakarta Post","Kompas","Bisnis Indonesia","The Daily Star (BD)","Nation Thailand","Kathmandu Post","Rising Nepal Daily","The PNG Sun","GovInsider Asia","Biometric Update","Tech Policy Press","Chatham House","World Bank","UNESCAP","UIDAI","MeitY","Reserve Bank of India","Bank Indonesia","Kominfo","PSA Philippines","DICT Philippines","BSP Philippines","ETDA Thailand","ID Tech Wire","India Policy Hub","Voice & Data","Global Voices"];
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function grad(t){return THEME_GRADS[t]||THEME_GRADS["Digital"]}
function icon(t){return THEME_ICONS[t]||THEME_ICONS["Digital"]}
function cls(t){return THEME_CLS[t]||"theme-digital"}
function flag(c){return COUNTRY_FLAGS[c]||"\\uD83C\\uDF0F"}
function cardHTML(a,featured){
  const cl=featured?"card featured":"card";
  return `<article class="${cl}" onclick="window.open('${esc(a.url)}','_blank')">
    <div class="thumb"><div class="thumb-bg" style="background:${grad(a.theme)}"><span style="position:relative;z-index:1">${icon(a.theme)}</span></div><span class="thumb-flag">${flag(a.country)}</span></div>
    <div class="card-body">
      <div class="card-meta"><span class="badge ${cls(a.theme)}">${esc(a.theme)}</span><span class="card-country">${esc(a.country)}</span>${a.date?`<span class="card-date">${esc(a.date)}</span>`:""}
      </div>
      <h2 class="card-headline">${esc(a.title||a.headline||"")}</h2>
      <p class="card-summary">${esc(a.summary||"")}</p>
      ${a.source?`<p class="card-source">Source: ${esc(a.source)}</p>`:""}
      <a class="card-link" href="${esc(a.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">Read full story <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 6h10M6 1l5 5-5 5"/></svg></a>
    </div>
  </article>`;
}
function buildTabs(){
  document.getElementById("tabs").innerHTML=COUNTRY_TABS.map(c=>`<button class="tab${c.id==="all"?" active":""}" onclick="filter('${c.id}',this)">${c.flag} ${c.label}</button>`).join("");
}
function buildGrid(country){
  const main=document.getElementById("main");
  const pool=country==="all"?ARTICLES:ARTICLES.filter(a=>a.country===country);
  if(!pool.length){main.innerHTML=`<div class="empty"><h3>No articles found</h3><p>Check back after the next daily update.</p></div>`;return;}
  let html="";
  if(country==="all"){
    COUNTRIES.forEach(c=>{
      const arts=ARTICLES.filter(a=>a.country===c);
      if(!arts.length)return;
      html+=`<div class="country-divider"><span class="flag">${flag(c)}</span><h2>${esc(c)}</h2><div class="line"></div></div><div class="grid">`;
      arts.forEach((a,i)=>{html+=cardHTML(a,i===0)});
      html+=`</div>`;
    });
  } else {
    html=`<div class="grid">`;
    pool.forEach((a,i)=>{html+=cardHTML(a,i===0)});
    html+=`</div>`;
  }
  main.innerHTML=html;
}
function buildSources(){
  document.getElementById("sources").innerHTML=`<h3>News Sources</h3><div class="sources-grid">${SOURCES_LIST.map(s=>`<span class="source-tag">${esc(s)}</span>`).join("")}</div><p class="footer-copy">Auto-updated daily via GitHub Actions &middot; Google News RSS &middot; Updated __UPDATE_TIME__</p>`;
}
function filter(country,btn){
  document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
  btn.classList.add("active");
  buildGrid(country);
  document.getElementById("main").scrollIntoView({behavior:"smooth",block:"start"});
}
buildTabs();buildGrid("all");buildSources();
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
