# Design System Specification: Luminous Minimalist

## 1. Overview & Creative North Star
**Creative North Star: The Digital Gallery**
This design system is built on the philosophy of "Luminous Intent." Rather than filling a screen with containers and lines, we treat the interface as a high-end editorial gallery. Every element must earn its place. We break the "template" look by utilizing extreme whitespace, intentional asymmetry, and a focus on optical rhythm.

The system moves away from traditional flat design into a tactile, layered experience. We use depth not just for decoration, but to signify importance. By overlapping glass-morphic surfaces and using high-contrast typographic scales, we create a professional environment that feels airy, premium, and human-centric.

## 2. Colors & Tonal Depth
Our palette is rooted in light and clarity. The primary objective is to use color to guide the eye without overwhelming the content.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders to section off content. Boundaries must be defined solely through background color shifts or tonal transitions. 
*   **Example:** A `surface-container-low` (#f3f3f5) card should sit on a `surface` (#f9f9fb) background. The change in hex code provides the "border" naturally.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of fine paper and frosted glass.
*   **Base:** `surface` (#f9f9fb) is the canvas.
*   **Level 1 (Subtle Inset):** `surface-container-low` (#f3f3f5) for large structural areas like sidebars.
*   **Level 2 (The Primary Card):** `surface-container-lowest` (#ffffff) for the highest-priority content blocks.
*   **Level 3 (Interactive/Floating):** Use glassmorphism (Semi-transparent `surface-container-lowest` with a 20px-40px Backdrop Blur).

### The "Glass & Gradient" Rule
To escape a "generic" aesthetic, utilize subtle gradients on primary interactive elements.
*   **Primary Action Gradient:** Linear transition from `primary` (#0058bc) to `primary-container` (#0070eb) at a 135-degree angle. This adds "soul" and a sense of light source to the vibrant blue.
*   **Glass Floating Elements:** Use 70% opacity on `surface-container-lowest` for floating navigation or tooltips to allow underlying content to bleed through softly.

## 3. Typography
We utilize a sophisticated typographic scale to establish authority. While the system uses **Inter** (as defined in the tokens), it should be typeset to mimic the precision of high-end editorial magazines.

*   **Display Scale (`display-lg` 3.5rem):** Reserved for hero moments. Use tight letter-spacing (-0.02em) and bold weights to create a "San Francisco" bold aesthetic.
*   **Headline Scale (`headline-md` 1.75rem):** Used for section starts. Ensure generous vertical breathing room above and below.
*   **The Body-Label Relationship:** Contrast the `body-lg` (1rem) for content with `label-md` (0.75rem) in all-caps for metadata or categories to create a rhythmic hierarchy.
*   **Brand Identity:** Hierarchy is conveyed through scale contrast, not just weight. A very large `display-sm` next to a `body-md` creates a premium "bespoke" feel.

## 4. Elevation & Depth
Hierarchy is achieved through **Tonal Layering** rather than structural rigidity.

*   **The Layering Principle:** Stack surfaces from darkest to lightest. Place a `surface-container-lowest` (pure white) card on a `surface-container-low` section to create a soft, natural lift without needing a shadow.
*   **Ambient Shadows:** For floating components (Modals, Hovered Cards), use extra-diffused shadows.
    *   *Shadow Formula:* `0px 12px 32px rgba(26, 28, 29, 0.06)`. The shadow color must be a tinted version of `on-surface` (#1a1c1d) at extremely low opacity to mimic natural ambient light.
*   **The "Ghost Border" Fallback:** If a container sits on a background of the same color and requires definition for accessibility, use a **Ghost Border**: `outline-variant` (#c1c6d7) at 15% opacity. Never use 100% opaque borders.
*   **Glassmorphism Depth:** When using glass layers, ensure the `backdrop-blur` is high (min 16px). This integrates the element into the layout rather than making it look "pasted on."

## 5. Components

### Buttons
*   **Primary:** Pill-shaped (`full` 9999px radius) or `xl` (1.5rem). Uses the Primary Gradient. Text is `on-primary` (#ffffff).
*   **Secondary:** `surface-container-highest` background with `on-surface-variant` text. No border.
*   **Tertiary:** Transparent background, `primary` text. Use for low-emphasis actions.

### Cards & Lists
*   **Rule:** Forbid the use of divider lines.
*   **Card Styling:** Use `xl` (1.5rem) corner radius. Use background color shifts (`surface-container-lowest`) to define the card area.
*   **Lists:** Separate list items with 16px of vertical white space (Spacing Scale) instead of lines.

### Input Fields
*   **Visual Style:** Subtle `surface-container-high` (#e8e8ea) background with `md` (0.75rem) corners.
*   **Focus State:** A "Ghost Border" of `primary` at 40% opacity and a subtle 2px glow.
*   **Text:** Labels use `label-md` placed 8px above the field.

### Selection Chips
*   **Style:** `md` radius. Unselected chips use `surface-container-high`. Selected chips use `secondary-container` (#a1befd) with `on-secondary-container` text.

### Additional Suggestion: The "Utility Float"
A custom component for this system: A semi-transparent glass bar (70% `surface-container-lowest`, 24px blur) that floats at the bottom of the screen for secondary actions, mimicking the iOS dock.

## 6. Do's and Don'ts

### Do:
*   **Do** use asymmetrical margins (e.g., more padding on the left than right in a hero) to create a modern editorial feel.
*   **Do** use `primary` sparingly. It should act as a beacon, not a background.
*   **Do** prioritize whitespace. If a screen feels "busy," increase the padding using the `xl` spacing scale.

### Don't:
*   **Don't** use pure black (#000000) for text. Always use `on-surface` (#1a1c1d) to maintain a soft, professional tone.
*   **Don't** use standard "drop shadows." If you can see where the shadow starts, it's too heavy.
*   **Don't** stack more than three layers of glass; it creates visual "mud" and kills the airy aesthetic.
*   **Don't** use 1px dividers. If you need separation, use a 4px `surface-container-highest` bar or simple whitespace.