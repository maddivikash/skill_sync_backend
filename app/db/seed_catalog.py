"""Seed data for the suggestion catalog (100+ roles, tech + non-tech).

Built from domain FAMILIES + a ROLES list (with seniority variants) so every
role gets relevant skills/tools/courses without hand-writing 100 dicts.

Runtime reads from the DB, never this file. Seeding (see app/db/seed_run.py,
called once from entrypoint.sh) is ADDITIVE + idempotent: it inserts any roles
or items that don't already exist, so expanding this file adds data on the next
boot without duplicating or wiping rows.
"""
from sqlalchemy.orm import Session

from app.models.catalog import CatalogItem, CatalogRole


def _c(name, provider, hours, url, desc=None):
    return {"name": name, "provider": provider, "estimated_hours": hours, "url": url, "description": desc}


def _p(name, desc, steps):
    return {"name": name, "description": desc, "steps": steps}


# Added to any "senior/lead/staff/principal/manager" role.
SENIOR_SKILLS = ["System design at scale", "Architecture & trade-offs", "Mentoring & code review", "Technical leadership", "Stakeholder communication"]
SENIOR_COURSES = [
    _c("Grokking the System Design Interview", "DesignGurus", 25, "https://www.designgurus.io/course/grokking-the-system-design-interview"),
    _c("Designing Data-Intensive Applications (book)", "Martin Kleppmann", 30, "https://dataintensive.net/"),
]
SENIOR_PROJECT = _p("Write & defend an architecture RFC", "Design a system and get it reviewed.", ["Define requirements", "Draft design + trade-offs", "Diagram", "Review with peers"])


