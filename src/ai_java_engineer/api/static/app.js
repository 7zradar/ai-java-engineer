/**
 * AI JAVA ENGINEER - FRONTEND CONTROLLER
 * Reactive dashboard for autonomous multi-agent Java engineering
 */

const PIPELINE_STEPS = [
  { id: 'product_node', name: 'Product Agent', icon: '📝', desc: 'Historias & AC' },
  { id: 'context_node', name: 'Context Indexer', icon: '🔍', desc: 'Escaneo & RAG' },
  { id: 'architect_node', name: 'Architect Agent', icon: '📐', desc: 'Diseño API' },
  { id: 'coder_node', name: 'Coding Agent', icon: '💻', desc: 'Generación .java' },
  { id: 'qa_node', name: 'QA Subagent', icon: '🎯', desc: 'Edge Cases & Negatives' },
  { id: 'build_node', name: 'Build & Healing', icon: '⚙️', desc: 'Compilación Maven' },
  { id: 'test_node', name: 'Test Runner', icon: '🧪', desc: 'JUnit 5 Suite' },
  { id: 'security_node', name: 'Security Guard', icon: '🛡️', desc: 'SAST Scan' },
  { id: 'review_node', name: 'Code Reviewer', icon: '👀', desc: 'Auditoría Peer' },
  { id: 'waiting_approval_node', name: 'Compuerta HITL', icon: '🧑‍💻', desc: 'Revisión Humana' },
  { id: 'completed_node', name: 'Git Delivery', icon: '🚀', desc: 'Pull Request' },
];


const PRESETS = {
  feature: {
    title: "API de Historial de Pedidos de Clientes",
    desc: "Construir endpoint GET /api/v1/customers/{id}/orders con paginación y filtros de estado (PENDING, SHIPPED) utilizando Spring Boot 3 y Java 21."
  },
  bugfix: {
    title: "Corrección de NullPointerException en CustomerService",
    desc: "En CustomerService, validar que si el cliente está inactivo o no existe se lance una excepción de negocio con código 400 Bad Request en lugar de NullPointerException."
  },
  testing: {
    title: "Pruebas Unitarias con JUnit 5 y Mockito para OrderController",
    desc: "Generar una suite completa de pruebas unitarias con JUnit 5 y Mockito para OrderController cubriendo casos exitosos, validaciones negativas y casos de borde."
  }
};


let currentRunId = null;
let pollTimer = null;
let activeFileTab = null;
let cachedRunData = null;
let currentUser = null;
let authToken = localStorage.getItem("ai_java_token") || null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initPresets();
  initModals();
  initActions();
  initAuth();
  initJira();
  fetchHealth();
  fetchRuns();
  
  // Auto refresh runs list periodically
  setInterval(fetchRuns, 10000);
});

/* ==========================================================================
   HEALTH & SYSTEM STATUS
   ========================================================================== */
