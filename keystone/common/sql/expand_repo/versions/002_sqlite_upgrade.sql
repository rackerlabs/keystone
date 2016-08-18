DROP TRIGGER IF EXISTS password_created_at;
CREATE TRIGGER password_created_at AFTER INSERT ON password
FOR EACH ROW
WHEN (NEW.created_at IS NULL)
BEGIN
  UPDATE password SET created_at = DATETIME('now') WHERE id = NEW.id;
END;