FAM: dict = {
    "software": {
        "skills": ["A primary language (Python/Java/Go)", "Data structures & algorithms", "Git & code review", "Testing", "Debugging", "Databases & SQL", "Clean code"],
        "tools": ["VS Code", "Git/GitHub", "Docker", "PostgreSQL", "Postman", "Linux"],
        "courses": [
            _c("CS50x: Intro to Computer Science", "Harvard / edX", 100, "https://cs50.harvard.edu/x/"),
            _c("The Odin Project", "The Odin Project", 200, "https://www.theodinproject.com/"),
            _c("Grokking Coding Interview Patterns", "DesignGurus", 40, "https://www.designgurus.io/course/grokking-the-coding-interview"),
        ],
        "projects": [_p("Ship a full app", "Build & deploy end to end.", ["Design", "Build API", "Build UI", "Test", "Deploy"])],
    },
    "frontend": {
        "skills": ["HTML & semantics", "Modern CSS", "JavaScript (ES2020+)", "React", "TypeScript", "Accessibility", "Web performance"],
        "tools": ["React", "TypeScript", "Vite", "Tailwind CSS", "Chrome DevTools", "Figma"],
        "courses": [
            _c("The Joy of React", "Josh W. Comeau", 30, "https://www.joyofreact.com/"),
            _c("JavaScript: The Advanced Concepts", "Udemy (ZTM)", 25, "https://www.udemy.com/course/advanced-javascript-concepts/"),
            _c("CSS for JavaScript Developers", "Josh W. Comeau", 40, "https://css-for-js.dev/"),
        ],
        "projects": [_p("Component library", "Reusable, accessible UI kit.", ["Design tokens", "Core components", "Storybook", "Publish"])],
    },
    "backend": {
        "skills": ["A backend language", "REST API design", "SQL & data modeling", "Auth & security", "Caching", "Testing", "Message queues"],
        "tools": ["FastAPI / Spring / Express", "PostgreSQL", "Redis", "Docker", "Postman", "OpenAPI"],
        "courses": [
            _c("FastAPI - The Complete Course", "Udemy (Eric Roby)", 22, "https://www.udemy.com/course/fastapi-the-complete-course/"),
            _c("Databases & SQL", "Stanford Online / edX", 30, "https://www.edx.org/learn/relational-databases"),
            _c("Designing RESTful APIs", "Udacity", 15, "https://www.udacity.com/course/designing-restful-apis--ud388"),
        ],
        "projects": [_p("Build a production API", "REST service with auth.", ["Schema", "CRUD", "Auth", "Rate limit", "Deploy"])],
    },
    "fullstack": {
        "skills": ["Frontend (React)", "Backend APIs", "Databases", "Auth", "Deployment / CI-CD", "System design basics"],
        "tools": ["React", "Node.js / FastAPI", "PostgreSQL", "Docker", "GitHub Actions", "Vercel"],
        "courses": [
            _c("Full Stack Open", "University of Helsinki", 120, "https://fullstackopen.com/en/"),
            _c("The Odin Project - Full Stack", "The Odin Project", 200, "https://www.theodinproject.com/"),
            _c("Docker & Kubernetes: Practical Guide", "Udemy (Academind)", 23, "https://www.udemy.com/course/docker-kubernetes-the-practical-guide/"),
        ],
        "projects": [_p("SaaS starter", "Auth + billing + dashboard.", ["Auth", "DB schema", "Dashboard", "Billing", "Deploy"])],
    },
    "mobile": {
        "skills": ["A mobile framework", "Mobile UI patterns", "State management", "Offline storage", "Push notifications", "App store release"],
        "tools": ["React Native / Flutter", "Expo", "Firebase", "Xcode", "Android Studio"],
        "courses": [
            _c("React Native - The Practical Guide", "Udemy (Academind)", 28, "https://www.udemy.com/course/react-native-the-practical-guide/"),
            _c("Flutter & Dart - Complete Guide", "Udemy (Academind)", 40, "https://www.udemy.com/course/learn-flutter-dart-to-build-ios-android-apps/"),
        ],
        "projects": [_p("Cross-platform app", "Ship to both stores.", ["Design", "Build", "Persist data", "Publish"])],
    },
    "android": {
        "skills": ["Kotlin", "Jetpack Compose", "Android SDK", "Coroutines", "MVVM", "Room"],
        "tools": ["Kotlin", "Android Studio", "Jetpack Compose", "Gradle", "Firebase"],
        "courses": [
            _c("Android Basics with Compose", "Google", 60, "https://developer.android.com/courses/android-basics-compose/course"),
            _c("Jetpack Compose - Complete Guide", "Udemy (Academind)", 25, "https://www.udemy.com/course/jetpack-compose-the-complete-guide/"),
        ],
        "projects": [_p("Native Android app", "Compose + MVVM.", ["Compose UI", "ViewModel", "Room DB", "Publish"])],
    },
    "ios": {
        "skills": ["Swift", "SwiftUI", "UIKit basics", "async/await", "Core Data", "App Store release"],
        "tools": ["Swift", "Xcode", "SwiftUI", "TestFlight", "Instruments"],
        "courses": [
            _c("100 Days of SwiftUI", "Hacking with Swift", 100, "https://www.hackingwithswift.com/100/swiftui"),
            _c("iOS & Swift - Complete Bootcamp", "Udemy (Angela Yu)", 55, "https://www.udemy.com/course/ios-13-app-development-bootcamp/"),
        ],
        "projects": [_p("Native iOS app", "SwiftUI end to end.", ["Views", "State", "Persistence", "TestFlight"])],
    },
    "devops": {
        "skills": ["Linux", "Docker", "Kubernetes", "CI/CD", "Infrastructure as Code", "Cloud (AWS)", "Monitoring"],
        "tools": ["Docker", "Kubernetes", "Terraform", "GitHub Actions", "AWS", "Prometheus"],
        "courses": [
            _c("AWS Certified Solutions Architect - Associate", "Udemy (Stephane Maarek)", 27, "https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/"),
            _c("Kubernetes for the Absolute Beginners", "KodeKloud", 12, "https://kodekloud.com/courses/kubernetes-for-the-absolute-beginners-hands-on/"),
            _c("Terraform Associate", "HashiCorp Learn", 15, "https://developer.hashicorp.com/terraform/tutorials"),
        ],
        "projects": [_p("Deploy an app to the cloud", "Container to production.", ["Dockerize", "Push to registry", "Deploy", "Add alarms", "Autoscale"])],
    },
    "cloud": {
        "skills": ["Cloud services (AWS/GCP/Azure)", "Networking (VPC)", "IAM & security", "IaC", "Cost optimization", "High availability"],
        "tools": ["AWS", "Terraform", "CloudFormation", "Draw.io", "Kubernetes"],
        "courses": [
            _c("AWS Certified Solutions Architect - Associate", "Udemy (Stephane Maarek)", 27, "https://www.udemy.com/course/aws-certified-solutions-architect-associate-saa-c03/"),
            _c("Google Cloud Professional Cloud Architect", "Coursera (Google Cloud)", 40, "https://www.coursera.org/professional-certificates/gcp-cloud-architect"),
            _c("AWS Well-Architected", "AWS Skill Builder", 8, "https://aws.amazon.com/architecture/well-architected/"),
        ],
        "projects": [_p("Design a scalable architecture", "Diagram + IaC.", ["Requirements", "Diagram", "IaC", "Cost estimate"])],
    },
    "sre": {
        "skills": ["SLIs/SLOs & error budgets", "Observability", "Incident response", "Linux internals", "Automation", "Capacity planning"],
        "tools": ["Prometheus", "Grafana", "PagerDuty", "Kubernetes", "OpenTelemetry"],
        "courses": [
            _c("Google SRE Book", "Google", 25, "https://sre.google/books/"),
            _c("SRE: Measuring & Managing Reliability", "Coursera (Google Cloud)", 15, "https://www.coursera.org/learn/site-reliability-engineering-slos"),
        ],
        "projects": [_p("Observability stack", "Instrument a service.", ["Metrics", "Dashboards", "SLO alerts", "Runbook"])],
    },
    "network": {
        "skills": ["TCP/IP & DNS", "Routing & switching", "Firewalls & VPN", "Linux networking", "Load balancing", "Troubleshooting"],
        "tools": ["Wireshark", "Cisco IOS", "pfSense", "nmap", "Ansible"],
        "courses": [
            _c("Cisco CCNA", "Udemy (Neil Anderson)", 30, "https://www.udemy.com/course/ccna-complete/"),
            _c("Computer Networking", "Coursera (Google IT)", 25, "https://www.coursera.org/learn/computer-networking"),
        ],
        "projects": [_p("Home lab network", "Design & secure a network.", ["Topology", "VLANs", "Firewall rules", "Monitoring"])],
    },
    "dba": {
        "skills": ["SQL tuning", "Indexing & query plans", "Backup & recovery", "Replication", "Security & roles", "Monitoring"],
        "tools": ["PostgreSQL", "MySQL", "pgAdmin", "Percona Toolkit", "Prometheus"],
        "courses": [
            _c("PostgreSQL for Everybody", "Coursera (Michigan)", 40, "https://www.coursera.org/specializations/postgresql-for-everybody"),
            _c("High Performance PostgreSQL", "Udemy", 10, "https://www.udemy.com/course/postgresql-high-performance/"),
        ],
        "projects": [_p("Tune a slow database", "Diagnose & optimize.", ["Find slow queries", "Index", "Analyze plans", "Backups"])],
    },
    "security": {
        "skills": ["Network security", "Web security (OWASP)", "Cryptography basics", "Threat modeling", "Incident response", "Cloud security"],
        "tools": ["Burp Suite", "Wireshark", "Nmap", "Metasploit", "Kali Linux"],
        "courses": [
            _c("Web Security Academy", "PortSwigger", 40, "https://portswigger.net/web-security"),
            _c("Introduction to Cyber Security", "TryHackMe", 30, "https://tryhackme.com/path/outline/introtocyber"),
            _c("The Complete Cyber Security Course", "Udemy (Nathan House)", 30, "https://www.udemy.com/course/the-complete-internet-security-privacy-course-volume-1/"),
        ],
        "projects": [_p("CTF write-ups", "Practice real exploits.", ["Pick room", "Recon", "Exploit", "Document mitigation"])],
    },
    "appsec": {
        "skills": ["Secure coding", "OWASP Top 10", "Threat modeling", "SAST/DAST", "Code review for security", "Dependency scanning"],
        "tools": ["Burp Suite", "OWASP ZAP", "Semgrep", "Snyk", "Git"],
        "courses": [
            _c("Web Security Academy", "PortSwigger", 40, "https://portswigger.net/web-security"),
            _c("Secure Coding Practices", "Coursera (UC Davis)", 20, "https://www.coursera.org/specializations/secure-coding-practices"),
        ],
        "projects": [_p("Secure an app", "Find & fix vulns.", ["Threat model", "Run SAST/DAST", "Fix findings", "Add CI checks"])],
    },
    "data-science": {
        "skills": ["Python for data", "Statistics & probability", "pandas & NumPy", "Machine learning", "Data visualization", "Model evaluation"],
        "tools": ["Python", "Jupyter", "pandas", "scikit-learn", "Matplotlib"],
        "courses": [
            _c("Machine Learning Specialization", "Coursera (Andrew Ng)", 60, "https://www.coursera.org/specializations/machine-learning-introduction"),
            _c("Data Analysis with Python", "freeCodeCamp", 30, "https://www.freecodecamp.org/learn/data-analysis-with-python/"),
            _c("Statistics with Python", "Coursera (Michigan)", 30, "https://www.coursera.org/specializations/statistics-with-python"),
        ],
        "projects": [_p("End-to-end ML model", "Data to prediction.", ["Explore data", "Features", "Train & evaluate", "Serve"])],
    },
    "ml": {
        "skills": ["ML algorithms", "Deep learning", "PyTorch/TensorFlow", "Feature engineering", "Model deployment", "Evaluation & metrics"],
        "tools": ["Python", "PyTorch", "scikit-learn", "Hugging Face", "MLflow"],
        "courses": [
            _c("Practical Deep Learning for Coders", "fast.ai", 50, "https://course.fast.ai/"),
            _c("Deep Learning Specialization", "Coursera (DeepLearning.AI)", 80, "https://www.coursera.org/specializations/deep-learning"),
        ],
        "projects": [_p("Train & deploy a model", "Real ML pipeline.", ["Dataset", "Train", "Evaluate", "Serve via API"])],
    },
    "ai-llm": {
        "skills": ["Prompt engineering", "RAG", "Vector databases", "LLM APIs & agents", "Fine-tuning basics", "Evaluation & guardrails"],
        "tools": ["Python", "LangChain / LlamaIndex", "OpenAI / Anthropic APIs", "pgvector / Pinecone", "Hugging Face"],
        "courses": [
            _c("ChatGPT Prompt Engineering for Developers", "DeepLearning.AI", 3, "https://www.deeplearning.ai/short-courses/chatgpt-prompt-engineering-for-developers/"),
            _c("LangChain for LLM App Development", "DeepLearning.AI", 4, "https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/"),
            _c("Building & Evaluating Advanced RAG", "DeepLearning.AI", 3, "https://www.deeplearning.ai/short-courses/building-evaluating-advanced-rag/"),
        ],
        "projects": [_p("RAG chatbot over your docs", "Grounded Q&A.", ["Chunk docs", "Embed", "Retrieval + LLM", "Citations", "Deploy"])],
    },
    "mlops": {
        "skills": ["ML pipelines", "Model serving", "Experiment tracking", "CI/CD for ML", "Monitoring & drift", "Containers"],
        "tools": ["MLflow", "Docker", "Kubernetes", "Airflow", "DVC"],
        "courses": [
            _c("MLOps Zoomcamp", "DataTalks.Club", 80, "https://github.com/DataTalksClub/mlops-zoomcamp"),
            _c("ML Engineering for Production (MLOps)", "Coursera (DeepLearning.AI)", 40, "https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops"),
        ],
        "projects": [_p("End-to-end ML pipeline", "Train→track→deploy→monitor.", ["Pipeline", "Track", "Serve", "Monitor drift"])],
    },
    "data-eng": {
        "skills": ["SQL (advanced)", "Python", "ETL / ELT", "Data warehousing", "Orchestration", "Streaming basics", "Data modeling"],
        "tools": ["SQL", "Airflow", "dbt", "Spark", "Snowflake", "Kafka"],
        "courses": [
            _c("Data Engineering Zoomcamp", "DataTalks.Club", 80, "https://github.com/DataTalksClub/data-engineering-zoomcamp"),
            _c("The Complete SQL Bootcamp", "Udemy (Jose Portilla)", 9, "https://www.udemy.com/course/the-complete-sql-bootcamp/"),
            _c("dbt Fundamentals", "dbt Labs", 6, "https://learn.getdbt.com/courses/dbt-fundamentals"),
        ],
        "projects": [_p("Build an ETL pipeline", "Ingest→transform→load.", ["Ingest", "Transform (dbt)", "Warehouse", "Schedule"])],
    },
    "data-analyst": {
        "skills": ["SQL", "Excel / Sheets", "Data visualization", "Statistics", "Dashboarding (BI)", "Storytelling with data"],
        "tools": ["SQL", "Tableau", "Power BI", "Excel", "Python (pandas)"],
        "courses": [
            _c("Google Data Analytics Certificate", "Coursera (Google)", 120, "https://www.coursera.org/professional-certificates/google-data-analytics"),
            _c("The Complete SQL Bootcamp", "Udemy (Jose Portilla)", 9, "https://www.udemy.com/course/the-complete-sql-bootcamp/"),
            _c("Tableau A-Z", "Udemy (Kirill Eremenko)", 9, "https://www.udemy.com/course/tableau10/"),
        ],
        "projects": [_p("Interactive dashboard", "Answer business questions.", ["Gather data", "Clean in SQL", "Dashboard", "Present"])],
    },
    "qa": {
        "skills": ["Test design", "Automation frameworks", "API testing", "CI integration", "Bug reporting", "Performance testing"],
        "tools": ["Playwright / Selenium", "Cypress", "Postman", "pytest / JUnit", "k6"],
        "courses": [
            _c("Playwright Testing", "Playwright Docs", 10, "https://playwright.dev/docs/intro"),
            _c("Selenium WebDriver with Java", "Udemy (Rahul Shetty)", 45, "https://www.udemy.com/course/selenium-real-time-examplesinterview-questions/"),
        ],
        "projects": [_p("E2E test suite", "Automate critical flows.", ["Map flows", "Write tests", "Add to CI", "Report coverage"])],
    },
    "design": {
        "skills": ["Design fundamentals", "Typography & color", "Wireframing", "Prototyping", "User research", "Design systems", "Usability testing"],
        "tools": ["Figma", "Sketch", "Adobe XD", "Maze", "Notion"],
        "courses": [
            _c("Google UX Design Certificate", "Coursera (Google)", 120, "https://www.coursera.org/professional-certificates/google-ux-design"),
            _c("Learn UI Design", "Erik Kennedy", 40, "https://www.learnui.design/"),
            _c("Refactoring UI", "Adam Wathan & Steve Schoger", 8, "https://www.refactoringui.com/"),
        ],
        "projects": [_p("Redesign a real flow", "End to end.", ["Audit UX", "Wireframe", "Hi-fi design", "Prototype & test"])],
    },
    "ux-research": {
        "skills": ["Research methods", "User interviews", "Surveys", "Usability testing", "Synthesis & personas", "Data-informed design"],
        "tools": ["Maze", "Dovetail", "Figma", "Notion", "UserTesting"],
        "courses": [
            _c("Google UX Design Certificate", "Coursera (Google)", 120, "https://www.coursera.org/professional-certificates/google-ux-design"),
            _c("UX Research at Scale", "Coursera / NNg", 20, "https://www.nngroup.com/courses/"),
        ],
        "projects": [_p("Run a research study", "From plan to insights.", ["Plan", "Recruit", "Interview/test", "Synthesize", "Report"])],
    },
    "graphic": {
        "skills": ["Layout & composition", "Typography", "Color theory", "Branding", "Illustration basics", "Print & digital"],
        "tools": ["Adobe Photoshop", "Illustrator", "InDesign", "Figma", "Canva"],
        "courses": [
            _c("Graphic Design Specialization", "Coursera (CalArts)", 60, "https://www.coursera.org/specializations/graphic-design"),
            _c("Adobe Illustrator Masterclass", "Udemy", 12, "https://www.udemy.com/course/adobe-illustrator-cc-advanced-training-course/"),
        ],
        "projects": [_p("Brand identity kit", "Logo + guidelines.", ["Moodboard", "Logo", "Palette & type", "Guidelines"])],
    },
    "embedded": {
        "skills": ["C / C++", "Microcontrollers", "RTOS basics", "Hardware interfacing", "Debugging with logic analyzers", "Low-level optimization"],
        "tools": ["C/C++", "ARM / STM32", "PlatformIO", "Oscilloscope", "Git"],
        "courses": [
            _c("Embedded Systems - Shape The World", "edX (UT Austin)", 60, "https://www.edx.org/learn/embedded-systems"),
            _c("Mastering Microcontroller with STM32", "Udemy (FastBit)", 25, "https://www.udemy.com/course/mastering-microcontroller-with-peripheral-driver-development/"),
        ],
        "projects": [_p("Build an embedded device", "Firmware + hardware.", ["Choose MCU", "Wire peripherals", "Write firmware", "Test"])],
    },
    "game": {
        "skills": ["A game engine (Unity/Godot)", "C# or GDScript", "Game physics", "Gameplay programming", "2D/3D math", "Optimization"],
        "tools": ["Unity", "Godot", "Blender", "C#", "Git LFS"],
        "courses": [
            _c("Complete C# Unity Game Developer 2D", "Udemy (GameDev.tv)", 35, "https://www.udemy.com/course/unitycourse/"),
            _c("Godot 4 Course", "GDQuest", 20, "https://www.gdquest.com/"),
        ],
        "projects": [_p("Ship a small game", "2D game to release.", ["Core mechanic", "Levels", "Polish", "Publish to itch.io"])],
    },
    "blockchain": {
        "skills": ["Solidity", "Smart contract security", "EVM & gas", "Web3 libraries", "DeFi concepts", "Testing contracts"],
        "tools": ["Solidity", "Foundry / Hardhat", "ethers.js", "MetaMask", "Remix"],
        "courses": [
            _c("Solidity & Smart Contract Bootcamp", "freeCodeCamp (Patrick Collins)", 32, "https://www.youtube.com/watch?v=gyMwXuJrbJQ"),
            _c("CryptoZombies", "Loom Network", 15, "https://cryptozombies.io/"),
        ],
        "projects": [_p("Deploy a dApp", "Contract + UI.", ["Write contract", "Test (Foundry)", "Deploy testnet", "web3 UI"])],
    },
    "devrel": {
        "skills": ["Technical communication", "Demos & talks", "Content creation", "Community building", "Developer empathy", "Sample code"],
        "tools": ["Markdown", "GitHub", "OBS / recording", "Notion", "Twitter/X"],
        "courses": [
            _c("Developer Relations foundations", "LinkedIn Learning", 6, "https://www.linkedin.com/learning/"),
            _c("Public Speaking", "Coursera (Washington)", 15, "https://www.coursera.org/learn/public-speaking"),
        ],
        "projects": [_p("Publish a dev tutorial", "Teach a real thing.", ["Pick topic", "Build demo", "Write/record", "Publish & share"])],
    },
    "tech-writing": {
        "skills": ["Clear technical writing", "API documentation", "Docs-as-code", "Information architecture", "Editing", "Diagramming"],
        "tools": ["Markdown", "Docusaurus", "Git", "Swagger/OpenAPI", "Mermaid"],
        "courses": [
            _c("Google Technical Writing Courses", "Google", 10, "https://developers.google.com/tech-writing"),
            _c("Documenting APIs", "idratherbewriting", 25, "https://idratherbewriting.com/learnapidoc/"),
        ],
        "projects": [_p("Document a project", "Real docs.", ["Getting started", "API reference", "Guides", "Contribute PR"])],
    },
    "eng-mgmt": {
        "skills": ["1:1s & coaching", "Delivery & planning", "Hiring & interviewing", "Feedback & performance", "Technical strategy", "Stakeholder management"],
        "tools": ["Jira / Linear", "Notion", "Lattice", "Miro"],
        "courses": [
            _c("The Manager's Path (book)", "Camille Fournier", 12, "https://www.oreilly.com/library/view/the-managers-path/9781491973882/"),
            _c("Engineering Management", "LinkedIn Learning", 8, "https://www.linkedin.com/learning/paths/become-a-manager"),
        ],
        "projects": [_p("Team operating cadence", "Set your team's rhythm.", ["1:1 template", "Planning", "Career ladder", "Feedback loop"])],
    },
    # ---------- Non-tech ----------
    "product": {
        "skills": ["User research", "Roadmapping & prioritization", "Writing PRDs", "Metrics & analytics", "Stakeholder communication", "A/B testing", "Go-to-market"],
        "tools": ["Jira", "Figma", "Amplitude / Mixpanel", "Notion", "Miro"],
        "courses": [
            _c("Digital Product Management", "Coursera (Virginia)", 25, "https://www.coursera.org/specializations/uva-darden-digital-product-management"),
            _c("Become a Product Manager", "Udemy (Cole Mercer)", 13, "https://www.udemy.com/course/become-a-product-manager-learn-the-skills-get-a-job/"),
            _c("Product Management Fundamentals", "Reforge / Product School", 20, "https://www.productschool.com/"),
        ],
        "projects": [_p("Ship a product spec", "Idea → PRD → launch plan.", ["User research", "PRD", "Prioritize", "GTM plan"])],
    },
    "project": {
        "skills": ["Planning & scheduling", "Agile / Scrum", "Risk management", "Stakeholder management", "Budgeting", "Reporting"],
        "tools": ["Jira", "Asana", "MS Project", "Confluence", "Miro"],
        "courses": [
            _c("Google Project Management Certificate", "Coursera (Google)", 120, "https://www.coursera.org/professional-certificates/google-project-management"),
            _c("PMP Certification Prep", "Udemy (Joseph Phillips)", 35, "https://www.udemy.com/course/pmp-pmbok6-35-pdus/"),
            _c("Professional Scrum Master (PSM I)", "Scrum.org", 15, "https://www.scrum.org/professional-scrum-master-i-certification"),
        ],
        "projects": [_p("Run a project end to end", "Plan to delivery.", ["Charter", "Plan & schedule", "Track risks", "Retrospective"])],
    },
    "business": {
        "skills": ["Requirements gathering", "Process modeling", "Data analysis", "Stakeholder interviews", "Documentation (BRD/FRD)", "SQL basics"],
        "tools": ["Excel", "SQL", "Jira", "Visio / Lucidchart", "Power BI"],
        "courses": [
            _c("Business Analysis Fundamentals", "Udemy (Ashan Fernando)", 8, "https://www.udemy.com/course/business-analysis-fundamentals/"),
            _c("Business Analytics Specialization", "Coursera (Wharton)", 40, "https://www.coursera.org/specializations/business-analytics"),
            _c("Excel Skills for Business", "Coursera (Macquarie)", 40, "https://www.coursera.org/specializations/excel"),
        ],
        "projects": [_p("Analyze a business process", "Find & fix inefficiency.", ["Map current state", "Gather requirements", "Recommend", "BRD"])],
    },
    "consulting": {
        "skills": ["Structured problem solving", "Financial modeling", "Market research", "Slide/storytelling", "Client communication", "Frameworks"],
        "tools": ["Excel", "PowerPoint", "Think-cell", "Tableau", "Notion"],
        "courses": [
            _c("Strategy & Game Theory / Business Strategy", "Coursera (Virginia/Darden)", 25, "https://www.coursera.org/specializations/business-strategy"),
            _c("McKinsey Forward / Consulting Approach", "Udemy", 12, "https://www.udemy.com/course/management-consulting-skills/"),
        ],
        "projects": [_p("Case study deck", "Solve a business case.", ["Frame problem", "Analyze", "Recommend", "Executive deck"])],
    },
    "operations": {
        "skills": ["Process optimization", "KPIs & reporting", "Cross-functional coordination", "Data analysis", "Vendor management", "Automation"],
        "tools": ["Excel / Sheets", "SQL", "Notion", "Zapier", "Tableau"],
        "courses": [
            _c("Operations Management", "Coursera (Illinois)", 25, "https://www.coursera.org/learn/operations-management"),
            _c("Six Sigma Yellow Belt", "Coursera (Georgia Tech)", 20, "https://www.coursera.org/specializations/six-sigma-fundamentals"),
        ],
        "projects": [_p("Optimize an operational process", "Measure & improve.", ["Baseline KPIs", "Find bottleneck", "Improve", "Measure impact"])],
    },
    "marketing": {
        "skills": ["Marketing strategy", "Content & copywriting", "SEO/SEM", "Analytics", "Social media", "Email & funnels", "Brand"],
        "tools": ["Google Analytics", "HubSpot", "Meta Ads", "Canva", "Mailchimp", "Ahrefs / SEMrush"],
        "courses": [
            _c("Google Digital Marketing & E-commerce Certificate", "Coursera (Google)", 120, "https://www.coursera.org/professional-certificates/google-digital-marketing-ecommerce"),
            _c("The Complete Digital Marketing Course", "Udemy (Rob Percival)", 22, "https://www.udemy.com/course/learn-digital-marketing-course/"),
            _c("SEO Training Course", "HubSpot Academy", 6, "https://academy.hubspot.com/courses/seo-training"),
        ],
        "projects": [_p("Run a marketing campaign", "Plan → execute → measure.", ["Audience & goals", "Content", "Launch", "Measure ROI"])],
    },
    "sales": {
        "skills": ["Prospecting", "Discovery & qualification", "Objection handling", "Negotiation", "CRM hygiene", "Pipeline management"],
        "tools": ["Salesforce", "HubSpot", "Outreach", "LinkedIn Sales Navigator", "Gong"],
        "courses": [
            _c("Sales Training: Techniques for a Human-Centric Sales", "Coursera (HubSpot)", 25, "https://www.coursera.org/professional-certificates/hubspot-sales-representative"),
            _c("The Complete Sales Skills Master Class", "Udemy", 12, "https://www.udemy.com/course/the-complete-sales-skills-master-class-sales-marketing/"),
        ],
        "projects": [_p("Build a sales playbook", "Repeatable process.", ["ICP", "Outreach scripts", "Discovery flow", "Objection handling"])],
    },
    "customer-success": {
        "skills": ["Onboarding", "Relationship management", "Churn & retention", "Product expertise", "Escalation handling", "Upsell/renewal"],
        "tools": ["Salesforce / Gainsight", "Zendesk", "Intercom", "Notion", "Slack"],
        "courses": [
            _c("Customer Success Manager Certification", "Udemy", 10, "https://www.udemy.com/course/customer-success-manager/"),
            _c("Customer Relationship Management", "Coursera", 15, "https://www.coursera.org/learn/customer-relationship-management"),
        ],
        "projects": [_p("Design an onboarding flow", "Reduce churn.", ["Map journey", "Onboarding plan", "Health score", "QBR template"])],
    },
    "finance": {
        "skills": ["Financial modeling", "Accounting fundamentals", "Valuation", "Excel/Sheets mastery", "Budgeting & forecasting", "Data analysis"],
        "tools": ["Excel", "QuickBooks", "SQL", "Power BI", "Bloomberg"],
        "courses": [
            _c("Financial Markets", "Coursera (Yale)", 30, "https://www.coursera.org/learn/financial-markets-global"),
            _c("Financial Modeling & Valuation (FMVA)", "Corporate Finance Institute", 60, "https://corporatefinanceinstitute.com/certifications/financial-modeling-valuation-analyst-fmva-program/"),
            _c("Introduction to Corporate Finance", "Coursera (Wharton)", 15, "https://www.coursera.org/learn/wharton-finance"),
        ],
        "projects": [_p("Build a 3-statement model", "Model a company.", ["Assumptions", "Income statement", "Balance & cash flow", "Valuation"])],
    },
    "hr": {
        "skills": ["Recruiting & sourcing", "Interviewing", "Employee relations", "HR policy & compliance", "Compensation basics", "People analytics"],
        "tools": ["LinkedIn Recruiter", "Greenhouse / Lever", "Workday", "Excel", "Notion"],
        "courses": [
            _c("HR Management and Analytics", "Coursera (Wharton)", 30, "https://www.coursera.org/learn/wharton-human-resources"),
            _c("Recruiting, Hiring, and Onboarding Employees", "Coursera (Minnesota)", 12, "https://www.coursera.org/learn/recruiting-hiring-onboarding-employees"),
        ],
        "projects": [_p("Design a hiring process", "From JD to offer.", ["Job description", "Sourcing plan", "Interview rubric", "Onboarding"])],
    },
    "content": {
        "skills": ["Writing & editing", "Storytelling", "SEO writing", "Research", "Content strategy", "Voice & tone"],
        "tools": ["Google Docs", "Grammarly", "Surfer SEO", "WordPress", "Notion"],
        "courses": [
            _c("Content Marketing Certification", "HubSpot Academy", 6, "https://academy.hubspot.com/courses/content-marketing"),
            _c("Good with Words: Writing", "Coursera (Michigan)", 20, "https://www.coursera.org/specializations/good-with-words"),
        ],
        "projects": [_p("Build a content portfolio", "Publish real pieces.", ["Pick niche", "Outline", "Write 3 pieces", "Publish & measure"])],
    },
    "entrepreneur": {
        "skills": ["Idea validation", "Customer discovery", "MVP building", "Fundraising basics", "Go-to-market", "Unit economics"],
        "tools": ["Notion", "Figma", "No-code tools", "Stripe", "Google Analytics"],
        "courses": [
            _c("Startup Engineering / How to Start a Startup", "Y Combinator (Startup School)", 20, "https://www.startupschool.org/"),
            _c("Entrepreneurship Specialization", "Coursera (Wharton)", 40, "https://www.coursera.org/specializations/wharton-entrepreneurship"),
        ],
        "projects": [_p("Launch an MVP", "Validate a real idea.", ["Interview users", "Build MVP", "Launch", "Measure retention"])],
    },
}


