---
hide:
  - toc
---

# Playground

Paste some Markdown below, add configuration if desired, and click **Lint** to check it for style violations by
running `mdlint` in the browser.

<div id="playground-container" markdown>

<div id="playground-status">
  <div class="playground-spinner"></div>
  <span>Loading Python runtime (this may take a moment)...</span>
</div>

<div id="playground-editor" style="display: none" markdown>

=== "Markdown"

    <textarea id="md-input" class="playground-textarea" spellcheck="false" rows="16"></textarea>

=== "Configuration"

    <textarea id="config-input" class="playground-textarea" spellcheck="false" rows="16" placeholder="# .mdlint.toml format&#10;# Example:&#10;#&#10;# select = [&quot;MD001&quot;, &quot;MD003&quot;, &quot;MD004&quot;]&#10;# ignore = [&quot;MD013&quot;]&#10;#&#10;# [rules.MD003]&#10;# style = &quot;atx&quot;&#10;#&#10;# [rules.MD004]&#10;# style = &quot;dash&quot;"></textarea>

<div id="playground-controls">
  <button id="lint-btn" type="button">Lint</button>
</div>
<pre id="lint-output"></pre>

</div>

</div>
