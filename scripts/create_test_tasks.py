import urllib.request
import base64
import json
from ai_java_engineer.infrastructure.settings import get_settings

s = get_settings()
auth = base64.b64encode(f"{s.jira_email}:{s.jira_api_token}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# 1. Fetch project info
url_proj = f"{s.jira_url}/rest/api/3/project/{s.jira_project_key}"
req_proj = urllib.request.Request(url_proj, headers=headers)
with urllib.request.urlopen(req_proj) as r:
    proj_data = json.loads(r.read().decode())
    issue_types = proj_data.get("issueTypes", [])
    print("Project IssueTypes found:")
    type_map = {}
    for it in issue_types:
        name = it.get("name")
        it_id = it.get("id")
        sub = it.get("subtask")
        print(f"  ID: {it_id}, Name: {name}, Subtask: {sub}")
        if not sub:
            type_map[name.lower()] = it_id

print("Available type_map:", type_map)

target_type_id = type_map.get("historia") or type_map.get("story") or type_map.get("tarea") or type_map.get("task") or list(type_map.values())[0]
print("Selected target_type_id:", target_type_id)

def create_jira_issue(summary, desc_text, acceptance_criteria, labels=None):
    bullet_items = []
    for c in acceptance_criteria:
        bullet_items.append({
            "type": "listItem",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": c}]}]
        })
    adf_doc = {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": desc_text}]},
            {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Criterios de Aceptacion (Gherkin):"}]},
            {"type": "bulletList", "content": bullet_items}
        ]
    }
    body = {
        "fields": {
            "project": {"key": s.jira_project_key},
            "summary": summary,
            "description": adf_doc,
            "issuetype": {"id": target_type_id},
            "labels": labels or ["ai-java-engineer", "backend", "spring-boot-3"]
        }
    }
    req = urllib.request.Request(f"{s.jira_url}/rest/api/3/issue", data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
        print(f"SUCCESS CREATED {data.get('key')}: {summary}")
        return data.get("key")

tasks = [
    {
        "summary": "Filtro de Rate Limiting por IP para Endpoints Criticos (POST /api/v1/auth/**)",
        "desc": "Implementar un componente OncePerRequestFilter en Spring Boot 3 con Java 21 que limite las peticiones concurrentes por direccion IP a un maximo de 5 peticiones por minuto para endpoints de autenticacion. Debe retornar codigo HTTP 429 Too Many Requests con encabezado 'Retry-After: 60' si se supera la cuota.",
        "criteria": [
            "DADO un cliente enviando hasta 5 peticiones en un minuto a /api/v1/auth/login, CUANDO se evalua el filtro, ENTONCES todas responden HTTP 200 OK.",
            "DADO un cliente enviando una 6ta peticion en el mismo minuto, ENTONCES el filtro intercepta la llamada, responde HTTP 429 Too Many Requests y no ejecuta el controller.",
            "DADO el cuerpo de error HTTP 429, ENTONCES debe retornar JSON con campos 'error', 'message' y 'retryAfterSeconds'.",
            "DADO el codigo desarrollado, ENTONCES debe contar con pruebas unitarias exhaustivas con MockMvc simulando llamadas concurrentes."
        ],
        "labels": ["security", "rate-limit", "spring-boot-3", "java-21"]
    },
    {
        "summary": "Exportador Streaming de Transacciones en Formato CSV y JSON (GET /api/v1/transactions/export)",
        "desc": "Construir endpoint GET /api/v1/transactions/export con Spring Boot 3 que admita el parametro query 'format' ('csv' o 'json') y rango de fechas (startDate, endDate). Para grandes volumenes de datos, la generacion debe usar StreamingResponseBody para evitar OutOfMemoryError.",
        "criteria": [
            "DADO el parametro format=csv y un rango de fechas valido, CUANDO se invoca el endpoint, ENTONCES responde HTTP 200 OK con Content-Type: text/csv y Content-Disposition: attachment; filename=transactions.csv.",
            "DADO el archivo CSV generado, ENTONCES la primera linea contiene los encabezados: id,accountId,amount,currency,status,timestamp.",
            "DADO un formato no soportado (ej: format=xml), ENTONCES responde HTTP 400 Bad Request con mensaje explicativo.",
            "DADO el codigo, ENTONCES debe incluir pruebas unitarias con JUnit 5 validando el flujo de bytes generado."
        ],
        "labels": ["transactions", "streaming", "csv", "spring-data"]
    },
    {
        "summary": "Validador Criptografico de Firmas HMAC-SHA256 para Webhooks de Pagos",
        "desc": "Desarrollar un servicio y decorador/filtro en Spring Boot 3 que verifique la firma criptografica de notificaciones entrantes de pasarelas de pago. La firma viene en el encabezado 'X-Hub-Signature-256' con formato 'sha256=<hex_hash>'. Se debe computar el HMAC-SHA256 del raw payload usando una clave secreta corporativa y comparar en tiempo constante para mitigar timing attacks.",
        "criteria": [
            "DADO un webhook con firma HMAC-SHA256 valida calculada con el secreto, CUANDO se recibe el POST /api/v1/webhooks/payment, ENTONCES responde HTTP 200 OK.",
            "DADO un webhook con firma ausente, invalida o payload alterado, ENTONCES rechaza inmediatamente la peticion con HTTP 401 Unauthorized sin persistir el evento.",
            "DADO el algoritmo de comparacion de hashes, ENTONCES debe utilizar MessageDigest.isEqual para garantizar comparacion en tiempo constante.",
            "DADO el codigo de pruebas, ENTONCES debe verificar tanto casos de exito como vectores de manipulacion de carga util."
        ],
        "labels": ["cryptography", "webhooks", "hmac-sha256", "security"]
    }
]

created_keys = []
for t in tasks:
    k = create_jira_issue(t["summary"], t["desc"], t["criteria"], t["labels"])
    created_keys.append(k)

print("\nTODAS LAS TAREAS FUERON CREADAS SATISFACTORIAMENTE EN JIRA:", created_keys)
