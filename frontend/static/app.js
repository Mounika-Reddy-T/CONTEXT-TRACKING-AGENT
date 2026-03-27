/**
 * Drive the frontend chat experience for the memory agent project.
 */

const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatMessages = document.getElementById("chatMessages");
const sessionIdInput = document.getElementById("sessionId");
const refreshSessionButton = document.getElementById("refreshSessionButton");
const contextTags = document.getElementById("contextTags");
const memoryList = document.getElementById("memoryList");
const sessionSummary = document.getElementById("sessionSummary");
const guardrailNotes = document.getElementById("guardrailNotes");
const sendButton = document.getElementById("sendButton");

/**
 * Escape HTML-sensitive characters before rendering untrusted text.
 *
 * @param {string} value - Text that should be safely inserted into the DOM.
 * @returns {string} Escaped text suitable for HTML rendering.
 */
function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/**
 * Format plain-text assistant content so markdown-like bullets render on new lines.
 *
 * This keeps rendering safe by escaping HTML first, then inserting line breaks
 * for common list markers produced by LLM responses.
 *
 * @param {string} content - Raw message content returned by the backend.
 * @returns {string} Safely formatted HTML for chat bubble rendering.
 */
function formatMessageContent(content) {
  const normalizedContent = content
    .replace(/\s-\s\*\*/g, "\n- **")
    .replace(/\s-\s/g, "\n- ")
    .trim();

  return escapeHtml(normalizedContent).replaceAll("\n", "<br>");
}

/**
 * Append one rendered message bubble to the visible chat history.
 *
 * @param {string} role - Either `user` or `assistant`.
 * @param {string} content - Message content to render.
 */
function appendMessage(role, content) {
  const bubble = document.createElement("article");
  bubble.className = `chat-bubble ${role}`;
  bubble.innerHTML = formatMessageContent(content);
  chatMessages.appendChild(bubble);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Render the context tags shown in the sidebar panel.
 *
 * @param {string[]} tags - Topic labels derived by the backend.
 */
function renderContextTags(tags) {
  contextTags.innerHTML = "";

  if (!tags.length) {
    contextTags.innerHTML = '<span class="note">No context tags yet.</span>';
    return;
  }

  tags.forEach((tag) => {
    const element = document.createElement("span");
    element.className = "tag";
    element.textContent = tag;
    contextTags.appendChild(element);
  });
}

/**
 * Render the recent memory list returned by the backend.
 *
 * @param {Array<{role: string, content: string, created_at: string}>} items - Stored session messages.
 */
function renderMemory(items) {
  memoryList.innerHTML = "";

  if (!items.length) {
    memoryList.innerHTML = '<div class="memory-item">No remembered interactions yet.</div>';
    return;
  }

  items.forEach((item) => {
    const wrapper = document.createElement("div");
    wrapper.className = "memory-item";
    const safeContent = escapeHtml(item.content);
    wrapper.innerHTML = `<strong>${escapeHtml(item.role)}</strong><span>${safeContent}</span>`;
    memoryList.appendChild(wrapper);
  });
}

/**
 * Render any guardrail notes returned by the backend.
 *
 * @param {string[]} notes - Guardrail notes associated with the latest request.
 */
function renderGuardrailNotes(notes) {
  guardrailNotes.innerHTML = "";

  if (!notes.length) {
    return;
  }

  notes.forEach((note) => {
    const element = document.createElement("span");
    element.className = "note";
    element.textContent = note;
    guardrailNotes.appendChild(element);
  });
}

/**
 * Fetch the current session snapshot and update the sidebar.
 */
async function refreshSessionSnapshot() {
  const sessionId = sessionIdInput.value.trim();

  if (!sessionId) {
    return;
  }

  const response = await fetch(`/api/session/${encodeURIComponent(sessionId)}`);
  const data = await response.json();

  renderContextTags(data.context_tags);
  renderMemory(data.recent_memory);
  sessionSummary.textContent = data.summary || "No summary available yet.";
}

/**
 * Submit a message to the backend and render the assistant response.
 *
 * @param {SubmitEvent} event - Browser form submission event.
 */
async function handleSubmit(event) {
  event.preventDefault();

  const message = messageInput.value.trim();
  const sessionId = sessionIdInput.value.trim();

  if (!message || !sessionId) {
    return;
  }

  sendButton.disabled = true;
  appendMessage("user", message);
  messageInput.value = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error("The backend could not process the message.");
    }

    const data = await response.json();
    appendMessage("assistant", data.response);
    renderContextTags(data.context_tags);
    renderMemory(data.recent_memory);
    renderGuardrailNotes(data.guardrail_notes);
    await refreshSessionSnapshot();
  } catch (error) {
    appendMessage("assistant", `Error: ${error.message}`);
  } finally {
    sendButton.disabled = false;
  }
}

chatForm.addEventListener("submit", handleSubmit);
refreshSessionButton.addEventListener("click", refreshSessionSnapshot);
refreshSessionSnapshot();
