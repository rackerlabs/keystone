DROP TRIGGER IF EXISTS new_user_to_user;
CREATE TRIGGER new_user_to_user AFTER INSERT ON new_user
FOR EACH ROW
BEGIN
  INSERT IGNORE INTO user (id, enabled, default_project_id) VALUES (new.id, new.enabled, new.default_project_id);
END;

DROP TRIGGER IF EXISTS user_to_newuser;
CREATE TRIGGER user_to_newuser AFTER INSERT ON user
FOR EACH ROW
BEGIN
  INSERT IGNORE INTO new_user (id, enabled, default_project_id) VALUES (new.id, new.enabled, new.default_project_id);
END;
