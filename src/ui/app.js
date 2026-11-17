const apiKeyInput = document.getElementById("api-key");
const projectInput = document.getElementById("project-id");
const questionInput = document.getElementById("question");
const askButton = document.getElementById("ask");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const answerEl = document.getElementById("answer");
const confidenceEl = document.getElementById("confidence");
const citationsEl = document.getElementById("citations");
const errorEl = document.getElementById("error");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function renderCitations(citations) {
  if (!citations.length) {
    citationsEl.innerHTML = '<p class="meta">No citations.</p>';
    return;
  }

  citationsEl.innerHTML = citations.map((citation) => {
    const meta = [
      citation.asset_name && `Document: ${escapeHtml(citation.asset_name)}`,
      citation.page != null && `Page: ${escapeHtml(citation.page)}`,
      citation.doc_type && `Type: ${escapeHtml(citation.doc_type)}`,
      citation.section && `Section: ${escapeHtml(citation.section)}`,
      citation.chunk_id != null && `Chunk: ${escapeHtml(citation.chunk_id)}`,
      citation.score != null && `Score: ${Number(citation.score).toFixed(3)}`,
    ].filter(Boolean).join(" · ");

    return `<div class="citation">
      <div class="meta">${meta}</div>
      <blockquote>${escapeHtml(citation.quote)}</blockquote>
    </div>`;
  }).join("");
}

async function ask() {
  const question = questionInput.value.trim();
  const projectId = projectInput.value.trim();
  if (!question || !projectId) {
    showError("Enter a project ID and a question.");
    return;
  }

  errorEl.classList.add("hidden");
  resultEl.classList.add("hidden");
  statusEl.textContent = "Asking…";
  askButton.disabled = true;

  try {
    const headers = {"Content-Type": "application/json"};
    const apiKey = apiKeyInput.value.trim();
    if (apiKey) headers["X-API-Key"] = apiKey;

    const response = await fetch(`/api/v1/nlp/index/answer/${encodeURIComponent(projectId)}`, {
      method: "POST",
      headers,
      body: JSON.stringify({text: question, limit: 5}),
    });

    const data = await response.json();
    if (!response.ok) {
      showError(data.detail || data.signal || `Request failed (${response.status})`);
      return;
    }

    answerEl.textContent = data.answer;
    confidenceEl.textContent = data.low_confidence ? "Low confidence" : "Grounded";
    confidenceEl.className = data.low_confidence ? "badge low" : "badge";
    renderCitations(data.citations || []);
    resultEl.classList.remove("hidden");
  } catch (error) {
    showError(String(error));
  } finally {
    statusEl.textContent = "";
    askButton.disabled = false;
  }
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.classList.remove("hidden");
}

askButton.addEventListener("click", ask);
questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) ask();
});
