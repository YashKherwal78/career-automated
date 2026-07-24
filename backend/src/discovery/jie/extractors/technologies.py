import re
from typing import List, Dict

# Canonical Technologies Registry & Alias mapping
TECH_REGISTRY: Dict[str, str] = {
    # Programming Languages
    "python": "Python", "python3": "Python", "py": "Python",
    "java": "Java",
    "c++": "C++", "cpp": "C++", "c plus plus": "C++",
    "c#": "C#", "csharp": "C#",
    "golang": "Go", "go lang": "Go", "go": "Go",
    "rust": "Rust",
    "javascript": "JavaScript", "js": "JavaScript",
    "typescript": "TypeScript", "ts": "TypeScript",
    "ruby": "Ruby", "rails": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "sql": "SQL",
    
    # Frontend
    "react": "React", "reactjs": "React", "react.js": "React",
    "next.js": "Next.js", "nextjs": "Next.js",
    "angular": "Angular", "angularjs": "Angular",
    "vue": "Vue", "vue.js": "Vue", "vuejs": "Vue",
    "svelte": "Svelte",
    "tailwind": "Tailwind CSS", "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "html": "HTML5", "html5": "HTML5",
    "css": "CSS3", "css3": "CSS3",
    
    # Backend / Frameworks
    "fastapi": "FastAPI", "fast api": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "spring": "Spring Boot", "spring boot": "Spring Boot",
    "express": "Express", "express.js": "Express", "expressjs": "Express",
    "nest.js": "NestJS", "nestjs": "NestJS",
    "laravel": "Laravel",
    "rails": "Ruby on Rails", "ruby on rails": "Ruby on Rails",
    
    # Databases
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "redis": "Redis",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "neo4j": "Neo4j",
    
    # Infrastructure & DevOps
    "docker": "Docker",
    "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "kafka": "Apache Kafka", "apache kafka": "Apache Kafka",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "jenkins": "Jenkins",
    "github actions": "GitHub Actions",
    "ci/cd": "CI/CD", "cicd": "CI/CD",
    
    # Cloud
    "aws": "AWS", "amazon web services": "AWS",
    "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
    "azure": "Azure", "microsoft azure": "Azure",
    
    # AI & ML
    "tensorflow": "TensorFlow", "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "langchain": "LangChain",
    "pinecone": "Pinecone",
    "faiss": "FAISS",
    "chroma": "Chroma", "chromadb": "Chroma",
    "openai": "OpenAI",
    "llm": "LLMs", "llms": "LLMs",
    "scikit-learn": "Scikit-Learn", "sklearn": "Scikit-Learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "huggingface": "Hugging Face", "hugging face": "Hugging Face"
}

def extract_technologies(text: str) -> List[str] :
    """Extracts and normalizes technologies based on canonical tech registry."""
    extracted = set()
    text_lower = text.lower()
    
    # Check boundaries for word matches to prevent false positives (e.g. 'go' inside 'good')
    for raw, canonical in TECH_REGISTRY.items():
        # Escape specific tech terms containing special characters (like c++, c#)
        pattern = r'\b' + re.escape(raw) + r'\b'
        if "+" in raw or "#" in raw:
            # Special boundaries handling for c++ and c#
            pattern = re.escape(raw)
            
        if re.search(pattern, text_lower):
            extracted.add(canonical)
            
    return sorted(list(extracted))