async function fetchHealth() {
  try {
    const res = await fetch("/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();
    
    document.getElementById("system-status-text").textContent = "Sistema Activo (" + data.status + ")";
    document.getElementById("provider-tag").textContent = "LLM: " + (data.llm_provider || "mock").toUpperCase();
    document.getElementById("backend-tag").textContent = "Backend: " + (data.execution_backend || "mock").toUpperCase();
  } catch (err) {
    document.getElementById("system-status-text").textContent = "Servidor Desconectado";
    document.getElementById("system-status-pill").querySelector(".status-dot").classList.remove("healthy");
  }
}

/* ==========================================================================
   RUNS LISTING & SELECTION
   ========================================================================== */
async function fetchRuns() {
  try {
    const res = await fetch("/runs");
    if (!res.ok) return;
    const runs = await res.json();
    
    const countBadge = document.getElementById("runs-count");
    if (countBadge) countBadge.textContent = runs.length;
    
    const container = document.getElementById("runs-list-container");
    if (!runs || runs.length === 0) {
      container.innerHTML = `
        <div class="empty-state-card" style="text-align: center; padding: 20px; color: var(--text-muted); font-size: 0.85rem;">
          <p>No hay tareas registradas aún.</p>
          <button class="btn btn-sm btn-primary" style="margin-top: 10px;" onclick="openNewRunModal()">+ Crear Primera</button>
        </div>`;
      return;
    }

    container.innerHTML = "";
    runs.forEach(run => {
      const card = document.createElement("div");
      card.className = `run-card ${run.execution_id === currentRunId ? "selected" : ""}`;
      card.onclick = () => selectRun(run.execution_id);

      const statusBadge = getStatusBadge(run.status);
      card.innerHTML = `
        <div class="run-card-top">
          <span class="run-card-id">${escapeHtml(run.execution_id)}</span>
          ${statusBadge}
        </div>
        <div class="run-card-title">${escapeHtml(run.title || run.execution_id)}</div>
        <div class="run-card-footer">
          <span>Iteración: ${run.iteration || 0}</span>
          <span>${escapeHtml(run.created_at || "Reciente")}</span>
        </div>
      `;
      container.appendChild(card);
    });

    // Auto-select latest run if none selected
    if (!currentRunId && runs.length > 0) {
      selectRun(runs[0].execution_id);
    }
  } catch (err) {
    console.error("Error fetching runs:", err);
  }
}

function selectRun(runId) {
  if (pollTimer) clearInterval(pollTimer);
  currentRunId = runId;

  // Highlight card in sidebar
  document.querySelectorAll(".run-card").forEach(c => {
    c.classList.remove("selected");
    if (c.querySelector(".run-card-id")?.textContent === runId) {
      c.classList.add("selected");
    }
  });

  loadRunDetails(runId);
  // Start polling while active
  pollTimer = setInterval(() => {
    loadRunDetails(runId);
  }, 1500);
}

/* ==========================================================================
   RUN DETAILS LOADER & RENDERER
   ========================================================================== */
async function loadRunDetails(runId) {
  try {
    const res = await fetch(`/runs/${runId}`);
    if (!res.ok) return;
    const run = await res.json();
    cachedRunData = run;

    // Show run view and hide empty state
    document.getElementById("no-run-state").style.display = "none";
    document.getElementById("run-view").style.display = "block";

    // Header info
    document.getElementById("run-id-pill").textContent = run.execution_id;
    document.getElementById("run-iteration-badge").textContent = `Iteración: ${run.iteration || 0}`;
    document.getElementById("run-workspace-badge").textContent = `Workspace: ${run.workspace_path ? run.workspace_path.split(/[\\/]/).pop() : "sandbox"}`;
    
    const req = run.requirement || {};
    document.getElementById("run-title").textContent = req.title || run.execution_id;
    document.getElementById("run-raw-text").textContent = req.raw_text || "Sin descripción.";

    // Jira pill
    const jiraPill = document.getElementById("run-jira-pill");
    const jiraKeyEl = document.getElementById("run-jira-key");
    if (run.jira_key) {
      if (jiraPill) jiraPill.style.display = "inline-flex";
      if (jiraKeyEl) jiraKeyEl.textContent = `JIRA: ${run.jira_key}`;
    } else {
      if (jiraPill) jiraPill.style.display = "none";
    }

    // Status badge
    const badgeEl = document.getElementById("run-status-badge");
    badgeEl.className = "run-status-badge";
    badgeEl.innerHTML = getStatusBadge(run.status);

    // Human Gate Banner (HITL)
    const approvalBanner = document.getElementById("approval-banner");
    if (run.status === "WAITING_APPROVAL") {
      approvalBanner.style.display = "flex";
      updateApprovalBannerForUser();
    } else {
      approvalBanner.style.display = "none";
    }

    // Business Value & ROI Metrics
    if (run.roi_metrics) {
      const elHours = document.getElementById("roi-hours-saved");
      const elSavings = document.getElementById("roi-savings-usd");
      if (elHours) elHours.textContent = `${run.roi_metrics.dev_hours_saved} hrs`;
      if (elSavings) elSavings.textContent = `$${run.roi_metrics.savings_usd.toFixed(2)} USD`;
    }

    // Stop polling if completed or failed
    if (["COMPLETED", "FAILED", "SECURITY_BLOCKED"].includes(run.status)) {
      if (pollTimer) clearInterval(pollTimer);
    }


    // Render Pipeline Stepper
    renderPipelineStepper(run);

    // Render Tab Contents
    renderProductSpec(run.product_spec);
    renderArchitectureSpec(run.architecture_spec);
    renderCodeViewer(run.changed_files, run.files_content);
    renderQualityAndSecurity(run);
    renderPullRequest(run.pr_payload);
    renderTimeline(run.timeline);

  } catch (err) {
    console.error("Error loading run details:", err);
  }
}

/* ==========================================================================
   RENDERERS: STEPPER & TABS
   ========================================================================== */

function renderPipelineStepper(run) {
  const container = document.getElementById("pipeline-stepper");
  if (!container) return;

  const timeline = run.timeline || [];
  const visitedNodes = new Set(timeline.map(t => t.node_name));
  const isCompleted = run.status === "COMPLETED";
  const isWaiting = run.status === "WAITING_APPROVAL";
  const isRunning = run.status === "RUNNING";

  container.innerHTML = "";

  PIPELINE_STEPS.forEach((step, idx) => {
    const nodeEl = document.createElement("div");
    let stateClass = "pending";
    let statusText = "Pendiente";

    // Determine status for this step
    const wasVisited = visitedNodes.has(step.id);

    if (step.id === "completed_node" && isCompleted) {
      stateClass = "completed";
      statusText = "Listo";
    } else if (step.id === "waiting_approval_node" && isWaiting) {
      stateClass = "waiting";
      statusText = "Esperando";
    } else if (wasVisited) {
      stateClass = "completed";
      statusText = "Completado";
    } else if (isRunning && !wasVisited && (idx === 0 || visitedNodes.has(PIPELINE_STEPS[idx - 1].id))) {
      stateClass = "active";
      statusText = "Ejecutando...";
    }

    nodeEl.className = `step-node ${stateClass}`;
    nodeEl.innerHTML = `
      <span class="step-icon">${step.icon}</span>
      <span class="step-name">${step.name}</span>
      <span class="step-status">${statusText}</span>
    `;
    container.appendChild(nodeEl);
  });
}

function renderProductSpec(spec) {
  if (!spec) {
    document.getElementById("spec-summary").textContent = "Esperando análisis del Product Agent...";
    document.getElementById("user-stories-container").innerHTML = "<p class='text-muted'>Sin historias de usuario aún.</p>";
    document.getElementById("acceptance-criteria-container").innerHTML = "<p class='text-muted'>Sin criterios aún.</p>";
    return;
  }

  // Summary
  document.getElementById("spec-summary").textContent = spec.summary || "Sin resumen disponible.";

  // User stories
  const storiesContainer = document.getElementById("user-stories-container");
  storiesContainer.innerHTML = "";
  if (spec.user_stories && spec.user_stories.length > 0) {
    spec.user_stories.forEach(us => {
      const card = document.createElement("div");
      card.className = "story-card";
      card.innerHTML = `
        <div class="story-header">
          <span class="story-title">${escapeHtml(us.title)}</span>
          <span class="story-id">${escapeHtml(us.id)}</span>
        </div>
        <div class="story-body">
          <p><strong>Como:</strong> ${escapeHtml(us.as_a)}</p>
          <p><strong>Quiero:</strong> ${escapeHtml(us.i_want)}</p>
          <p><strong>Para:</strong> ${escapeHtml(us.so_that)}</p>
        </div>
      `;
      storiesContainer.appendChild(card);
    });
  } else {
    storiesContainer.innerHTML = "<p class='text-muted'>No se generaron historias de usuario.</p>";
  }

  // Acceptance criteria (Gherkin)
  const acContainer = document.getElementById("acceptance-criteria-container");
  acContainer.innerHTML = "";
  if (spec.acceptance_criteria && spec.acceptance_criteria.length > 0) {
    spec.acceptance_criteria.forEach(ac => {
      const card = document.createElement("div");
      card.className = "ac-card";
      card.innerHTML = `
        <div class="ac-title">${escapeHtml(ac.id)}: ${escapeHtml(ac.scenario || "Escenario")}</div>
        <div class="ac-gherkin">
          <div><span class="gherkin-kw">DADO:</span> ${escapeHtml(ac.given)}</div>
          <div><span class="gherkin-kw">CUANDO:</span> ${escapeHtml(ac.when)}</div>
          <div><span class="gherkin-kw">ENTONCES:</span> ${escapeHtml(ac.then)}</div>
        </div>

      `;
      acContainer.appendChild(card);
    });
  }

  // Business rules
  const rulesList = document.getElementById("business-rules-list");
  rulesList.innerHTML = "";
  if (spec.business_rules && spec.business_rules.length > 0) {
    spec.business_rules.forEach(r => {
      const li = document.createElement("li");
      li.textContent = r;
      rulesList.appendChild(li);
    });
  } else {
    rulesList.innerHTML = "<li class='text-muted'>Sin reglas de negocio específicas.</li>";
  }

  // Edge cases
  const edgeList = document.getElementById("edge-cases-list");
  edgeList.innerHTML = "";
  if (spec.edge_cases && spec.edge_cases.length > 0) {
    spec.edge_cases.forEach(e => {
      const li = document.createElement("li");
      li.textContent = e;
      edgeList.appendChild(li);
    });
  } else {
    edgeList.innerHTML = "<li class='text-muted'>Sin casos límite identificados.</li>";
  }
}

function renderArchitectureSpec(arch) {
  const tbody = document.getElementById("endpoints-table-body");
  const compGrid = document.getElementById("components-grid");
  if (!tbody || !compGrid) return;

  if (!arch) {
    tbody.innerHTML = "<tr><td colspan='4' class='text-center text-muted'>Esperando especificación de arquitectura...</td></tr>";
    compGrid.innerHTML = "<p class='text-muted'>Sin componentes definidos.</p>";
    return;
  }

  // Endpoints table
  tbody.innerHTML = "";
  if (arch.endpoints && arch.endpoints.length > 0) {
    arch.endpoints.forEach(ep => {
      const tr = document.createElement("tr");
      const method = (ep.method || "GET").toUpperCase();
      const methodClass = `method-${method.toLowerCase()}`;
      tr.innerHTML = `
        <td><span class="method-tag ${methodClass}">${method}</span></td>
        <td class="endpoint-path">${escapeHtml(ep.path)}</td>
        <td>${escapeHtml(ep.summary || ep.description || "N/A")}</td>
        <td><code>${escapeHtml(ep.response_dto || ep.response_type || "200 OK")}</code></td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = "<tr><td colspan='4' class='text-center text-muted'>No se definieron endpoints REST.</td></tr>";
  }

  // Components grid
  compGrid.innerHTML = "";
  if (arch.components && arch.components.length > 0) {
    arch.components.forEach(comp => {
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h4 style="font-size: 0.9rem; margin-bottom: 6px; color: #93c5fd;">${escapeHtml(comp.name || comp.class_name)}</h4>
        <p style="font-size: 0.82rem; color: var(--text-secondary);">${escapeHtml(comp.responsibility || comp.package || "")}</p>
      `;
      compGrid.appendChild(card);
    });
  } else {
    compGrid.innerHTML = "<p class='text-muted'>Sin componentes listados.</p>";
  }
}

function renderCodeViewer(changedFiles, filesContent) {
  const tabsBar = document.getElementById("file-tabs-bar");
  const counter = document.getElementById("files-counter");
  const pathLabel = document.getElementById("code-file-path");
  const display = document.getElementById("code-display");

  const files = changedFiles || [];
  counter.textContent = files.length;
  tabsBar.innerHTML = "";

  if (files.length === 0) {
    pathLabel.textContent = "Ningún archivo generado todavía";
    display.textContent = "// El código generado por Coding Agent aparecerá aquí...";
    return;
  }

  if (!activeFileTab || !files.includes(activeFileTab)) {
    activeFileTab = files[0];
  }

  files.forEach(file => {
    const btn = document.createElement("button");
    btn.className = `file-tab ${file === activeFileTab ? "active" : ""}`;
    const filename = file.split(/[\\/]/).pop();
    btn.innerHTML = `<span>☕</span> ${escapeHtml(filename)}`;
    btn.onclick = () => {
      activeFileTab = file;
      renderCodeViewer(changedFiles, filesContent);
    };
    tabsBar.appendChild(btn);
  });

  pathLabel.textContent = activeFileTab;
  const content = (filesContent && filesContent[activeFileTab]) || "// Contenido no disponible o archivo en creación...";
  display.textContent = content;
}

function renderQualityAndSecurity(run) {
  // Build card
  const buildResult = run.build_result;
  const buildBadge = document.getElementById("build-status-badge");
  const buildDuration = document.getElementById("build-duration-stat");
  const buildError = document.getElementById("build-error-summary");
  const buildStdout = document.getElementById("build-stdout");

  if (buildResult) {
    const ok = buildResult.success;
    buildBadge.className = `badge ${ok ? "badge-completed" : "badge-failed"}`;
    buildBadge.textContent = ok ? "EXITOSA" : "FALLIDA";
    buildDuration.textContent = `${buildResult.duration_ms || 0} ms`;
    buildError.textContent = buildResult.error_summary || (ok ? "Build limpio sin errores." : "Error durante la compilación.");
    buildStdout.textContent = buildResult.stdout || "// Sin salida registrada";
  } else {
    buildBadge.className = "badge badge-pending";
    buildBadge.textContent = "PENDIENTE";
    buildDuration.textContent = "-- ms";
    buildError.textContent = "Esperando compilación...";
    buildStdout.textContent = "// Sin salida aún";
  }

  // Tests card
  const testResult = run.test_result;
  const testBadge = document.getElementById("test-status-badge");
  const testRatio = document.getElementById("tests-ratio-stat");
  const testBar = document.getElementById("test-bar-fill");
  const testCasesList = document.getElementById("test-cases-list");

  if (testResult) {
    const passed = testResult.passed_count || 0;
    const total = testResult.total || 0;
    const pct = total > 0 ? Math.round((passed / total) * 100) : 100;
    
    testBadge.className = `badge ${testResult.passed ? "badge-completed" : "badge-failed"}`;
    testBadge.textContent = testResult.passed ? "PASARON" : "FALLARON";
    testRatio.textContent = `${passed} / ${total} tests pasados (${pct}%)`;
    testBar.style.width = `${pct}%`;

    testCasesList.innerHTML = "";
    if (testResult.cases && testResult.cases.length > 0) {
      testResult.cases.forEach(c => {
        const li = document.createElement("li");
        li.innerHTML = `✅ <strong>${escapeHtml(c.name)}</strong> (${(c.time * 1000).toFixed(0)}ms)`;
        testCasesList.appendChild(li);
      });
    } else {
      testCasesList.innerHTML = "<li class='text-muted'>Tests ejecutados satisfactoriamente.</li>";
    }
  } else {
    testBadge.className = "badge badge-pending";
    testBadge.textContent = "PENDIENTE";
    testRatio.textContent = "0 / 0 pasados";
    testBar.style.width = "0%";
    testCasesList.innerHTML = "<li class='text-muted'>Esperando ejecución de pruebas...</li>";
  }

  // Security card
  const secResult = run.security_result;
  const secBadge = document.getElementById("security-status-badge");
  const secFindings = document.getElementById("security-findings-list");

  if (secResult) {
    secBadge.className = `badge ${secResult.passed ? "badge-completed" : "badge-failed"}`;
    secBadge.textContent = secResult.passed ? "SEGURO" : "VULNERABLE";
    
    secFindings.innerHTML = "";
    if (secResult.findings && secResult.findings.length > 0) {
      secResult.findings.forEach(f => {
        const div = document.createElement("div");
        div.style.marginBottom = "8px";
        div.innerHTML = `⚠️ <strong>[${escapeHtml(f.severity || 'WARN')}]</strong> ${escapeHtml(f.message || f.rule_id || 'Alerta')}`;
        secFindings.appendChild(div);
      });
    } else {
      secFindings.innerHTML = "<p style='color: #34d399; font-size: 0.85rem;'>✅ 0 vulnerabilidades detectadas. Código limpio.</p>";
    }
  } else {
    secBadge.className = "badge badge-pending";
    secBadge.textContent = "PENDIENTE";
    secFindings.innerHTML = "<p class='text-muted'>Esperando análisis de seguridad...</p>";
  }

  // Review card
  const reviewResult = run.review_result;
  const reviewBadge = document.getElementById("review-status-badge");
  const reviewBox = document.getElementById("review-feedback-box");

  if (reviewResult) {
    reviewBadge.className = `badge ${reviewResult.verdict === 'APPROVED' ? 'badge-completed' : 'badge-waiting'}`;
    reviewBadge.textContent = reviewResult.verdict || "REVISADO";
    reviewBox.innerHTML = `
      <p style="font-size: 0.85rem; line-height: 1.6; color: var(--text-secondary);">
        ${escapeHtml(reviewResult.feedback || "Código aprobado con altos estándares de calidad y cobertura.")}
      </p>
    `;
  } else {
    reviewBadge.className = "badge badge-pending";
    reviewBadge.textContent = "PENDIENTE";
    reviewBox.innerHTML = "<p class='text-muted'>Esperando veredicto del Review Agent...</p>";
  }
}

function renderPullRequest(pr) {
  const title = document.getElementById("pr-title");
  const branch = document.getElementById("pr-branch-name");
  const base = document.getElementById("pr-base-branch");
  const body = document.getElementById("pr-body-markdown");

  if (pr) {
    title.textContent = pr.title || "feat: Automated Feature";
    branch.textContent = pr.branch || "feat/ai-branch";
    base.textContent = pr.base_branch || "main";
    body.textContent = pr.body || "Sin descripción.";
  } else {
    title.textContent = "Pull Request en espera de aprobación";
    branch.textContent = "feat/pendiente";
    base.textContent = "main";
    body.textContent = "El Pull Request se creará automáticamente cuando el pipeline complete con éxito.";
  }
}

function renderTimeline(timeline) {
  const list = document.getElementById("timeline-list");
  if (!list) return;

  if (!timeline || timeline.length === 0) {
    list.innerHTML = "<p class='text-muted'>No hay eventos registrados.</p>";
    return;
  }

  list.innerHTML = "";
  timeline.forEach(item => {
    const div = document.createElement("div");
    div.className = "timeline-item";
    div.innerHTML = `
      <span class="timeline-name">${escapeHtml(item.node_name)}</span>
      <span class="timeline-time">${escapeHtml(item.created_at || "")}</span>
    `;
    list.appendChild(div);
  });
}

/* ==========================================================================
   HUMAN APPROVAL (HITL) ACTIONS
   ========================================================================== */
function initActions() {
  const btnApprove = document.getElementById("btn-approve-run");
  const btnReject = document.getElementById("btn-reject-run");

  if (btnApprove) {
    btnApprove.onclick = async () => {
      if (!currentRunId) return;
      const reviewer = document.getElementById("approval-reviewer-input").value || (currentUser ? currentUser.display_name : "lead-architect");
      const feedback = document.getElementById("approval-feedback-input").value;

      try {
        btnApprove.disabled = true;
        btnApprove.textContent = "Aprobando...";

        const headers = { "Content-Type": "application/json" };
        if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

        const res = await fetch(`/runs/${currentRunId}/approve`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            reviewer,
            decision: "APPROVE",
            feedback,
            role: currentUser ? currentUser.role_title : "Lead Architect"
          })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Error en aprobación");
        }
        // Resume polling
        selectRun(currentRunId);
      } catch (err) {
        alert(err.message);
      } finally {
        btnApprove.disabled = false;
        btnApprove.textContent = "✅ Aprobar y Crear PR";
      }
    };
  }

  if (btnReject) {
    btnReject.onclick = async () => {
      if (!currentRunId) return;
      const reviewer = document.getElementById("approval-reviewer-input").value || (currentUser ? currentUser.display_name : "lead-architect");
      const feedback = document.getElementById("approval-feedback-input").value || "Rechazado por el usuario";

      if (!confirm("¿Segura que deseas rechazar este Pull Request?")) return;

      try {
        btnReject.disabled = true;
        const headers = { "Content-Type": "application/json" };
        if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

        const res = await fetch(`/runs/${currentRunId}/approve`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            reviewer,
            decision: "REJECT",
            feedback,
            role: currentUser ? currentUser.role_title : "Lead Architect"
          })
        });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Error en rechazo");
        }
        selectRun(currentRunId);
      } catch (err) {
        alert(err.message);
      } finally {
        btnReject.disabled = false;
      }
    };
  }

  // Copy code button
  const copyBtn = document.getElementById("btn-copy-code");
  if (copyBtn) {
    copyBtn.onclick = () => {
      const code = document.getElementById("code-display").textContent;
      navigator.clipboard.writeText(code).then(() => {
        copyBtn.textContent = "¡Copiado! ✓";
        setTimeout(() => copyBtn.textContent = "Copiar Código", 2000);
      });
    };
  }

  // Refresh button
  const refreshBtn = document.getElementById("btn-refresh");
  if (refreshBtn) {
    refreshBtn.onclick = () => {
      fetchHealth();
      fetchRuns();
      if (currentRunId) loadRunDetails(currentRunId);
    };
  }
}

