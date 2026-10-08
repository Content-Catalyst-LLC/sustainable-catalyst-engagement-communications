# Source inventory and compatibility boundary

Source A: `sustainable-catalyst-product-support-feedback-main` at v7.8.1. `backend/app/main.py` exposes `FastAPI` and imports help desk case, email channels, service levels, customer portal, survey and release intelligence modules. Remains deployed independently.

Source B: `sustainable-catalyst-engagement-intake-main` at v2.0.2. `docs/ARCHITECTURE.md` documents private `wp_sc_ei_inquiries`, `wp_sc_ei_attachments`, `wp_sc_ei_audit_log`, dedicated capabilities, protected file quarantine and a separate public consulting/contact presentation. Remains deployed independently.

Do not assume similarly named fields are identical or combine contacts by email. Do not replace old shortcode routes. Next release will define canonical mapping and migration reconciliation after a database inventory. This artifact does NOT include or distribute either legacy codebase.
