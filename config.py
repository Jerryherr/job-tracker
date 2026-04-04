"""
Configuration: vertical domain keywords and job category keywords.
All matching is case-insensitive on job title + stripped JD text.
"""

# ── Vertical industry domains ─────────────────────────────────────────────────
VERTICAL_DOMAINS = {
    "finance": {
        "label": "金融 / Fintech",
        "color": "#2196F3",
        "keywords": [
            "finance", "financial services", "banking", "bank", "trading",
            "fintech", "investment", "payments", "payment processing",
            "insurance", "insurtech", "accounting", "wealth management",
            "asset management", "hedge fund", "equity", "credit", "loan",
            "capital markets", "treasury", "risk management", "quant",
            "portfolio", "brokerage", "mortgage",
        ],
    },
    "healthcare": {
        "label": "医疗 / 健康",
        "color": "#4CAF50",
        "keywords": [
            "healthcare", "medical", "health system", "clinical", "pharma",
            "pharmaceutical", "biotech", "biotechnology", "hospital",
            "physician", "therapy", "therapeutics", "drug discovery",
            "patient", "biomedicine", "life sciences", "genomics",
            "radiology", "ehr", "electronic health record", "hipaa",
            "care delivery", "health plan", "payer", "provider",
        ],
    },
    "legal": {
        "label": "法律 / 合规",
        "color": "#FF9800",
        "keywords": [
            "legal tech", "legaltech", "law firm", "litigation support",
            "e-discovery", "contract management", "legal document",
            "legal research", "regulatory compliance platform",
        ],
    },
    "education": {
        "label": "教育 / EdTech",
        "color": "#9C27B0",
        "keywords": [
            "edtech", "education technology", "learning platform",
            "k-12", "higher education", "university", "curriculum",
            "tutoring", "e-learning", "learning management",
            "student", "classroom", "academic institution",
        ],
    },
    "government": {
        "label": "政府 / 国防",
        "color": "#607D8B",
        "keywords": [
            "government", "defense", "military", "federal agency",
            "public sector", "national security", "intelligence community",
            "dod", "department of defense", "civilian government",
            "law enforcement", "public safety",
        ],
    },
    "retail": {
        "label": "零售 / 电商",
        "color": "#FF5722",
        "keywords": [
            "retail", "e-commerce", "ecommerce", "consumer goods", "cpg",
            "supply chain", "logistics", "fulfillment", "inventory",
            "merchandising", "brick and mortar",
        ],
    },
    "energy": {
        "label": "能源 / 气候",
        "color": "#00BCD4",
        "keywords": [
            "energy", "oil and gas", "renewable energy", "climate tech",
            "sustainability", "cleantech", "carbon", "power grid",
            "utilities", "solar", "wind energy", "electric vehicle",
            "grid management",
        ],
    },
    "real_estate": {
        "label": "房地产",
        "color": "#795548",
        "keywords": [
            "real estate", "proptech", "property management",
            "construction tech", "architecture", "commercial real estate",
        ],
    },
    "media_entertainment": {
        "label": "媒体 / 娱乐",
        "color": "#E91E63",
        "keywords": [
            "media", "entertainment", "gaming", "game studio", "film",
            "music industry", "publishing", "adtech", "advertising technology",
            "content creation", "streaming",
        ],
    },
}

# ── Job function categories ───────────────────────────────────────────────────
# Ordered by priority — first match wins when title matches multiple.
JOB_CATEGORIES = [
    {
        "key": "research",
        "label": "Research",
        "color": "#673AB7",
        "keywords": [
            "research scientist", "research engineer", "researcher",
            "postdoc", "fellowship", "fundamental research",
            "alignment researcher", "interpretability",
        ],
    },
    {
        "key": "ml_ai",
        "label": "ML / AI Engineering",
        "color": "#3F51B5",
        "keywords": [
            "machine learning", "ml engineer", "ai engineer",
            "deep learning", "nlp engineer", "computer vision engineer",
            "reinforcement learning", "llm", "model training",
            "inference engineer", "pretraining",
        ],
    },
    {
        "key": "software_engineering",
        "label": "Software Engineering",
        "color": "#2196F3",
        "keywords": [
            "software engineer", "software developer", "backend engineer",
            "frontend engineer", "full stack", "fullstack",
            "infrastructure engineer", "platform engineer",
            "systems engineer", "devops", "site reliability",
            "sre", "mobile engineer",
        ],
    },
    {
        "key": "security",
        "label": "Security",
        "color": "#F44336",
        "keywords": [
            "security engineer", "cybersecurity", "information security",
            "infosec", "red team", "penetration testing",
            "trust & safety", "trust and safety",
        ],
    },
    {
        "key": "data",
        "label": "Data / Analytics",
        "color": "#00BCD4",
        "keywords": [
            "data scientist", "data analyst", "data engineer",
            "analytics engineer", "business intelligence", "bi analyst",
        ],
    },
    {
        "key": "product",
        "label": "Product / Design",
        "color": "#FF5722",
        "keywords": [
            "product manager", "product designer", "ux designer",
            "ui designer", "design", "user experience", "user research",
            "product lead",
        ],
    },
    {
        "key": "operations",
        "label": "Operations / Program Mgmt",
        "color": "#FF9800",
        "keywords": [
            "operations manager", "program manager", "project manager",
            "chief of staff", "strategy", "business operations",
            "technical program manager", "tpm",
        ],
    },
    {
        "key": "go_to_market",
        "label": "Sales / Marketing / BD",
        "color": "#E91E63",
        "keywords": [
            "sales", "marketing", "business development", "account manager",
            "account executive", "customer success", "partnerships",
            "growth", "revenue", "solutions engineer", "field engineer",
        ],
    },
    {
        "key": "policy_legal",
        "label": "Policy / Legal / Ethics",
        "color": "#607D8B",
        "keywords": [
            "policy", "legal counsel", "attorney", "lawyer",
            "government relations", "public affairs", "ethics",
            "responsible ai", "safety policy",
        ],
    },
    {
        "key": "finance_hr",
        "label": "Finance / HR / Recruiting",
        "color": "#795548",
        "keywords": [
            "financial analyst", "controller", "accounting",
            "human resources", "hr", "recruiter", "recruiting",
            "talent acquisition", "people operations", "payroll",
            "compensation", "benefits",
        ],
    },
]

# ── Companies ─────────────────────────────────────────────────────────────────
COMPANIES = {
    "openai": {
        "label": "OpenAI",
        "api_type": "ashby",            # uses Ashby HQ
        "ashby_board": "openai",
        "color": "#10a37f",
        "careers_url": "https://openai.com/careers/search/",
    },
    "anthropic": {
        "label": "Anthropic",
        "api_type": "greenhouse",       # uses Greenhouse
        "greenhouse_board": "anthropic",
        "color": "#d97757",
        "careers_url": "https://www.anthropic.com/careers/jobs",
    },
}

DB_PATH = "data/jobs.db"
REPORTS_DIR = "reports"
