(function () {
  const PROPOSAL_ISSUE_URL =
    "https://github.com/chentaow-splunk/o11y-otel-cookbooks/issues/new?template=recipe-proposal.yml";

  function siteUrl(path) {
    const script = document.currentScript || document.querySelector('script[src$="scenario-assistant.js"]');
    const base = script && script.src ? script.src : window.location.href;
    return new URL(`../${path}`, base).toString();
  }

  function endpointUrl(path) {
    return new URL(path, window.location.origin).toString();
  }

  function cookbookUrl(path) {
    if (!path || path === "#") return "#";
    if (/^https?:\/\//.test(path)) return path;
    return siteUrl(path);
  }

  function injectHeaderAction() {
    const header = document.querySelector(".md-header__inner");
    if (!header || header.querySelector(".header-recipe-action")) {
      return;
    }

    const link = document.createElement("a");
    link.className = "header-recipe-action";
    link.href = PROPOSAL_ISSUE_URL;
    link.textContent = "Submit recipe";
    link.target = "_blank";
    link.rel = "noopener";
    link.setAttribute("aria-label", "Submit a community-supported recipe proposal");

    const searchButton = header.querySelector('label[for="__search"]');
    const palette = header.querySelector('[data-md-component="palette"]');
    header.insertBefore(link, palette || searchButton || null);
  }

  function injectAiAdvisor() {
    const existing = document.querySelector("[data-ai-assistant]");
    if (existing) return existing;

    const shell = document.createElement("div");
    shell.className = "ai-sidebar-shell";
    shell.innerHTML = `
      <button class="ai-sidebar-toggle" type="button" data-ai-toggle aria-controls="ai-advisor-sidebar" aria-expanded="false">
        AI Advisor
      </button>
      <div class="ai-sidebar-backdrop" data-ai-backdrop hidden></div>
      <aside class="ai-sidebar" id="ai-advisor-sidebar" aria-labelledby="ai-advisor-title" aria-hidden="true" data-ai-assistant data-assistant-endpoint="/api/scenario-assistant">
        <div class="ai-sidebar-header">
          <div>
            <p class="scenario-eyebrow">AI advisor</p>
            <h2 id="ai-advisor-title">Cookbook recommendation</h2>
          </div>
          <button class="ai-sidebar-close" type="button" data-ai-close aria-label="Close AI advisor">Close</button>
        </div>

        <p class="ai-sidebar-status" data-ai-status>Requires the server-side OpenAI endpoint.</p>

        <form class="ai-advisor-form" data-ai-form>
          <label>
            <span>Scenario</span>
            <textarea data-ai-input rows="5" placeholder="Example: I need minimum collector sizing for a Windows .NET app and an AKS PoC with gateway collectors." autocomplete="off"></textarea>
          </label>
          <label class="ai-api-key-field">
            <span>OpenAI API key for this request</span>
            <input type="password" data-ai-api-key placeholder="Optional. Leave blank if the backend already has a key." autocomplete="off" autocapitalize="none" spellcheck="false" />
            <small>Your key is kept only in this page's memory until you submit. This page does not store it in localStorage, sessionStorage, cookies, or the repository. If entered, it is sent only with this assistant request to the configured backend and then cleared from the form.</small>
          </label>
          <button type="submit">Ask AI</button>
        </form>

        <div class="assistant-suggestions" aria-label="Suggested prompts">
          <button type="button" data-ai-prompt="I need minimum collector sizing for a Windows .NET app and an AKS PoC.">Windows and AKS sizing</button>
          <button type="button" data-ai-prompt="Which cookbook should I use for Kubernetes collector gateway deployment?">Kubernetes gateway</button>
          <button type="button" data-ai-prompt="I need OpenTelemetry instrumentation guidance for Python on Kubernetes.">Python on Kubernetes</button>
          <button type="button" data-ai-prompt="I need GenAI tracing for OpenAI or Bedrock workloads.">GenAI traces</button>
        </div>

        <div class="ai-answer" data-ai-answer aria-live="polite" hidden></div>
      </aside>`;

    document.body.appendChild(shell);
    return shell.querySelector("[data-ai-assistant]");
  }

  injectHeaderAction();

  const aiRoot = injectAiAdvisor();
  const browseRoot = document.querySelector("[data-scenario-home]");

  const browseState = {
    scenarios: [],
    categories: [],
    supportStatuses: [],
    category: "all",
    supportStatus: "all",
    query: "",
    showAll: false,
  };

  const browse = {
    chips: document.querySelector("[data-scenario-chips]"),
    supportChips: document.querySelector("[data-support-chips]"),
    search: document.querySelector("[data-scenario-search]"),
    results: document.querySelector("[data-scenario-results]"),
    count: document.querySelector("[data-scenario-count]"),
    empty: document.querySelector("[data-scenario-empty]"),
    showAll: document.querySelector("[data-scenario-show-all]"),
  };

  const aiShell = aiRoot ? aiRoot.closest(".ai-sidebar-shell") : null;
  const ai = {
    form: aiRoot ? aiRoot.querySelector("[data-ai-form]") : null,
    input: aiRoot ? aiRoot.querySelector("[data-ai-input]") : null,
    apiKey: aiRoot ? aiRoot.querySelector("[data-ai-api-key]") : null,
    answer: aiRoot ? aiRoot.querySelector("[data-ai-answer]") : null,
    status: aiRoot ? aiRoot.querySelector("[data-ai-status]") : null,
    buttons: aiRoot ? aiRoot.querySelectorAll("[data-ai-prompt]") : [],
    toggle: aiShell ? aiShell.querySelector("[data-ai-toggle]") : null,
    backdrop: aiShell ? aiShell.querySelector("[data-ai-backdrop]") : null,
    close: aiShell ? aiShell.querySelector("[data-ai-close]") : null,
  };

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function textForBrowse(scenario) {
    return [
      scenario.title,
      scenario.category,
      scenario.summary,
      scenario.sourcePath,
      scenario.supportStatus,
      scenario.supportLabel,
      scenario.supportDescription,
      scenario.supportSource,
      ...(scenario.tags || []),
    ].join(" ").toLowerCase();
  }

  function visibleScenarios() {
    const terms = browseState.query
      .toLowerCase()
      .split(/[^a-z0-9.+#-]+/)
      .filter(Boolean);

    return browseState.scenarios
      .filter((scenario) => browseState.category === "all" || scenario.category === browseState.category)
      .filter(
        (scenario) => browseState.supportStatus === "all" || scenario.supportStatus === browseState.supportStatus
      )
      .filter((scenario) => {
        if (!terms.length) return true;
        const haystack = textForBrowse(scenario);
        return terms.every((term) => haystack.includes(term));
      })
      .sort((a, b) => {
        if (a.category !== b.category) {
          return a.category.localeCompare(b.category);
        }
        return a.title.localeCompare(b.title);
      });
  }

  function renderChips() {
    if (!browse.chips) return;

    const chips = [
      `<button class="scenario-chip is-active" type="button" data-category="all">All</button>`,
      ...browseState.categories.map(
        (category) =>
          `<button class="scenario-chip" type="button" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`
      ),
    ];

    browse.chips.innerHTML = chips.join("");
    browse.chips.addEventListener("click", (event) => {
      const button = event.target.closest("[data-category]");
      if (!button) return;
      browseState.category = button.dataset.category;
      browseState.showAll = false;
      browse.chips
        .querySelectorAll(".scenario-chip")
        .forEach((chip) => chip.classList.toggle("is-active", chip === button));
      renderResults();
    });
  }

  function supportClass(status) {
    return String(status || "unknown").toLowerCase().replace(/[^a-z0-9-]/g, "");
  }

  function supportPill(item) {
    const status = supportClass(item.supportStatus);
    const label = item.supportLabel || "Unclassified";
    const description = item.supportDescription || "";
    return `<span class="support-pill support-pill--${escapeHtml(status)}" title="${escapeHtml(description)}">${escapeHtml(label)}</span>`;
  }

  function renderSupportChips() {
    if (!browse.supportChips) return;

    const chips = [
      `<button class="scenario-chip is-active" type="button" data-support-status="all">All statuses</button>`,
      ...browseState.supportStatuses.map((profile) => {
        const status = profile.status || "";
        const label = profile.label || status;
        return `<button class="scenario-chip" type="button" data-support-status="${escapeHtml(status)}">${escapeHtml(label)}</button>`;
      }),
    ];

    browse.supportChips.innerHTML = chips.join("");
    browse.supportChips.addEventListener("click", (event) => {
      const button = event.target.closest("[data-support-status]");
      if (!button) return;
      browseState.supportStatus = button.dataset.supportStatus || "all";
      browseState.showAll = false;
      browse.supportChips
        .querySelectorAll(".scenario-chip")
        .forEach((chip) => chip.classList.toggle("is-active", chip === button));
      renderResults();
    });
  }

  function renderResults() {
    if (!browse.results) return;

    const allMatches = visibleScenarios();
    const maxRows = browseState.showAll ? allMatches.length : browseState.query || browseState.category !== "all" ? 30 : 16;
    const matches = allMatches.slice(0, maxRows);

    browse.results.innerHTML = matches
      .map((scenario) => {
        const tags = (scenario.tags || [])
          .slice(0, 5)
          .map((tag) => `<span>${escapeHtml(tag)}</span>`)
          .join("");
        return `
          <tr>
            <td>
              <a class="scenario-title" href="${escapeHtml(scenario.url)}">${escapeHtml(scenario.title)}</a>
              <p>${escapeHtml(scenario.summary || scenario.sourcePath || "")}</p>
            </td>
            <td>${supportPill(scenario)}</td>
            <td>${escapeHtml(scenario.category)}</td>
            <td><div class="scenario-tags">${tags}</div></td>
          </tr>`;
      })
      .join("");

    if (browse.count) {
      browse.count.textContent = `Showing ${matches.length} of ${allMatches.length} matching scenarios`;
    }

    if (browse.empty) {
      browse.empty.hidden = allMatches.length > 0;
    }

    if (browse.showAll) {
      browse.showAll.hidden = allMatches.length <= matches.length;
      browse.showAll.textContent = `Show all ${allMatches.length} matches`;
    }
  }

  function setAiOpen(isOpen) {
    if (!aiRoot || !aiShell) return;
    aiShell.classList.toggle("is-open", isOpen);
    aiRoot.setAttribute("aria-hidden", String(!isOpen));
    if (ai.toggle) {
      ai.toggle.setAttribute("aria-expanded", String(isOpen));
    }
    if (ai.backdrop) {
      ai.backdrop.hidden = !isOpen;
    }
    document.documentElement.classList.toggle("ai-sidebar-open", isOpen);
    if (isOpen && ai.input) {
      window.setTimeout(() => ai.input.focus(), 120);
    }
  }

  function setAiStatus(message, mode) {
    if (!ai.status) return;
    ai.status.textContent = message;
    ai.status.dataset.mode = mode || "neutral";
  }

  function setAiBusy(isBusy) {
    if (ai.form) {
      ai.form.querySelectorAll("button, textarea, input").forEach((element) => {
        element.disabled = isBusy;
      });
    }
    ai.buttons.forEach((button) => {
      button.disabled = isBusy;
    });
  }

  function renderAiAnswer(payload) {
    if (!ai.answer) return;

    const recommendations = Array.isArray(payload.recommendations) ? payload.recommendations : [];
    const recommendationHtml = recommendations.length
      ? `<ol class="ai-recommendations">${recommendations
          .map(
            (item) => `
              <li>
                <a href="${escapeHtml(cookbookUrl(item.url || "#"))}">${escapeHtml(item.title || "Untitled cookbook")}</a>
                <span>${supportPill(item)}</span>
                <span>${escapeHtml(item.category || item.sourcePath || "")}</span>
                <p>${escapeHtml(item.why || "")}</p>
              </li>`
          )
          .join("")}</ol>`
      : `<p>No cookbook recommendation was returned for this scenario.</p>`;

    ai.answer.hidden = false;
    ai.answer.innerHTML = `
      <div class="ai-answer-summary">
        <p>${escapeHtml(payload.answer || "Review the recommended cookbooks below.")}</p>
      </div>
      ${recommendationHtml}`;
  }

  async function askAi(question) {
    if (!aiRoot) return;
    const endpoint = aiRoot.dataset.assistantEndpoint || "/api/scenario-assistant";
    const apiKey = ai.apiKey ? ai.apiKey.value.trim() : "";
    const requestBody = { question };
    if (apiKey) {
      requestBody.apiKey = apiKey;
    }
    setAiOpen(true);
    setAiBusy(true);
    setAiStatus(
      apiKey ? "Asking the advisor with your per-request key..." : "Asking the OpenAI-backed advisor...",
      "pending"
    );

    try {
      const response = await fetch(endpointUrl(endpoint), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.error || `Assistant endpoint returned HTTP ${response.status}`);
      }

      renderAiAnswer(payload);
      setAiStatus("Recommendation generated from the examples knowledge base.", "ready");
    } catch (error) {
      if (ai.answer) {
        ai.answer.hidden = false;
        ai.answer.innerHTML = `
          <div class="ai-answer-summary ai-answer-error">
            <p>${escapeHtml(error.message)}</p>
          </div>`;
      }
      setAiStatus("Assistant backend unavailable.", "error");
    } finally {
      if (ai.apiKey) {
        ai.apiKey.value = "";
      }
      setAiBusy(false);
    }
  }

  async function initBrowse() {
    if (!browseRoot) return;
    try {
      const response = await fetch(siteUrl("assets/scenario-index.json"), { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Scenario index returned ${response.status}`);
      }
      const data = await response.json();
      browseState.scenarios = data.scenarios || [];
      browseState.categories = data.categories || [];
      browseState.supportStatuses = data.supportStatuses || [];
      renderChips();
      renderSupportChips();
      renderResults();
    } catch (error) {
      if (browse.count) {
        browse.count.textContent = "Scenario index could not be loaded. Use the sidebar navigation instead.";
      }
      console.warn(error);
    }
  }

  if (browse.search) {
    browse.search.addEventListener("input", (event) => {
      browseState.query = event.target.value;
      browseState.showAll = false;
      renderResults();
    });
  }

  if (browse.showAll) {
    browse.showAll.addEventListener("click", () => {
      browseState.showAll = true;
      renderResults();
    });
  }

  if (ai.toggle) {
    ai.toggle.addEventListener("click", () => {
      setAiOpen(!aiShell.classList.contains("is-open"));
    });
  }

  if (ai.close) {
    ai.close.addEventListener("click", () => setAiOpen(false));
  }

  if (ai.backdrop) {
    ai.backdrop.addEventListener("click", () => setAiOpen(false));
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setAiOpen(false);
    }
  });

  if (ai.form && ai.input) {
    ai.form.addEventListener("submit", (event) => {
      event.preventDefault();
      const question = ai.input.value.trim();
      if (!question) return;
      askAi(question);
    });
  }

  ai.buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const prompt = button.dataset.aiPrompt || button.textContent || "";
      if (ai.input) {
        ai.input.value = prompt;
      }
      askAi(prompt);
    });
  });

  initBrowse();
})();
