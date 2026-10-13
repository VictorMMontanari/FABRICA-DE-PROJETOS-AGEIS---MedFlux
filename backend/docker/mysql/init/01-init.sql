-- Executado uma única vez pelo container do MySQL, quando o volume mysql_data é criado.
--
-- Banco, usuário e permissões:
--   * O banco abaixo é criado (ou ajustado) com utf8mb4, necessário para acentos e emojis.
--   * O usuário da aplicação é criado pelo entrypoint oficial do MySQL a partir de
--     MYSQL_USER / MYSQL_PASSWORD (.env), recebendo ALL PRIVILEGES apenas em MYSQL_DATABASE.
--     Assim nenhuma senha fica versionada neste arquivo.
--   * Para recriar do zero: docker compose down -v (apaga os dados).

CREATE DATABASE IF NOT EXISTS `medflux`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

ALTER DATABASE `medflux`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
