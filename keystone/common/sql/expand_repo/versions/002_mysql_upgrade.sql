DROP TRIGGER IF EXISTS password_created_at;
CREATE TRIGGER password_created_at BEFORE INSERT ON password
FOR EACH ROW
BEGIN
  IF NEW.created_at IS NULL THEN
    SET NEW.created_at = now();
  END IF;
END;