# (slug, display name, family, is_senior)
ROLES = [
    # Software
    ("software-engineer", "Software Engineer", "software", False),
    ("junior-software-engineer", "Junior Software Engineer", "software", False),
    ("senior-software-engineer", "Senior Software Engineer", "software", True),
    ("staff-software-engineer", "Staff Software Engineer", "software", True),
    ("principal-engineer", "Principal Engineer", "software", True),
    ("tech-lead", "Technical Lead", "software", True),
    ("web-developer", "Web Developer", "frontend", False),
    ("frontend-engineer", "Frontend Engineer", "frontend", False),
    ("senior-frontend-engineer", "Senior Frontend Engineer", "frontend", True),
    ("backend-engineer", "Backend Engineer", "backend", False),
    ("senior-backend-engineer", "Senior Backend Engineer", "backend", True),
    ("api-engineer", "API Engineer", "backend", False),
    ("fullstack-engineer", "Full-Stack Engineer", "fullstack", False),
    ("senior-fullstack-engineer", "Senior Full-Stack Engineer", "fullstack", True),
    ("design-systems-engineer", "Design Systems Engineer", "frontend", False),
    # Mobile
    ("mobile-engineer", "Mobile Engineer", "mobile", False),
    ("android-engineer", "Android Engineer", "android", False),
    ("ios-engineer", "iOS Engineer", "ios", False),
    ("react-native-developer", "React Native Developer", "mobile", False),
    ("flutter-developer", "Flutter Developer", "mobile", False),
    # Infra / DevOps / Cloud
    ("devops-engineer", "DevOps Engineer", "devops", False),
    ("senior-devops-engineer", "Senior DevOps Engineer", "devops", True),
    ("cloud-engineer", "Cloud Engineer", "cloud", False),
    ("cloud-architect", "Cloud / Solutions Architect", "cloud", True),
    ("site-reliability-engineer", "Site Reliability Engineer", "sre", False),
    ("platform-engineer", "Platform Engineer", "devops", False),
    ("infrastructure-engineer", "Infrastructure Engineer", "devops", False),
    ("kubernetes-engineer", "Kubernetes Engineer", "devops", False),
    ("observability-engineer", "Observability Engineer", "sre", False),
    ("network-engineer", "Network Engineer", "network", False),
    ("systems-administrator", "Systems Administrator", "network", False),
    ("database-administrator", "Database Administrator", "dba", False),
    # Security
    ("security-engineer", "Security Engineer", "security", False),
    ("application-security-engineer", "Application Security Engineer", "appsec", False),
    ("penetration-tester", "Penetration Tester", "appsec", False),
    ("security-analyst", "Security Analyst (SOC)", "security", False),
    ("cloud-security-engineer", "Cloud Security Engineer", "security", False),
    ("devsecops-engineer", "DevSecOps Engineer", "security", False),
    # Data / AI
    ("data-scientist", "Data Scientist", "data-science", False),
    ("senior-data-scientist", "Senior Data Scientist", "data-science", True),
    ("machine-learning-engineer", "Machine Learning Engineer", "ml", False),
    ("deep-learning-engineer", "Deep Learning Engineer", "ml", False),
    ("ai-llm-engineer", "AI / LLM Engineer", "ai-llm", False),
    ("prompt-engineer", "Prompt Engineer", "ai-llm", False),
    ("nlp-engineer", "NLP Engineer", "ml", False),
    ("computer-vision-engineer", "Computer Vision Engineer", "ml", False),
    ("research-scientist-ml", "Research Scientist (ML)", "ml", True),
    ("mlops-engineer", "MLOps Engineer", "mlops", False),
    ("data-engineer", "Data Engineer", "data-eng", False),
    ("senior-data-engineer", "Senior Data Engineer", "data-eng", True),
    ("analytics-engineer", "Analytics Engineer", "data-eng", False),
    ("data-architect", "Data Architect", "data-eng", True),
    ("data-analyst", "Data Analyst", "data-analyst", False),
    ("bi-developer", "Business Intelligence Developer", "data-analyst", False),
    ("bioinformatics-engineer", "Bioinformatics Engineer", "data-science", False),
    ("gis-analyst", "GIS Analyst", "data-analyst", False),
    # QA
    ("qa-engineer", "QA Engineer", "qa", False),
    ("sdet", "SDET / Automation Test Engineer", "qa", False),
    ("performance-test-engineer", "Performance Test Engineer", "qa", False),
    # Design
    ("ux-ui-designer", "UX/UI Designer", "design", False),
    ("product-designer", "Product Designer", "design", False),
    ("interaction-designer", "Interaction Designer", "design", False),
    ("ux-researcher", "UX Researcher", "ux-research", False),
    ("graphic-designer", "Graphic Designer", "graphic", False),
    # Specialized eng
    ("embedded-engineer", "Embedded Systems Engineer", "embedded", False),
    ("firmware-engineer", "Firmware Engineer", "embedded", False),
    ("robotics-engineer", "Robotics Engineer", "embedded", False),
    ("iot-engineer", "IoT Engineer", "embedded", False),
    ("game-developer", "Game Developer", "game", False),
    ("graphics-engineer", "Graphics Engineer", "game", False),
    ("ar-vr-engineer", "AR/VR Engineer", "game", False),
    ("blockchain-engineer", "Blockchain / Web3 Engineer", "blockchain", False),
    ("smart-contract-auditor", "Smart Contract Auditor", "blockchain", True),
    # DevRel / Writing / Management
    ("developer-advocate", "Developer Advocate (DevRel)", "devrel", False),
    ("solutions-engineer", "Solutions Engineer", "devrel", False),
    ("support-engineer", "Support Engineer", "devrel", False),
    ("technical-writer", "Technical Writer", "tech-writing", False),
    ("engineering-manager", "Engineering Manager", "eng-mgmt", True),
    ("cto", "CTO / VP Engineering", "eng-mgmt", True),
    # Product
    ("product-manager", "Product Manager", "product", False),
    ("associate-product-manager", "Associate Product Manager (APM)", "product", False),
    ("senior-product-manager", "Senior Product Manager", "product", True),
    ("technical-product-manager", "Technical Product Manager", "product", False),
    ("product-owner", "Product Owner", "product", False),
    ("group-product-manager", "Group Product Manager", "product", True),
    ("product-operations-manager", "Product Operations Manager", "operations", False),
    # Project / Program
    ("project-manager", "Project Manager", "project", False),
    ("scrum-master", "Scrum Master", "project", False),
    ("program-manager", "Program Manager", "project", True),
    ("delivery-manager", "Delivery Manager", "project", True),
    # Business / Ops / Consulting
    ("business-analyst", "Business Analyst", "business", False),
    ("senior-business-analyst", "Senior Business Analyst", "business", True),
    ("business-systems-analyst", "Business Systems Analyst", "business", False),
    ("management-consultant", "Management Consultant", "consulting", False),
    ("strategy-analyst", "Strategy Analyst", "consulting", False),
    ("operations-manager", "Operations Manager", "operations", True),
    ("business-operations-analyst", "Business Operations Analyst", "operations", False),
    ("supply-chain-analyst", "Supply Chain Analyst", "operations", False),
    # Marketing
    ("digital-marketer", "Digital Marketing Specialist", "marketing", False),
    ("content-marketer", "Content Marketer", "marketing", False),
    ("seo-specialist", "SEO Specialist", "marketing", False),
    ("growth-marketer", "Growth Marketer", "marketing", False),
    ("social-media-manager", "Social Media Manager", "marketing", False),
    ("product-marketing-manager", "Product Marketing Manager (PMM)", "marketing", True),
    ("marketing-manager", "Marketing Manager", "marketing", True),
    ("marketing-analyst", "Marketing Analyst", "data-analyst", False),
    ("brand-manager", "Brand Manager", "marketing", True),
    # Sales / CS
    ("sales-development-rep", "Sales Development Representative (SDR)", "sales", False),
    ("account-executive", "Account Executive", "sales", False),
    ("account-manager", "Account Manager", "sales", False),
    ("sales-manager", "Sales Manager", "sales", True),
    ("customer-success-manager", "Customer Success Manager", "customer-success", False),
    ("customer-support-specialist", "Customer Support Specialist", "customer-success", False),
    # Finance
    ("financial-analyst", "Financial Analyst", "finance", False),
    ("accountant", "Accountant", "finance", False),
    ("fpa-analyst", "FP&A Analyst", "finance", False),
    ("investment-analyst", "Investment Analyst", "finance", True),
    ("financial-controller", "Financial Controller", "finance", True),
    ("quantitative-analyst", "Quantitative Analyst", "finance", True),
    # HR / People
    ("hr-generalist", "HR Generalist", "hr", False),
    ("technical-recruiter", "Technical Recruiter", "hr", False),
    ("talent-acquisition", "Talent Acquisition Specialist", "hr", False),
    ("people-ops-manager", "People Operations Manager", "hr", True),
    ("ld-specialist", "Learning & Development Specialist", "hr", False),
    # Content / Writing
    ("content-writer", "Content Writer", "content", False),
    ("copywriter", "Copywriter", "content", False),
    ("ux-writer", "UX Writer", "content", False),
    ("editor", "Editor", "content", False),
    # Other
    ("entrepreneur", "Founder / Entrepreneur", "entrepreneur", False),
]


