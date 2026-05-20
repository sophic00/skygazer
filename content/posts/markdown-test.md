+++
title = "Markdown Elements Test Guide"
date = 2026-05-19
description = "A demonstration of various Markdown elements to test the site's layout, typography, and styling."
[taxonomies]
tags = ["test", "formatting", "markdown"]
+++

This post is a visual formatting showcase. It contains different Markdown elements so we can check how headers, blockquotes, lists, tables, and code snippets render in both the current theme and the proposed responsive design.

## Typography Elements

Here is some regular paragraph text. Web typography should be easy to read and comfortable to scan. Below are different heading levels:

### Heading Level 3
And a minor heading for sub-sections:
#### Heading Level 4

---

## Blockquotes

> "Simplicity is the ultimate sophistication."
> 
> — Leonardo da Vinci

Here is a multi-paragraph blockquote to test internal margin spacing:
> Minimalist web design isn't just about removing things.
> 
> It's about ensuring that the elements that remain have maximum impact, readability, and speed.

---

## Lists and Details

Let's test an ordered and unordered list layout:

* **Minimalist Design**: Zero tracking, lightweight CSS, high accessibility.
* **Modern Tools**:
  * Zola Static Site Generator
  * CSS Custom Variables
  * Fluid Layouts

1. First, create your content using Markdown.
2. Second, compile the website with `zola build`.
3. Finally, deploy to your server.

---

## Code Snippets

Testing inline code like `const blog = "Zola";` and block code syntax highlighting:

```rust
// Rust hello world block to test code formatting
fn main() {
    let name = "Sophic";
    println!("Hello, {}!", name);
}
```

```css
/* Inline styles to test custom scrollbars and background */
:root {
  --accent: #4f46e5;
  --bg-primary: #f8fafc;
}
```

---

## Tables

Testing default table borders, alignment, and responsiveness:

| Feature | Standard Blog | Zola Bear |
| :--- | :--- | :--- |
| **Page Size** | ~2.5 MB | **~5 KB** |
| **Dependencies** | heavy JS, ads, trackers | **None** |
| **LCP Speed** | >2.5s | **<0.2s** |
| **Self-Hosted** | Hard | **Super Easy** |

---

Thank you for exploring this formatting showcase. We'll use these posts to inspect and verify the visual styling updates!
