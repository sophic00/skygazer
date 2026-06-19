+++
title = "Testing Modern Footnote Styling"
description = "A sample post demonstrating the clean, aligned footnotes style inspired by kacaii.dev."
date = 2026-06-19
draft = false
extra = { disabled = true }
+++

This post serves as a test page for our newly implemented footnote styling. The goal is to verify that in-text references and bottom footnotes render cleanly and behave exactly like the modern layout seen on **kacaii.dev**.

## Single-Digit Footnotes

Footnotes are extremely useful for adding side thoughts[^1] or providing definitions without interrupting the primary narrative flow. For example, we might mention Zola[^2], our static site generator of choice.

Notice how clicking the superscript number smoothly jumps you down to the footnote. Clicking the footnote number prefix at the bottom should navigate you right back to your exact reading position in this paragraph.

## Multi-Paragraph Footnotes

Sometimes, a citation or aside requires more detail and spans multiple paragraphs[^3]. In these cases, our CSS should ensure that the prefix number at the bottom aligns perfectly with the top line of the first paragraph, and doesn't get pushed down.

## Alignment & Double-Digit Footnotes

To verify vertical alignment of footnote markers when the count exceeds nine, we can skip ahead and define a double-digit footnote[^10]. With our CSS prefix styling (`text-align: right` and a fixed width), the decimal points for `1.`, `2.`, `3.`, and `10.` should align perfectly in a straight vertical column.

[^1]: This is a simple, single-line footnote to verify the basic layout.

[^2]: Zola is a fast, single-binary static site generator written in Rust.

[^3]: This is the first paragraph of a multi-paragraph footnote.

    And this is the second paragraph of the same footnote, showing how the content flows naturally while the number prefix remains anchored to the top-left.

[^10]: This is a double-digit footnote to test the right-alignment of numbers. Notice how the dot after the number aligns vertically with the dots of single-digit footnotes.
