-- R5: the period end of the latest financial report, as the screener shows it (`lastReportDate`).
-- Additive only (ADD COLUMN): no table is rebuilt, so nothing can cascade (lesson of migration 0002).
ALTER TABLE screener_snapshots ADD COLUMN last_report_date TEXT;
-- The value the screener showed at the moment a statement was downloaded (NULL for older rows).
ALTER TABLE statement_fetches ADD COLUMN report_date TEXT
