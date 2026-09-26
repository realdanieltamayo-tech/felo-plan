# Handoff — PRJ-12 phase 2: Clients hub (built 2026-09-26, branch clients-hub)

- app/lib/clients.js: /clients list (contacts except category 'test'; per contact: lead count, latest stage/title,
  sum of value_cents, open tasks, linked projects, last activity) + /clients/:id page (contact, leads & deals, projects from
  felo_project_links joined with the felo_workroom summary incl. proposal number + live shares, Gmail threads via
  /api/hq/clients/:id/emails = gmail.list "from:X OR to:X" headers only, felo_email_drafts to them, tasks, notes).
  Read-only; editing stays on /crm. Menu "Clients" -> /clients.
- Table felo_project_links(project PK, contact_id, linked_by, linked_at); Felo tool felo_project_link (Level 1).
  oil-equipment-site -> contact 21 (Lucas Osorio) linked by Claude (table pre-created with the same schema).
- Workroom sync now also reads the proposal number (meta quote-number) -> Dogo: FGC-2026-0926-DGO.
- Skills felo-website-playbook + felo-proposals: link the project to its client when work starts.
- Projects & jobs cards show "Client: <name>".
- Tests: tests/clients.test.cjs; 353 pass.
- Note for Daniel: 4 old test contacts (Codex CRM test, Gpt test, Card One Test, test notificatiion) still show; set their
  category to "test" (Felo can do it) to hide them.
Next PRJ-12 phases: 3 Websites, 4 Automations, 5 Products & Money (+ supervisors), 6 Team, 7 movie look.
