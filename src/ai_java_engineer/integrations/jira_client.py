"""Atlassian Jira Integration Client for AI Java Engineer platform.

Supports:
1. Live Atlassian Jira Cloud REST API (v3) via HTTP Basic Auth (email + API token).
2. Embedded high-fidelity enterprise demonstration backlog for executive presentations.
3. Webhook listener ingestion and automated ticket lifecycle transitions.
"""

from datetime import datetime, timezone
import json
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from pydantic import BaseModel, Field

from ai_java_engineer.domain.requirement import RequirementSpec
from ai_java_engineer.infrastructure.logging import get_logger
from ai_java_engineer.infrastructure.settings import AppSettings, get_settings

logger = get_logger("jira_client")


class JiraIssue(BaseModel):
    """Normalized Jira Issue representation."""

    key: str = Field(description="Issue key, e.g. PAY-104")
    summary: str = Field(description="Issue summary title")
    description: str = Field(description="Full issue description / requirement")
    issue_type: str = Field(default="Story", description="Story | Bug | Task | Epic")
    status: str = Field(default="To Do", description="To Do | In Progress | In Review | Done")
    priority: str = Field(default="Medium", description="Highest | High | Medium | Low")
    assignee: str = Field(default="Java X (Agente Sintético)", description="Assigned developer or synthetic agent")
    reporter: str = Field(default="Diego Del Carpio", description="Creator / Product Owner")
    labels: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    comments: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))


# Enterprise Demo Backlog Tickets
INITIAL_DEMO_ISSUES: dict[str, JiraIssue] = {
    "PAY-104": JiraIssue(
        key="PAY-104",
        summary="API de Procesamiento de Reembolsos con Webhooks y Clave de Idempotencia",
        description="Construir servicio Spring Boot 3 y Java 21 para el endpoint POST /api/v1/refunds que reciba paymentId, amount, reason y header Idempotency-Key. Validar que no se procese dos veces el mismo reembolso y emitir evento a webhook de notificaciones.",
        issue_type="Story",
        status="To Do",
        priority="High",
        assignee="Java X",
        reporter="Diego Del Carpio (Delivery Manager)",
        labels=["payments", "spring-boot-3", "idempotency", "agent-factory"],
        acceptance_criteria=[
            "DADO un pago existente y un idempotencyKey único, CUANDO se solicita el reembolso, ENTONCES se crea el reembolso con estado PENDING y código HTTP 201 Created.",
            "DADO un idempotencyKey ya utilizado previamente, CUANDO se reintenta la misma solicitud, ENTONCES se retorna la respuesta previa en caché sin duplicar cobro con HTTP 200 OK.",
            "DADO un monto negativo o mayor al total de la transacción original, CUANDO se valida la petición, ENTONCES responde HTTP 400 Bad Request con mensaje descriptivo.",
        ],
    ),
    "AUTH-205": JiraIssue(
        key="AUTH-205",
        summary="Validación de Tokens OAuth2 / JWT con Spring Security 6",
        description="Implementar JwtAuthenticationFilter y SecurityFilterChain en Spring Boot 3 para validar claims de roles corporativos (ROLE_ADMIN, ROLE_DEVELOPER) y autenticación OAuth2 / JWT, manejando expiración con HTTP 401 Unauthorized.",
        issue_type="Story",
        status="To Do",
        priority="Highest",
        assignee="Java X",
        reporter="Lorena (Directora de Operaciones)",
        labels=["security", "jwt", "oauth2", "spring-security"],
        acceptance_criteria=[
            "DADO un token JWT firmado y no expirado, CUANDO se consume un endpoint protegido, ENTONCES el SecurityContext se puebla con el usuario y responde HTTP 200 OK.",
            "DADO un token expirado o con firma adulterada, CUANDO se envía en el header Authorization, ENTONCES responde inmediatamente HTTP 401 Unauthorized sin llamar al controller.",
        ],
    ),
    "ORD-301": JiraIssue(
        key="ORD-301",
        summary="Endpoint Paginado con Filtros Dinámicos para Historial de Pedidos",
        description="Construir endpoint GET /api/v1/customers/{id}/orders con paginación nativa Pageable de Spring Data, filtros opcionales por estado (PENDING, SHIPPED, CANCELLED) y ordenamiento cronológico.",
        issue_type="Story",
        status="To Do",
        priority="Medium",
        assignee="Java X",
        reporter="Diego Del Carpio",
        labels=["orders", "pagination", "spring-data-jpa"],
        acceptance_criteria=[
            "DADO un cliente con pedidos, CUANDO se solicita la página 0 con tamaño 10, ENTONCES retorna JSON con content, totalElements, totalPages y HTTP 200 OK.",
            "DADO un parámetro de estado inexistente en el enum, CUANDO se consulta la API, ENTONCES retorna HTTP 400 Bad Request.",
        ],
    ),
    "BUG-412": JiraIssue(
        key="BUG-412",
        summary="Corrección de NullPointerException en CustomerService al buscar IDs inexistentes",
        description="En CustomerService.findById, si el repositorio devuelve Optional.empty(), se produce NPE al intentar acceder a customer.getStatus(). Se debe lanzar CustomerNotFoundException con código HTTP 404 Not Found y mensaje claro.",
        issue_type="Bug",
        status="To Do",
        priority="High",
        assignee="Java X",
        reporter="Lead Architect",
        labels=["bugfix", "exceptions", "self-healing"],
        acceptance_criteria=[
            "DADO un ID de cliente que no existe en la base de datos, CUANDO se llama a CustomerService.findById, ENTONCES no se produce NPE y responde HTTP 404 Not Found.",
        ],
    ),
}