/* ==========================================================================
   TABS & MODALS NAVIGATION
   ========================================================================== */
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.onclick = () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const panel = document.getElementById(targetId);
      if (panel) panel.classList.add("active");
    };
  });
}

function initPresets() {
  const presetBtns = document.querySelectorAll(".preset-btn");
  presetBtns.forEach(btn => {
    btn.onclick = () => {
      presetBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const presetKey = btn.getAttribute("data-preset");
      const data = PRESETS[presetKey];
      if (data) {
        document.getElementById("task-title-input").value = data.title;
        document.getElementById("task-desc-input").value = data.desc;
      }
    };
  });
}

function initModals() {
  const openBtn = document.getElementById("btn-new-run");
  if (openBtn) openBtn.onclick = openNewRunModal;

  const submitBtn = document.getElementById("btn-submit-task");
  if (submitBtn) {
    submitBtn.onclick = async () => {
      const title = document.getElementById("task-title-input").value.trim();
      const requirement_text = document.getElementById("task-desc-input").value.trim();
      const workspace_path = document.getElementById("task-workspace-input").value.trim();
      const require_human_pr_approval = document.getElementById("task-hitl-checkbox").checked;

      if (!title || !requirement_text) {
        alert("Por favor completa el título y el requerimiento.");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Iniciando Agentes...";

      try {
        const headers = { "Content-Type": "application/json" };
        if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

        const res = await fetch("/runs", {
          method: "POST",
          headers,
          body: JSON.stringify({
            title,
            requirement_text,
            workspace_path: workspace_path || "sandbox",
            require_human_pr_approval
          })
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Error al crear la tarea");
        }
        const data = await res.json();

        closeNewRunModal();
        await fetchRuns();
        selectRun(data.execution_id);
      } catch (err) {
        alert("Fallo al iniciar tarea: " + err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "🚀 Iniciar Tarea Multi-Agente";
      }
    };
  }
}

function openNewRunModal() {
  document.getElementById("new-run-modal").classList.add("active");
}

function closeNewRunModal() {
  document.getElementById("new-run-modal").classList.remove("active");
}

function triggerSamplePilot() {
  openNewRunModal();
}

/* ==========================================================================
   AUTHENTICATION & RBAC CONTROLLER
   ========================================================================== */
function initAuth() {
  const showLoginBtn = document.getElementById("btn-show-login");
  if (showLoginBtn) {
    showLoginBtn.onclick = openLoginModal;
  }

  const logoutBtn = document.getElementById("btn-logout");
  if (logoutBtn) {
    logoutBtn.onclick = logout;
  }

  // Quick profile buttons in login modal
  const roleButtons = document.querySelectorAll(".role-pill-btn");
  roleButtons.forEach(btn => {
    btn.onclick = () => {
      roleButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const u = btn.getAttribute("data-user");
      const p = btn.getAttribute("data-pwd");
      const uInput = document.getElementById("login-username");
      const pInput = document.getElementById("login-password");
      if (uInput) uInput.value = u;
      if (pInput) pInput.value = p;
    };
  });

  // Verify existing session if token exists
  if (authToken) {
    verifySession();
  } else {
    const savedUser = localStorage.getItem("ai_java_user");
    if (savedUser) {
      try {
        currentUser = JSON.parse(savedUser);
        applyUserSession(currentUser);
      } catch (e) {
        openLoginModal();
      }
    } else {
      // Default to auto-login as admin for immediate usability
      submitLogin("admin", "admin", true);
    }
  }
}

async function verifySession() {
  try {
    const res = await fetch("/auth/me", {
      headers: { "Authorization": `Bearer ${authToken}` }
    });
    if (res.ok) {
      currentUser = await res.json();
      localStorage.setItem("ai_java_user", JSON.stringify(currentUser));
      applyUserSession(currentUser);
    } else {
      localStorage.removeItem("ai_java_token");
      localStorage.removeItem("ai_java_user");
      authToken = null;
      currentUser = null;
      openLoginModal();
    }
  } catch (err) {
    console.warn("Could not verify session:", err);
  }
}

function openLoginModal() {
  const modal = document.getElementById("login-modal");
  if (modal) {
    modal.classList.add("active");
    const errorEl = document.getElementById("login-error-msg");
    if (errorEl) errorEl.style.display = "none";
  }
}

function closeLoginModal() {
  const modal = document.getElementById("login-modal");
  if (modal) modal.classList.remove("active");
}

async function submitLogin(customUser, customPwd, isSilent = false) {
  const username = customUser || document.getElementById("login-username")?.value.trim();
  const password = customPwd || document.getElementById("login-password")?.value.trim();
  const errorEl = document.getElementById("login-error-msg");

  if (!username || !password) {
    if (errorEl) {
      errorEl.textContent = "⚠️ Por favor ingresa usuario y contraseña.";
      errorEl.style.display = "block";
    }
    return;
  }

  const submitBtn = document.getElementById("btn-submit-login");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Verificando...";
  }

  try {
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Credenciales incorrectas.");
    }

    const data = await res.json();
    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem("ai_java_token", authToken);
    localStorage.setItem("ai_java_user", JSON.stringify(currentUser));

    applyUserSession(currentUser);
    closeLoginModal();
  } catch (err) {
    if (!isSilent) {
      if (errorEl) {
        errorEl.textContent = `⚠️ ${err.message}`;
        errorEl.style.display = "block";
      } else {
        alert(err.message);
      }
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "🚀 Ingresar a la Plataforma";
    }
  }
}

async function logout() {
  if (authToken) {
    fetch("/auth/logout", {
      method: "POST",
      headers: { "Authorization": `Bearer ${authToken}` }
    }).catch(() => {});
  }
  localStorage.removeItem("ai_java_token");
  localStorage.removeItem("ai_java_user");
  authToken = null;
  currentUser = null;

  const profileTag = document.getElementById("user-profile-tag");
  if (profileTag) profileTag.style.display = "none";
  const loginBtn = document.getElementById("btn-show-login");
  if (loginBtn) loginBtn.style.display = "inline-flex";

  openLoginModal();
}

function applyUserSession(user) {
  if (!user) return;

  const profileTag = document.getElementById("user-profile-tag");
  const loginBtn = document.getElementById("btn-show-login");
  if (profileTag) profileTag.style.display = "inline-flex";
  if (loginBtn) loginBtn.style.display = "none";

  const avatarEl = document.getElementById("nav-user-avatar");
  const nameEl = document.getElementById("nav-user-name");
  const roleEl = document.getElementById("nav-user-role");

  if (avatarEl) avatarEl.textContent = user.avatar || "👤";
  if (nameEl) nameEl.textContent = user.display_name || user.username;
  if (roleEl) roleEl.textContent = user.role_title || user.role;

  // Reviewer input pre-fill
  const reviewerInput = document.getElementById("approval-reviewer-input");
  if (reviewerInput) {
    reviewerInput.value = `${user.display_name} (${user.role_title})`;
  }

  // Update permissions for active run
  updateApprovalBannerForUser();

  // Task creation permission
  const btnNewRun = document.getElementById("btn-new-run");
  if (btnNewRun) {
    const canCreate = !user.permissions || user.permissions.includes("create_task");
    btnNewRun.disabled = !canCreate;
    btnNewRun.title = canCreate ? "Crear nueva tarea" : "Tu rol actual no tiene permisos para crear tareas.";
    btnNewRun.style.opacity = canCreate ? "1" : "0.5";
  }

  // Highlight ROI banner for operations director (Lorena)
  const roiBanner = document.getElementById("roi-banner");
  if (roiBanner) {
    if (user.role === "operations_director") {
      roiBanner.style.border = "2px solid #38BDF8";
      roiBanner.style.boxShadow = "0 0 20px rgba(56, 189, 248, 0.35)";
    } else {
      roiBanner.style.border = "none";
      roiBanner.style.borderLeft = "4px solid #38BDF8";
      roiBanner.style.boxShadow = "0 4px 6px -1px rgba(0, 0, 0, 0.1)";
    }
  }
}

function updateApprovalBannerForUser() {
  const btnApprove = document.getElementById("btn-approve-run");
  const btnReject = document.getElementById("btn-reject-run");
  const bannerContent = document.querySelector(".approval-banner-content");
  if (!btnApprove || !btnReject) return;

  const canApprove = currentUser ? currentUser.permissions?.includes("approve_pr") : true;

  btnApprove.disabled = !canApprove;
  btnReject.disabled = !canApprove;
  btnApprove.style.opacity = canApprove ? "1" : "0.4";
  btnReject.style.opacity = canApprove ? "1" : "0.4";

  // Existing notice cleanup
  const existingNotice = document.getElementById("approval-permission-notice");
  if (existingNotice) existingNotice.remove();

  if (!canApprove && bannerContent) {
    const notice = document.createElement("div");
    notice.id = "approval-permission-notice";
    notice.className = "permission-blocked-notice";
    notice.innerHTML = `🔒 <em>Aprobación restringida:</em> Tu rol actual (<strong>${currentUser ? currentUser.role_title : "Invitado"}</strong>) no cuenta con autorización para autorizar Pull Requests a producción. Requiere rol <strong>Lead Architect</strong> o <strong>Delivery Manager</strong>.`;
    bannerContent.appendChild(notice);
  }
}

/* ==========================================================================
   HELPERS & UTILITIES
   ========================================================================== */
function getStatusBadge(status) {
  const s = (status || "PENDING").toUpperCase();
  switch (s) {
    case "COMPLETED":
      return '<span class="badge badge-completed">Completado</span>';
    case "RUNNING":
      return '<span class="badge badge-running">En curso</span>';
    case "WAITING_APPROVAL":
      return '<span class="badge badge-waiting">Aprobación</span>';
    case "FAILED":
      return '<span class="badge badge-failed">Fallido</span>';
    case "SECURITY_BLOCKED":
      return '<span class="badge badge-failed">Bloqueado</span>';
    default:
      return '<span class="badge badge-pending">Pendiente</span>';
  }
}

function escapeHtml(str) {
  if (typeof str !== "string") return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/* ==========================================================================
   JIRA INTEGRATION CONTROLLER
   ========================================================================== */
function initJira() {
  const btnOpenJira = document.getElementById("btn-open-jira");
  if (btnOpenJira) {
    btnOpenJira.onclick = openJiraModal;
  }
}

function openJiraModal() {
  const modal = document.getElementById("jira-modal");
  if (modal) {
    modal.classList.add("active");
    loadJiraIssues();
  }
}

function closeJiraModal() {
  const modal = document.getElementById("jira-modal");
  if (modal) {
    modal.classList.remove("active");
  }
}

function openRunForJiraKey(jiraKey) {
  closeJiraModal();
  const card = Array.from(document.querySelectorAll(".run-card")).find(c => {
    return c.textContent.includes(jiraKey);
  });
  if (card) {
    card.click();
    showToast(`Visualizando ejecución para el ticket ${jiraKey}`, "info");
  } else {
    showToast(`Buscando ticket Jira ${jiraKey}...`, "info");
    fetchRuns().then(() => {
      const refreshedCard = Array.from(document.querySelectorAll(".run-card")).find(c => c.textContent.includes(jiraKey));
      if (refreshedCard) refreshedCard.click();
    });
  }
}

async function loadJiraIssues() {
  const container = document.getElementById("jira-issues-container");
  if (!container) return;

  container.innerHTML = '<p class="text-muted text-center" style="padding: 20px;">Cargando tickets de Jira en vivo...</p>';

  try {
    const res = await fetch("/integrations/jira/issues");
    if (!res.ok) throw new Error("Error al consultar backlog de Jira");
    const issues = await res.json();

    if (!issues || issues.length === 0) {
      container.innerHTML = '<p class="text-muted text-center" style="padding: 20px;">No hay tickets pendientes en tu proyecto de Jira en este momento.</p>';
      return;
    }

    container.innerHTML = "";
    issues.forEach(issue => {
      const card = document.createElement("div");
      card.className = "jira-card";

      let priorityClass = "jira-priority-medium";
      if (issue.priority === "Highest") priorityClass = "jira-priority-highest";
      else if (issue.priority === "High") priorityClass = "jira-priority-high";

      const acCount = (issue.acceptance_criteria && issue.acceptance_criteria.length) || 0;
      const statusLower = (issue.status || "").toLowerCase();
      const isReviewOrDone = statusLower.includes("revis") || statusLower.includes("review") || statusLower.includes("finaliz") || statusLower.includes("done");

      let actionButtons = "";
      if (isReviewOrDone) {
        actionButtons = `
          <button class="btn btn-sm btn-outline" style="border: 1px solid var(--accent); color: var(--accent);" onclick="openRunForJiraKey('${escapeHtml(issue.key)}')">
            👁️ Ver en Revisión Humana
          </button>
          <button class="btn btn-sm btn-primary" onclick="importJiraByKey('${escapeHtml(issue.key)}', this)">
            ⚡ Re-ejecutar con Gemini 3.6
          </button>
        `;
      } else {
        actionButtons = `
          <button class="btn btn-sm btn-primary" onclick="importJiraByKey('${escapeHtml(issue.key)}', this)">
            🚀 Asignar a Java X y Ejecutar
          </button>
        `;
      }

      card.innerHTML = `
        <div class="jira-card-header">
          <div class="jira-card-tags">
            <span class="jira-key-badge">${escapeHtml(issue.key)}</span>
            <span class="jira-type-badge">${escapeHtml(issue.issue_type)}</span>
            <span class="jira-priority-badge ${priorityClass}">Prioridad: ${escapeHtml(issue.priority)}</span>
          </div>
          <span style="font-size: 0.8rem; font-weight: 600; color: ${isReviewOrDone ? '#F59E0B' : '#60A5FA'};">${escapeHtml(issue.status)}</span>
        </div>
        <div class="jira-card-title">${escapeHtml(issue.summary)}</div>
        <div class="jira-card-desc">${escapeHtml(issue.description)}</div>
        <div class="jira-card-footer">
          <div class="jira-assignee-info">
            <span>👤 Asignado: <strong>${escapeHtml(issue.assignee)}</strong></span>
            <span>•</span>
            <span>📋 ${acCount} criterios Gherkin</span>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            ${actionButtons}
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<p class="text-danger text-center" style="padding: 20px;">Fallo al conectar con Jira: ${escapeHtml(err.message)}</p>`;
  }
}

async function importJiraByKey(customKey, btnElement) {
  const inputEl = document.getElementById("jira-manual-key-input");
  const key = (customKey || (inputEl ? inputEl.value : "")).trim().toUpperCase();

  if (!key) {
    showToast("Por favor ingresa una clave de ticket Jira válida (ej: SCRUM-5).", "warning");
    return;
  }

  const btn = btnElement || (inputEl ? inputEl.nextElementSibling : null);
  const oldText = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `⏳ Asignando a Java X...`;
  }

  const headers = { "Content-Type": "application/json" };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  try {
    const res = await fetch(`/integrations/jira/import/${key}`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        workspace_path: "sandbox",
        require_human_pr_approval: true
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Error al importar el ticket");
    }

    const data = await res.json();
    closeJiraModal();
    await fetchRuns();
    selectRun(data.execution_id);
    showToast(`🚀 ¡Tarea ${key} asignada a Java X con éxito! Ejecutando pod con Gemini 3.6 Flash...`, "success");
  } catch (err) {
    showToast("Error al importar ticket de Jira: " + err.message, "error");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = oldText;
    }
  }
}

/* ==========================================================================
   TOAST NOTIFICATION COMPONENT
   ========================================================================== */
function showToast(message, type = "info") {
  let toastContainer = document.getElementById("toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toast-container";
    toastContainer.style.cssText = "position: fixed; top: 20px; right: 20px; z-index: 99999; display: flex; flex-direction: column; gap: 10px; max-width: 420px; pointer-events: none;";
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  let bg = "#1E293B";
  let border = "1px solid rgba(255,255,255,0.15)";
  if (type === "success") { bg = "#064E3B"; border = "1px solid #10B981"; }
  else if (type === "error") { bg = "#7F1D1D"; border = "1px solid #EF4444"; }
  else if (type === "warning") { bg = "#78350F"; border = "1px solid #F59E0B"; }
  else if (type === "info") { bg = "#1E3A8A"; border = "1px solid #3B82F6"; }

  toast.style.cssText = `background: ${bg}; border: ${border}; color: #ffffff; padding: 14px 20px; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); font-size: 0.9rem; font-weight: 500; display: flex; align-items: center; gap: 10px; pointer-events: auto; transition: all 0.3s ease;`;
  toast.innerHTML = `<span>${message}</span>`;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 400);
  }, 4500);
}



