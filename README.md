# AI Java Engineer

> **Plataforma agentic de ingeniería de software que combina razonamiento probabilístico mediante LLMs con ejecución determinista, evaluación automática, aislamiento de herramientas, observabilidad, control humano y pipelines de entrega verificables.**

Diseñado para automatizar features Java/Spring Boot desde el requerimiento en lenguaje natural hasta un Pull Request validado, cumpliendo con la restricción de ejecutarse en entornos locales exclusivamente con **Python** mientras delega la compilación y ejecución de **Java 21 + Maven** a backends remotos o entornos sandbox controlados.

---

## Principios Arquitectónicos

1. **Separación de 3 Capas:**
   - **Capa 1: Razonamiento (Probabilística):** Product Agent, Architect Agent, Coding Agent, Debug Agent, Security Reviewer, Code Reviewer.
   - **Capa 2: Herramientas Deterministas:** Filesystem seguro con boundary checks, AST/regex parsing, Surefire XML parser, Git manager.
   - **Capa 3: Gobernanza:** Control de permisos, compuertas de aprobación humana (HITL), límites de reintento, presupuestos de tokens/coste y logs de auditoría.
2. **Orquestación Determinista:** Transiciones de estado regidas por lógica de control estricta (LangGraph / State Machine), no por agentes libres decidiendo qué hacer a cada paso.
3. **Vendor-Neutral:** Abstracción desacoplada de proveedores (`ModelProvider`) con soporte nativo para Gemini, OpenAI, Anthropic y MockProvider para pruebas unitarias.
4. **Evaluación Científica:** Benchmark reproducible con métricas de ingeniería (Build Success Rate, Test Pass Rate, Hidden Test Pass Rate, Regression Rate, Coste por Tarea) y taxonomía de errores (`E001`-`E010`).

---

## Estructura del Proyecto

```
ai-java-engineer/
├── specs/                     # 20 Especificaciones técnicas detalladas (SPEC-001 a SPEC-020)
├── prompts/                   # Prompts versionados por agente
├── evals/                     # Dataset de evaluación y tests ocultos
├── src/ai_java_engineer/
│   ├── api/                   # Endpoints FastAPI
│   ├── domain/                # Modelos de dominio Pydantic v2
│   ├── llm/                   # Abstracción de modelos y token budgeter
│   ├── tools/                 # Herramientas del sistema de archivos y git
│   ├── execution/             # Backends de ejecución Java (Mock y Remoto CI)
│   ├── retrieval/             # Code intelligence híbrido (Java parsing)
│   ├── agents/                # Agentes especializados
│   ├── orchestration/         # Grafo de estados determinista y persistencia SQLite
│   ├── security/              # Sanitización y defensas anti-injection
│   ├── observability/         # Tracing OpenTelemetry y métricas
│   └── evaluation/            # Harness de benchmarks y reporte de ablaciones
└── tests/                     # Suites de tests unitarios, de integración y E2E
```

---

## Ejecución Rápida

### 1. Requisitos
- Python 3.11+ (funciona sobre 3.12, 3.13, 3.14)

### 2. Instalación
```bash
pip install -r requirements.txt
```

### 3. Ejecución del Servidor API
```bash
python -m uvicorn ai_java_engineer.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Ejecución del Benchmark de Evaluación
```bash
python -m ai_java_engineer.evaluation.benchmark_runner --dataset evals/dataset.jsonl
```