class JiraClient:
    """Atlassian Jira Client supporting Cloud REST API and Local Enterprise Sandbox."""

    def __init__(self, settings: AppSettings | None = None):
        self.settings = settings or get_settings()
        self.is_connected = bool(self.settings.jira_url and self.settings.jira_api_token)
        self._issues_db: dict[str, JiraIssue] = {k: v.model_copy(deep=True) for k, v in INITIAL_DEMO_ISSUES.items()}

    def list_assigned_issues(self, assignee: str | None = None) -> list[JiraIssue]:
        """Lists issues assigned to Java X (or all pending backlog issues)."""
        target_assignee = assignee or self.settings.jira_agent_assignee or "Java X"

        if self.is_connected:
            try:
                return self._fetch_live_assigned_issues(target_assignee)
            except Exception as e:
                logger.warning(f"Failed to fetch live Jira issues: {e}")

        # Demo/Local Mode
        return list(self._issues_db.values())

    def get_issue(self, issue_key: str) -> JiraIssue | None:
        """Retrieves an issue by key (e.g. PAY-104)."""
        key_clean = issue_key.strip().upper()

        if self.is_connected:
            try:
                live_issue = self._fetch_live_issue(key_clean)
                if live_issue:
                    return live_issue
            except Exception as e:
                logger.warning(f"Failed to fetch live Jira issue {key_clean}: {e}")

        return self._issues_db.get(key_clean)

    def add_comment(self, issue_key: str, comment_text: str, author: str = "Java X Agent") -> bool:
        """Adds an execution or audit comment to the Jira ticket."""
        key_clean = issue_key.strip().upper()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        # Update in-memory / demo store
        if key_clean in self._issues_db:
            self._issues_db[key_clean].comments.append({
                "author": author,
                "text": comment_text,
                "created_at": timestamp,
            })
            self._issues_db[key_clean].updated_at = timestamp

        if self.is_connected:
            try:
                return self._post_live_comment(key_clean, comment_text)
            except Exception as e:
                logger.error(f"Failed to post comment to live Jira {key_clean}: {e}")

        return True

    def transition_issue(self, issue_key: str, target_status: str) -> bool:
        """Transitions ticket status (To Do -> In Progress -> In Review -> Done)."""
        key_clean = issue_key.strip().upper()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

        if key_clean in self._issues_db:
            self._issues_db[key_clean].status = target_status
            self._issues_db[key_clean].updated_at = timestamp
            logger.info(f"Jira issue {key_clean} transitioned to {target_status}")

        if self.is_connected:
            try:
                return self._post_live_transition(key_clean, target_status)
            except Exception as e:
                logger.error(f"Failed to transition live Jira ticket {key_clean}: {e}")

        return True

    def convert_to_requirement_spec(
        self,
        issue: JiraIssue,
        workspace_path: str | None = None,
    ) -> RequirementSpec:
        """Transforms a Jira ticket into an autonomous multi-agent RequirementSpec."""
        ac_text = "\n".join([f"- {ac}" for ac in issue.acceptance_criteria]) if issue.acceptance_criteria else ""
        raw_text = f"{issue.description}\n\nCriterios de Aceptación Jira:\n{ac_text}" if ac_text else issue.description

        constraints = ["Spring Boot 3.3", "Java 21", "JUnit 5 + Mockito"]
        if issue.issue_type == "Bug":
            constraints.append("Bugfix: Ensure non-null handling and custom HTTP error code")

        return RequirementSpec(
            id=f"JIRA-{issue.key}",
            title=f"[{issue.key}] {issue.summary}",
            raw_text=raw_text,
            target_repository=workspace_path or "./workspaces/sandbox",
            constraints=constraints,
            jira_key=issue.key,
            jira_url=f"{self.settings.jira_url or 'https://atlassian.net'}/browse/{issue.key}",
        )

    def process_webhook_event(self, webhook_data: dict[str, Any]) -> JiraIssue | None:
        """Processes incoming Atlassian Jira webhook payloads."""
        try:
            issue_data = webhook_data.get("issue", {})
            fields = issue_data.get("fields", {})
            key = issue_data.get("key")
            if not key:
                return None

            summary = fields.get("summary", "Sin título")
            description = fields.get("description", "")
            if isinstance(description, dict):
                # Atlassian Document Format (ADF) simple extraction
                description = json.dumps(description)

            issue_type = fields.get("issuetype", {}).get("name", "Story")
            status = fields.get("status", {}).get("name", "To Do")
            priority = fields.get("priority", {}).get("name", "Medium")
            assignee = fields.get("assignee", {}).get("displayName", "Java X")

            issue = JiraIssue(
                key=key,
                summary=summary,
                description=str(description),
                issue_type=issue_type,
                status=status,
                priority=priority,
                assignee=assignee,
                labels=fields.get("labels", []),
            )
            self._issues_db[key] = issue
            return issue
        except Exception as e:
            logger.error(f"Failed to parse Jira webhook payload: {e}")
            return None

    @staticmethod
    def _extract_adf_text(doc: Any) -> str:
        """Extracts plain text from Atlassian Document Format (ADF) JSON structure."""
        if not doc:
            return ""
        if isinstance(doc, str):
            return doc
        if isinstance(doc, dict):
            if doc.get("type") == "text":
                return doc.get("text", "")
            texts = []
            for item in doc.get("content", []):
                extracted = JiraClient._extract_adf_text(item)
                if extracted:
                    texts.append(extracted)
            return " ".join(texts).strip()
        if isinstance(doc, list):
            return " ".join([JiraClient._extract_adf_text(item) for item in doc if item]).strip()
        return str(doc)

    # ------------------------------------------------------------------------
    # Live Atlassian Jira Cloud REST API (v3) Implementation
    # ------------------------------------------------------------------------
    def _fetch_live_assigned_issues(self, assignee: str) -> list[JiraIssue]:
        base_url = self.settings.jira_url.rstrip("/")
        project_clause = f'project = "{self.settings.jira_project_key}"' if self.settings.jira_project_key else ""
        if project_clause:
            jql_query = f"{project_clause} AND statusCategory != Done ORDER BY updated DESC"
        else:
            jql_query = "statusCategory != Done ORDER BY updated DESC"

        jql_encoded = urllib.parse.quote(jql_query)
        url = f"{base_url}/rest/api/3/search/jql?jql={jql_encoded}&maxResults=20&fields=summary,description,status,priority,issuetype,assignee,labels"
        req = urllib.request.Request(url, headers=self._get_auth_headers())
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            issues = []
            for item in data.get("issues", []):
                fields = item.get("fields", {})
                desc_raw = fields.get("description")
                desc_text = self._extract_adf_text(desc_raw) if desc_raw else ""

                assignee_field = fields.get("assignee")
                assignee_name = assignee_field.get("displayName") if assignee_field else "Sin asignar"

                priority_field = fields.get("priority")
                priority_name = priority_field.get("name") if priority_field else "Medium"

                status_field = fields.get("status")
                status_name = status_field.get("name") if status_field else "To Do"

                issues.append(
                    JiraIssue(
                        key=item.get("key"),
                        summary=fields.get("summary", ""),
                        description=desc_text or f"Requerimiento importado de Jira {item.get('key')}",
                        issue_type=fields.get("issuetype", {}).get("name", "Story"),
                        status=status_name,
                        priority=priority_name,
                        assignee=assignee_name,
                        labels=fields.get("labels", []),
                    )
                )
            return issues

    def _fetch_live_issue(self, issue_key: str) -> JiraIssue | None:
        base_url = self.settings.jira_url.rstrip("/")
        url = f"{base_url}/rest/api/3/issue/{issue_key}"
        req = urllib.request.Request(url, headers=self._get_auth_headers())
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            fields = data.get("fields", {})
            desc_raw = fields.get("description")
            desc_text = self._extract_adf_text(desc_raw) if desc_raw else ""

            assignee_field = fields.get("assignee")
            assignee_name = assignee_field.get("displayName") if assignee_field else "Java X"

            priority_field = fields.get("priority")
            priority_name = priority_field.get("name") if priority_field else "Medium"

            status_field = fields.get("status")
            status_name = status_field.get("name") if status_field else "To Do"

            return JiraIssue(
                key=data.get("key"),
                summary=fields.get("summary", ""),
                description=desc_text or f"Requerimiento importado de Jira {data.get('key')}",
                issue_type=fields.get("issuetype", {}).get("name", "Story"),
                status=status_name,
                priority=priority_name,
                assignee=assignee_name,
                labels=fields.get("labels", []),
            )

    def _post_live_comment(self, issue_key: str, comment_text: str) -> bool:
        base_url = self.settings.jira_url.rstrip("/")
        url = f"{base_url}/rest/api/3/issue/{issue_key}/comment"
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment_text}],
                    }
                ],
            }
        }
        data_bytes = json.dumps(body).encode("utf-8")
        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status in (200, 201)

    def _post_live_transition(self, issue_key: str, target_status: str) -> bool:
        base_url = self.settings.jira_url.rstrip("/")
        transitions_url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
        headers = self._get_auth_headers()

        # 1. Fetch available transitions
        req = urllib.request.Request(transitions_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as res:
            t_data = json.loads(res.read().decode("utf-8"))
            transitions = t_data.get("transitions", [])

        # 2. Find best transition match
        target_norm = target_status.lower()
        selected_id = None

        for t in transitions:
            t_name = t.get("name", "").lower()
            to_name = t.get("to", {}).get("name", "").lower()
            to_cat = t.get("to", {}).get("statusCategory", {}).get("key", "").lower()

            if "review" in target_norm or "revis" in target_norm:
                if "revis" in t_name or "review" in t_name or "revis" in to_name:
                    selected_id = t["id"]
                    break
            elif "done" in target_norm or "finaliz" in target_norm or "qa" in target_norm:
                if to_cat == "done" or "finaliz" in t_name or "done" in t_name or "listo" in t_name:
                    selected_id = t["id"]
                    break
            elif "progress" in target_norm or "curso" in target_norm:
                if "curso" in t_name or "progress" in t_name or "curso" in to_name:
                    selected_id = t["id"]
                    break
            elif target_norm in t_name or target_norm in to_name:
                selected_id = t["id"]
                break

        if not selected_id and transitions:
            logger.info(f"No explicit transition match for '{target_status}', skipping live transition.")
            return False

        # 3. Post transition
        body = {"transition": {"id": selected_id}}
        data_bytes = json.dumps(body).encode("utf-8")
        post_headers = {**headers, "Content-Type": "application/json"}
        post_req = urllib.request.Request(transitions_url, data=data_bytes, headers=post_headers, method="POST")
        with urllib.request.urlopen(post_req, timeout=10) as res:
            logger.info(f"Successfully transitioned Jira {issue_key} to {target_status} (transition ID {selected_id})")
            return res.status in (200, 204)

    def _get_auth_headers(self) -> dict[str, str]:
        import base64

        auth_str = f"{self.settings.jira_email}:{self.settings.jira_api_token}"
        encoded = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded}",
            "Accept": "application/json",
        }


# Singleton Jira client instance
jira_client = JiraClient()
