# Security Policy & Boundaries

## Security Model Overview
The `ai-java-engineer` platform treats all external repository content and user requirements as **UNTRUSTED INPUT**. The system implements defensive barriers to prevent prompt injections, arbitrary filesystem access, secret leakage, and unauthorized execution.

## Core Security Boundaries
1. **Filesystem Containment (Sandboxing)**
   - All tool filesystem operations (`read_file`, `write_file`, `apply_patch`) validate absolute canonical paths against an authorized workspace root.
   - Any path traversal attempt (e.g. `../../etc/passwd` or `C:\Windows`) raises an immediate security violation.
2. **Secret Redaction (Data Loss Prevention)**
   - All stdout, stderr, model prompts, and structured logs pass through a regex-based `SecretSanitizer`.
   - Credentials matching patterns for API keys (e.g. `sk-...`, `AIza...`, GitHub Personal Access Tokens, Bearer tokens) are masked to `[REDACTED]`.
3. **Prompt Injection Mitigation**
   - Untrusted repository content and comments are encapsulated strictly as DATA blocks with explicit boundary delimiters and neutralizer tags, preventing them from overriding system governance policies.
4. **Tool Permissions & Gating**
   - Read operations: LOW RISK (Autonomous)
   - Code patch / write operations: MEDIUM RISK (Autonomous with diff tracking)
   - Git push & PR creation: HIGH RISK (Requires deterministic Human Approval Gate)
   - Production deployment: FORBIDDEN
