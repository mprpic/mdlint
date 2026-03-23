# HTML blocks with reversed link patterns

<pre class="codeblock"><code class="python">bulk = 100
for idx in range(0, len(bugs), bulk):
    res = bz.get_comments(bugs[idx:idx + bulk])['bugs']</code></pre>

<div>
Some (text)[inside] an HTML block.
</div>
