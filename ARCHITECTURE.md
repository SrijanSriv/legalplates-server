# LegalPlates Architecture Diagrams

## System Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        FE[Next.js Frontend]
        CHAT[Chat Interface]
        UPLOAD[Document Upload]
        TEMPLATES[Template Management]
    end
    
    subgraph "API Gateway"
        API[FastAPI Server]
        AUTH[Authentication]
        CORS[CORS Middleware]
    end
    
    subgraph "Core Services"
        UPLOAD_SVC[Upload Service]
        TEMPLATE_SVC[Template Generator]
        GEMINI_SVC[Gemini AI Service]
        EMBED_SVC[Embedding Service]
        EXA_SVC[Exa Web Search]
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL + pgvector)]
        TEMPLATES_TBL[Templates Table]
        VARIABLES_TBL[Variables Table]
        INSTANCES_TBL[Instances Table]
    end
    
    subgraph "External APIs"
        GEMINI_API[Google Gemini API]
        EXA_API[Exa.ai API]
    end
    
    FE --> API
    CHAT --> API
    UPLOAD --> API
    TEMPLATES --> API
    
    API --> UPLOAD_SVC
    API --> TEMPLATE_SVC
    API --> GEMINI_SVC
    API --> EMBED_SVC
    API --> EXA_SVC
    
    UPLOAD_SVC --> TEMPLATE_SVC
    TEMPLATE_SVC --> GEMINI_SVC
    TEMPLATE_SVC --> EMBED_SVC
    TEMPLATE_SVC --> EXA_SVC
    
    GEMINI_SVC --> GEMINI_API
    EXA_SVC --> EXA_API
    
    TEMPLATE_SVC --> DB
    UPLOAD_SVC --> DB
    
    DB --> TEMPLATES_TBL
    DB --> VARIABLES_TBL
    DB --> INSTANCES_TBL
```

## Document Processing Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant T as Template Generator
    participant G as Gemini AI
    participant E as Embedding Service
    participant D as Database
    
    U->>F: Upload Document
    F->>A: POST /api/v1/upload
    A->>T: Process Document
    
    par Parallel Processing
        T->>G: Extract Variables & Generate Template
        T->>E: Generate Embeddings
    end
    
    G-->>T: Variables + Template Body + Questions
    E-->>T: Vector Embeddings
    
    T->>D: Save Template + Variables
    T->>A: Return Template + Questions
    A->>F: Template Data
    F->>U: Display Form with Prefilled Values
```

## Template Matching Flow

```mermaid
flowchart TD
    A[User Query] --> B[Semantic Search]
    B --> C{Found Templates?}
    C -->|Yes| D[AI Re-ranking]
    C -->|No| E[Web Search Fallback]
    
    D --> F{Quality Check}
    F -->|High Quality| G[Return Database Match]
    F -->|Low Quality| E
    
    E --> H{Web Results?}
    H -->|Yes| I[Generate Template from Web]
    H -->|No| J[Return No Match]
    
    I --> K[Return Web Template]
    G --> L[Questions + Prefilled Values]
    K --> L
    L --> M[User Form]
```

## Prompt Evolution Stages

```mermaid
graph LR
    A[1. Role Prompting] --> B[2. Chain-of-Thought]
    B --> C[3. Guardrails]
    C --> D[4. Markdown Examples]
    D --> E[5. Artifact Removal]
    E --> F[6. Legal Classification]
    F --> G[7. Frontend Optimization]
    
    A --> A1["You are a senior legal advocate<br/>with X years experience"]
    B --> B1["Systematic variable extraction<br/>with clear rules"]
    C --> C1["Legal document validation<br/>and compliance checks"]
    D --> D1["Detailed formatting examples<br/>and structure guides"]
    E --> E1["Remove page numbers,<br/>incomplete phrases, artifacts"]
    F --> F1["Convert non-legal docs<br/>to legal templates"]
    G --> G1["Bullet points instead<br/>of tables for frontend"]
```

## Performance Optimization Flow

```mermaid
graph TD
    A[Document Upload] --> B[Parallel Processing]
    B --> C[Gemini AI Call]
    B --> D[Embedding Generation]
    B --> E[Duplicate Detection]
    
    C --> F[Combined API Call]
    F --> G[Variables + Template + Questions]
    
    D --> H[Vector Embeddings]
    E --> I{Duplicate Found?}
    I -->|Yes| J[Return Existing Template]
    I -->|No| K[Save New Template]
    
    G --> L[Template Ready]
    H --> L
    J --> L
    K --> L
    
    L --> M[Frontend Display]
    M --> N[Prefilled Form]
    N --> O[User Input]
    O --> P[Final Document]
```

## Key Features Architecture

```mermaid
mindmap
  root((LegalPlates))
    AI Processing
      Gemini Integration
        Variable Extraction
        Template Generation
        Question Creation
        Legal Classification
      Embedding Service
        Vector Generation
        Semantic Search
        Duplicate Detection
    Web Integration
      Exa Search
        Web Template Discovery
        Content Extraction
        Legal Document Sources
    Database Layer
      PostgreSQL
        Template Storage
        Variable Management
        Instance Tracking
      pgvector
        Vector Similarity
        Semantic Matching
        Performance Optimization
    Frontend Features
      Real-time Updates
        Server-Sent Events
        Progress Tracking
        Status Updates
      Smart Prefilling
        Query Analysis
        Field Auto-completion
        User Experience
      Template Management
        CRUD Operations
        Search & Filter
        Bulk Operations
```
