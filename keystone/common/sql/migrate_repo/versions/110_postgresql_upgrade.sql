CREATE OR REPLACE FUNCTION insert_into_user()
  RETURNS trigger AS
$BODY$
BEGIN
  DECLARE found_row INT;
  SELECT COUNT(1) INTO found_row FROM user
  WHERE id = NEW.id;
  IF found_row = 0 THEN
    INSERT IGNORE INTO user (id, enabled, default_project_id) VALUES (new.id, new.enabled, new.default_project_id);
  END IF;
END;
$BODY$

DROP TRIGGER IF EXISTS new_user_to_user ON new_user;
CREATE TRIGGER new_user_to_user AFTER INSERT ON new_user
FOR EACH ROW
EXECUTE PROCEDURE insert_into_user();

CREATE OR REPLACE FUNCTION insert_into_new_user()
  RETURNS trigger AS
$BODY$
BEGIN
  DECLARE found_row INT;
  SELECT COUNT(1) INTO found_row FROM new_user
  WHERE id = NEW.id;
  IF found_row = 0 THEN
    INSERT IGNORE INTO new_user (id, enabled, default_project_id) VALUES (new.id, new.enabled, new.default_project_id);
  END IF;
END;
$BODY$

DROP TRIGGER IF EXISTS user_to_newuser  ON user;
CREATE TRIGGER user_to_newuser AFTER INSERT ON user
FOR EACH ROW
EXECUTE PROCEDURE insert_into_new_user();
