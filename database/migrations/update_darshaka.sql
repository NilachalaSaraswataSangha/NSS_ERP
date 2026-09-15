-- Update PROBATIONARY display name from "Probationary Member" to "Darshaka"
-- Authority: NSS Bye-Law §B
UPDATE nss.master_data
SET    value_name = 'Darshaka'
WHERE  value_code = 'PROBATIONARY'
  AND  master_category_pk = (
      SELECT master_category_pk
      FROM   nss.master_category
      WHERE  category_code = 'MEMBERSHIP_TYPE'
  );
