CREATE OR REPLACE FUNCTION ensure_created_at_not_null()
  RETURNS trigger AS
$BODY$
BEGIN
  IF NEW.created_at IS NULL THEN
    NEW.created_at := now();
  END IF;
  RETURN NEW;
END
$BODY$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS password_created_at ON password;
CREATE TRIGGER password_created_at BEFORE INSERT ON password
FOR EACH ROW
EXECUTE PROCEDURE ensure_created_at_not_null();