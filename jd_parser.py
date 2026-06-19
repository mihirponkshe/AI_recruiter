# jd_parser.py
# Hardcoded JD configuration — parsed once offline, used by scorer.py

JD_CONFIG = {
    # Must-have skills (any candidate lacking these gets heavy penalty)
    "must_have_skills": [
        "embeddings", "sentence-transformers", "vector database",
        "pinecone", "weaviate", "qdrant", "milvus", "faiss",
        "opensearch", "elasticsearch", "hybrid search",
        "retrieval", "ranking", "information retrieval",
        "python", "evaluation", "ndcg", "mrr", "a/b testing",
        "production ml", "applied ml"
    ],
    # Nice-to-have (bonus, not required)
    "nice_to_have_skills": [
        "lora", "qlora", "peft", "fine-tuning", "llm", "rag",
        "xgboost", "learning to rank", "distributed systems",
        "open source", "pytorch", "transformers", "bert", "bge", "e5"
    ],
    # These in the title/career → strong positive signal
    "positive_titles": [
        "ml engineer", "ai engineer", "applied scientist",
        "research engineer", "senior engineer", "nlp engineer",
        "search engineer", "data scientist", "ai researcher",
        "machine learning engineer", "senior ml engineer",
        "senior ai engineer", "staff engineer", "principal engineer",
        "applied ml engineer", "deep learning engineer",
    ],
    # Hard disqualifiers
    "disqualifier_companies": [
        "tcs", "infosys", "wipro", "accenture", "cognizant",
        "capgemini", "hcl", "tech mahindra", "mphasis", "hexaware",
        "mindtree", "ltimindtree", "lti", "l&t infotech",
        "persistent", "cyient", "zensar", "birlasoft",
    ],
    "disqualifier_industries": [
        "consulting", "it services", "bpo", "outsourcing",
        "staffing", "recruitment", "human resources",
    ],
    "disqualifier_titles": [
        "marketing", "hr", "graphic design", "content writer",
        "business analyst", "project manager", "sales",
        "computer vision", "speech recognition", "robotics",
        "accountant", "operations manager", "civil engineer",
        "mechanical engineer", "customer support", "sales executive",
    ],
    # Location scoring
    "top_locations": [
        "pune", "noida", "hyderabad", "mumbai", "delhi", "ncr",
        "bangalore", "bengaluru", "gurgaon", "gurugram",
    ],
    # Experience band
    "exp_min": 5,
    "exp_max": 9,
    "exp_ideal_min": 6,
    "exp_ideal_max": 8,
    # Salary budget (from JD context: Series A, senior role)
    "salary_budget_max_lpa": 50,

    # ── Text analysis keywords (for headline + summary scoring) ──────────
    # High-signal terms: directly relevant to the JD role
    "text_high_signal_terms": [
        "ranking", "retrieval", "information retrieval", "search engine",
        "vector search", "vector database", "semantic search",
        "embedding", "embeddings", "sentence-transformer",
        "reranking", "re-ranking", "hybrid search",
        "faiss", "pinecone", "qdrant", "weaviate", "milvus",
        "opensearch", "elasticsearch", "solr", "lucene",
        "ndcg", "mrr", "recall@k", "precision@k",
        "recommendation system", "recommendation engine",
        "learning to rank", "bm25", "tf-idf",
        "dense retrieval", "sparse retrieval",
        "rag", "retrieval augmented",
    ],
    # Medium-signal terms: related ML/NLP but not core IR
    "text_medium_signal_terms": [
        "nlp", "natural language processing", "text classification",
        "named entity", "sentiment analysis", "text mining",
        "transformers", "bert", "gpt", "llm", "large language model",
        "fine-tuning", "fine tuning", "lora", "qlora", "peft",
        "pytorch", "tensorflow", "hugging face", "huggingface",
        "production ml", "mlops", "model deployment",
        "feature engineering", "a/b testing", "ab testing",
        "applied ml", "applied machine learning",
        "data pipeline", "real-time inference",
    ],
    # Production deployment terms (bonus)
    "text_production_terms": [
        "production", "deployed", "shipped", "launched",
        "real users", "live system", "served", "at scale",
        "millions of", "thousands of", "api endpoint",
        "latency", "throughput", "sla", "monitoring",
        "ci/cd", "docker", "kubernetes", "k8s",
    ],

    # ── Education config ─────────────────────────────────────────────────
    "relevant_fields_of_study": [
        "computer science", "computer engineering", "software engineering",
        "information technology", "data science", "artificial intelligence",
        "machine learning", "electrical engineering", "electronics",
        "mathematics", "statistics", "computational",
        "information systems", "cs", "cse", "ece", "eee", "it",
    ],
}
