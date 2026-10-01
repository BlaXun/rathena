-- Hashed account passwords (src/login/password.hpp): room for a PBKDF2 hash,
-- and the flags that record what the plain text was like before it was gone.
-- The login server also applies this itself at start-up.
ALTER TABLE `login` MODIFY `user_pass` varchar(128) NOT NULL default '';
ALTER TABLE `login` ADD COLUMN `pass_flags` tinyint(3) unsigned NOT NULL default '0' AFTER `user_pass`;