def _build_seed() -> dict:
    seed = {
        "general": {
            "name": "General",
            "skills": ["Git & version control", "Problem solving", "Reading documentation", "Communication", "Time management"],
            "tools": ["VS Code", "GitHub", "Notion", "Google Workspace"],
            "courses": [
                _c("Learning How to Learn", "Coursera (McMaster)", 15, "https://www.coursera.org/learn/learning-how-to-learn"),
                _c("CS50x: Intro to Computer Science", "Harvard / edX", 100, "https://cs50.harvard.edu/x/"),
            ],
            "projects": [_p("Ship a personal project", "Start to finish.", ["Plan", "Build", "Deploy", "Write README"])],
        }
    }
    for slug, name, family, senior in ROLES:
        fam = FAM[family]
        skills = list(fam["skills"])
        courses = list(fam["courses"])
        projects = list(fam["projects"])
        if senior:
            skills = skills + [s for s in SENIOR_SKILLS if s not in skills]
            courses = courses + SENIOR_COURSES
            projects = projects + [SENIOR_PROJECT]
        seed[slug] = {
            "name": name,
            "skills": skills,
            "tools": list(fam["tools"]),
            "courses": courses,
            "projects": projects,
        }
    return seed


SEED = _build_seed()


def seed_catalog(db: Session) -> int:
    """Insert any roles/items that don't exist yet. Additive + idempotent.

    Returns the number of NEW roles inserted (0 if nothing new).
    """
    new_roles = 0
    for slug, role_def in SEED.items():
        role = db.query(CatalogRole).filter(CatalogRole.slug == slug).first()
        if role is None:
            role = CatalogRole(slug=slug, name=role_def["name"])
            db.add(role)
            db.flush()
            new_roles += 1

        existing = {(i.category, i.name) for i in role.items}
        order = len(role.items)

        def add_item(**kwargs):
            nonlocal order
            key = (kwargs["category"], kwargs["name"])
            if key in existing:
                return
            db.add(CatalogItem(role_id=role.id, sort_order=order, **kwargs))
            existing.add(key)
            order += 1

        for nm in role_def.get("skills", []):
            add_item(category="skill", name=nm)
        for nm in role_def.get("tools", []):
            add_item(category="tool", name=nm)
        for c in role_def.get("courses", []):
            add_item(category="course", name=c["name"], description=c.get("description"),
                     provider=c.get("provider"), url=c.get("url"), estimated_hours=c.get("estimated_hours"))
        for p in role_def.get("projects", []):
            add_item(category="project", name=p["name"], description=p.get("description"), steps=p.get("steps"))

    db.commit()
    return new_roles
