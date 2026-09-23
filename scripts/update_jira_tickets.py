import urllib.request
import json
import base64
from ai_java_engineer.infrastructure.settings import get_settings

s = get_settings()
auth = base64.b64encode(f"{s.jira_email}:{s.jira_api_token}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

def update_issue_adf(key, summary, desc_intro, criteria):
    bullet_items = []
    for c in criteria:
        bullet_items.append({
            "type": "listItem",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": c}]}]
        })
    adf_doc = {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": desc_intro}]},
            {"type": "heading", "attrs": {"level": 3}, "content": [{"type": "text", "text": "Criterios de Aceptación (Gherkin):"}]},
            {"type": "bulletList", "content": bullet_items}
        ]
    }
    body = {
        "fields": {
            "summary": summary,
            "description": adf_doc
        }
    }
    req = urllib.request.Request(f"{s.jira_url}/rest/api/3/issue/{key}", data=json.dumps(body).encode(), headers=headers, method="PUT")
    with urllib.request.urlopen(req) as res:
        print(f"{key} UPDATED STATUS: {res.status}")

update_issue_adf(
    "SCRUM-5",
    "API REST de Verificación de Salud del Servicio (/api/v1/health)",
    "Construir un endpoint GET /api/v1/health con Spring Boot 3 y Java 21 que retorne el estado UP del microservicio, timestamp ISO-8601 y versión 1.0.0.",
    [
        "DADO un microservicio Spring Boot activo, CUANDO se consume GET /api/v1/health, ENTONCES responde código HTTP 200 OK con JSON {\"status\":\"UP\"}.",
        "DADO el cuerpo de respuesta, ENTONCES debe incluir timestamp en formato ISO-8601 y versión \"1.0.0\".",
        "DADO el código Java, ENTONCES debe estar cubierto con pruebas unitarias JUnit 5 y Mockito."
    ]
)

update_issue_adf(
    "SCRUM-6",
    "Servicio de Cálculo de Descuentos para Carrito de Compras",
    "Implementar servicio Spring Boot con endpoint POST /api/v1/discounts/calculate que reciba subtotal y cupón promocional.",
    [
        "DADO un subtotal positivo y cupón \"VIP10\", CUANDO se calcula el descuento, ENTONCES retorna el monto descontado (10%) y HTTP 200 OK.",
        "DADO un subtotal positivo y cupón \"PROMO20\", CUANDO se procesa, ENTONCES retorna el monto con 20% de descuento.",
        "DADO un subtotal menor o igual a cero, ENTONCES responde HTTP 400 Bad Request con mensaje descriptivo."
    ]
)
print("ALL DONE")
