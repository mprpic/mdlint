# Multi-line and Nested Backtick Code Spans

This includes types like `HashMap<K,
V>` and other things with `#[derive(Serialize)]`.

Run `cargo rustc -- -Zunstable-options
--pretty=expanded` to see the expanded code.

Add a code fence (three backquotes
` ``` ` on a separate line) before and after your output.
