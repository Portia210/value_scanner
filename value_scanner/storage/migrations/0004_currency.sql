-- Reporting currency of a downloaded statement ("USD", "TWD", ...), read from the page's
-- "Financials in millions TWD" line (NULL for older rows and until the next download).
-- Additive only (ADD COLUMN): no table is rebuilt, so nothing can cascade (lesson of migration 0002).
ALTER TABLE statement_fetches ADD COLUMN currency TEXT;
