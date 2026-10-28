-- Fabric Warehouse | role-based access: readers see gold, never the security schema

CREATE ROLE gold_reader;
GRANT SELECT ON SCHEMA::gold TO gold_reader;
GO

-- ALTER ROLE gold_reader ADD MEMBER [analyst@costaazul.example];
