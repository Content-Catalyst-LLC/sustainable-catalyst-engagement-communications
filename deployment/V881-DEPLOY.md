# v8.8.1 WordPress deployment

1. WordPress Dashboard → Plugins → Add New → Upload Plugin. Select `sustainable-catalyst-engagement-communications-wordpress-v8.8.1.zip`.
2. Choose Replace current with uploaded when prompted. Activate plugin if necessary.
3. Refresh the existing private Engagement test page containing `[sc_engagement_communications]`. Confirm links only to published existing pages.
4. Verify existing Contact, Feedback, Channel and Support pages and their forms still load unchanged.
5. If links are missing, check published page slugs; this release matches contact/contact-us, feedback, channel and support. It does not create or alter pages.
6. No PostgreSQL migration, VPS service restart, or backend deployment is needed for this plugin-only patch.

Full repo: unzip the release in Downloads and rsync into your project excluding .git/.venv/__pycache__, check git diff, stage and push. Do not overwrite uncommitted local changes.
