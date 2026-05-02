# ZeroLoop Two-Layer Architecture

## System Flow Diagram

```mermaid
graph TB
    A[User Request] --> B[API Route /api/analyze]
    B --> C[Layer 1: analyze.py]
    
    C --> D[check_npm_audit]
    C --> E[check_depcheck]
    C --> F[check_circular_dependencies]
    C --> G[check_node_version]
    
    D --> H[npm audit --json]
    E --> I[npx depcheck --json]
    F --> J[npx madge --circular --json]
    G --> K[Node version comparison]
    
    H --> L[Raw Findings JSON]
    I --> L
    J --> L
    K --> L
    
    L --> M[Layer 2: granite_interpreter.py]
    
    M --> N{Credentials?}
    N -->|Yes| O[interpret_findings]
    N -->|No| P[template_interpret]
    
    O --> Q[Call Granite API]
    Q --> R{Response OK?}
    R -->|Yes| S[Parse & Validate]
    R -->|No| P
    S -->|Valid| T[Interpreted Issues]
    S -->|Invalid| P
    
    P --> T
    T --> U[Return to User]
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Layer1 as analyze.py
    participant NPM as npm audit
    participant Depcheck
    participant Madge
    participant Layer2 as granite_interpreter.py
    participant Granite as Granite API
    
    User->>API: POST /api/analyze
    API->>Layer1: run_analysis(project_path)
    
    Layer1->>NPM: npm audit --json
    NPM-->>Layer1: Vulnerability data
    
    Layer1->>Depcheck: npx depcheck --json
    Depcheck-->>Layer1: Unused/missing deps
    
    Layer1->>Madge: npx madge --circular --json
    Madge-->>Layer1: Circular chains
    
    Layer1->>Layer1: check_node_version()
    
    Layer1-->>API: Raw findings JSON
    
    API->>Layer2: interpret_findings(raw_findings)
    
    alt Has credentials
        Layer2->>Granite: POST with prompt
        Granite-->>Layer2: AI interpretation
        Layer2->>Layer2: Validate schema
    else No credentials or error
        Layer2->>Layer2: template_interpret()
    end
    
    Layer2-->>API: Interpreted issues
    API-->>User: Final response
```

## Layer 1: Raw Findings Structure

```mermaid
graph LR
    A[run_analysis] --> B[Raw Findings Array]
    
    B --> C[npm_audit finding]
    B --> D[depcheck finding]
    B --> E[circular_deps finding]
    B --> F[node_version finding]
    
    C --> G[vulnerabilities]
    C --> H[metadata]
    
    D --> I[unused deps]
    D --> J[missing deps]
    D --> K[metadata]
    
    E --> L[circular chains]
    E --> M[metadata]
    
    F --> N[version mismatches]
    F --> O[metadata]
```

## Layer 2: Interpretation Flow

```mermaid
graph TB
    A[Raw Findings] --> B{Has Credentials?}
    
    B -->|Yes| C[Build Granite Prompt]
    C --> D[Call Granite API]
    D --> E{API Success?}
    
    E -->|Yes| F[Parse JSON Response]
    F --> G{Valid Schema?}
    
    G -->|Yes| H[Return Interpreted Issues]
    G -->|No| I[template_interpret]
    
    E -->|No| I
    B -->|No| I
    
    I --> J[Rule-based Interpretation]
    J --> H
    
    H --> K[interpreted_issues]
    H --> L[circular_constraint_pairs]
    H --> M[coordinated_fix_plan]
```

## Component Responsibilities

### Layer 1: analyze.py
- ✅ Execute npm audit
- ✅ Execute depcheck
- ✅ Execute madge (circular deps)
- ✅ Check Node version compatibility
- ✅ Aggregate raw findings
- ❌ NO interpretation
- ❌ NO bobclues
- ❌ NO fix recommendations

### Layer 2: granite_interpreter.py
- ✅ Call Granite API with raw findings
- ✅ Generate bobclues (DO NOT...)
- ✅ Provide explanations
- ✅ Assign severity levels
- ✅ Create fix recommendations
- ✅ Identify circular constraint pairs
- ✅ Generate coordinated fix plan
- ✅ Fallback to template interpretation

## Error Handling Flow

```mermaid
graph TB
    A[Error Occurs] --> B{Which Layer?}
    
    B -->|Layer 1| C{Tool Available?}
    C -->|npm audit fails| D[Return error finding]
    C -->|depcheck missing| E[Try install, then warn]
    C -->|madge fails| F[Use manual fallback]
    C -->|Node check fails| D
    
    D --> G[Continue with other checks]
    E --> G
    F --> G
    
    B -->|Layer 2| H{Error Type?}
    H -->|No credentials| I[Use template_interpret]
    H -->|API timeout| J[Retry once]
    H -->|Malformed response| I
    H -->|Invalid JSON| K[Parse partial, fill gaps]
    
    J -->|Still fails| I
    K --> I
    
    I --> L[Return template-based interpretation]
    G --> M[Return partial raw findings]
```

## Key Design Decisions

### 1. Separation of Concerns
- **Layer 1**: Pure data collection (no opinions)
- **Layer 2**: AI-powered interpretation (all opinions)

### 2. Graceful Degradation
- Missing tools → Continue with available tools
- No Granite credentials → Use template fallback
- API errors → Automatic fallback to templates

### 3. Schema Validation
- Layer 1 output: Strict raw findings format
- Layer 2 output: Validated interpretation schema
- Malformed responses: Handled gracefully

### 4. Tool Integration
- npm audit: Native npm command
- depcheck: npx (auto-install if needed)
- madge: Already integrated, keep as-is
- Node version: Pure Python logic

### 5. Backward Compatibility
- Keep old analyze.py as analyze_legacy.py
- Version API endpoints if needed
- Provide migration guide
