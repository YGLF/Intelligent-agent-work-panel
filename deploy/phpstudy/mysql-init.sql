-- phpStudy MySQL 初始化模板。
-- 请先把 change-me-strong-password 替换为本机专用强密码，再执行。
-- 不要把真实密码提交到代码仓库。

CREATE DATABASE IF NOT EXISTS `codex_agent_panel`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 为兼容 phpStudy 常见连接方式，同时创建 localhost 和 127.0.0.1 两个账号。
CREATE USER 'codex_panel_app'@'localhost'
  IDENTIFIED BY 'change-me-strong-password';
CREATE USER 'codex_panel_app'@'127.0.0.1'
  IDENTIFIED BY 'change-me-strong-password';

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP
  ON `codex_agent_panel`.*
  TO 'codex_panel_app'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP
  ON `codex_agent_panel`.*
  TO 'codex_panel_app'@'127.0.0.1';

FLUSH PRIVILEGES;
