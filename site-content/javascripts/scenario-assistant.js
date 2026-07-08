(function () {
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
    link.href = siteUrl("contributing/propose-recipe/");
    link.textContent = "Propose recipe";
    link.setAttribute("aria-label", "Propose a recipe for the examples backend");

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
    category: "all",
    query: "",
    showAll: false,
  };

  const browse = {
    chips: document.querySelector("[data-scenario-chips]"),
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
      ai.form.querySelectorAll("button, textarea").forEach((element) => {
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
    setAiOpen(true);
    setAiBusy(true);
    setAiStatus("Asking the OpenAI-backed advisor...", "pending");

    try {
      const response = await fetch(endpointUrl(endpoint), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
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
      renderChips();
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
