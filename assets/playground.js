(function () {
  "use strict";

  function initPlayground() {
    var container = document.getElementById("playground-container");
    if (!container || container.dataset.initialized) return;
    container.dataset.initialized = "true";

    var statusEl = document.getElementById("playground-status");
    var editorEl = document.getElementById("playground-editor");
    var lintBtn = document.getElementById("lint-btn");
    var inputEl = document.getElementById("md-input");
    var configEl = document.getElementById("config-input");
    var outputEl = document.getElementById("lint-output");

    var pyodide = null;
    var linterReady = false;

    // Set default sample content (set via JS to avoid Markdown processing)
    if (!inputEl.value) {
      inputEl.value = [
        "## Introduction",
        "",
        "This is a sample document with some issues.",
        "",
        "### Details",
        "",
        "* First item",
        "+ Second item",
        "- Third item",
        "",
        "#Bad ATX heading",
        "",
        "This is a [broken link]() example.",
        "",
        "Visit https://example.com for more info.",
        "",
      ].join("\n");
    }

    async function setup() {
      try {
        // Load Pyodide from CDN if not already loaded
        if (!window.loadPyodide) {
          await new Promise(function (resolve, reject) {
            var s = document.createElement("script");
            s.src =
              "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.js";
            s.onload = resolve;
            s.onerror = function () {
              reject(new Error("Failed to load Pyodide from CDN"));
            };
            document.head.appendChild(s);
          });
        }

        pyodide = await loadPyodide();

        statusEl.querySelector("span").textContent =
          "Installing packages...";
        await pyodide.loadPackage("micropip");
        await pyodide.runPythonAsync(
          "import micropip\nawait micropip.install(['markdown-it-py', 'mdit-py-plugins'])",
        );

        // Fetch and unpack mdlint source
        statusEl.querySelector("span").textContent = "Loading mdlint...";
        var resp = await fetch("../assets/mdlint-src.zip");
        if (!resp.ok) throw new Error("Failed to fetch mdlint source archive");
        var buffer = await resp.arrayBuffer();
        pyodide.unpackArchive(buffer, "zip", {
          extractDir: "/home/pyodide/",
        });

        // Define the linting function in Python (imports run once, not per call)
        await pyodide.runPythonAsync(
          [
            "import sys",
            "import tomllib",
            "sys.path.insert(0, '/home/pyodide/')",
            "from mdlint.config import Configuration, build_rule_configs",
            "from mdlint.linter import Linter",
            "",
            "def _playground_lint(content, config_toml):",
            "    config_data = tomllib.loads(config_toml) if config_toml else {}",
            "    rule_configs = build_rule_configs(config_data)",
            "    config = Configuration(",
            "        rules=rule_configs,",
            "        select=config_data.get('select', []),",
            "        ignore=config_data.get('ignore', []),",
            "    )",
            "    linter = Linter(rule_configs=config.rules, enabled_rules=config.enabled_rules)",
            "    result = linter.lint_stdin(content)",
            "    lines = []",
            "    for v in result.violations:",
            '        lc = f"{v.line}:{v.column}"',
            '        lines.append(f"{lc:>6}  {v.rule_id}/{v.rule_name}  {v.message}")',
            "    if lines:",
            "        total = len(result.violations)",
            '        vword = "violation" if total == 1 else "violations"',
            '        return "\\n".join(lines) + f"\\n\\n\\u2718 Found {total} {vword}"',
            '    return "\\u2714 No violations found!"',
          ].join("\n"),
        );

        linterReady = true;
        statusEl.style.display = "none";
        editorEl.style.display = "";

        lintBtn.addEventListener("click", runLint);
      } catch (err) {
        statusEl.querySelector("span").textContent =
          "Failed to load playground: " + err.message;
        statusEl.classList.add("error");
        console.error("Playground init failed:", err);
      }
    }

    function runLint() {
      if (!linterReady) return;

      var content = inputEl.value;
      if (!content.trim()) {
        outputEl.textContent = "Enter some Markdown to lint.";
        outputEl.className = "playground-output";
        return;
      }

      pyodide.globals.set("_md_content", content);
      pyodide.globals.set("_config_toml", configEl.value.trim());

      var result;
      try {
        result = pyodide.runPython(
          "_playground_lint(_md_content, _config_toml)",
        );
      } catch (err) {
        var msg = err.message || String(err);
        // Extract the Python error message (last line of traceback)
        var lines = msg.split("\n").filter(function (l) {
          return l.trim();
        });
        var pyErr = lines[lines.length - 1] || msg;
        outputEl.textContent = "Configuration error: " + pyErr;
        outputEl.className = "playground-output violations";
        return;
      }

      outputEl.textContent = result;
      outputEl.className = result.includes("\u2714")
        ? "playground-output success"
        : "playground-output violations";
    }

    setup();
  }

  // Support MkDocs Material instant navigation
  if (typeof document$ !== "undefined") {
    document$.subscribe(initPlayground);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPlayground);
  } else {
    initPlayground();
  }
})();
