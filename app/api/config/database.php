<?php
// config/database.php
$configPath = __DIR__ . '/config.php';
if (!file_exists($configPath)) {
    throw new RuntimeException('config.php が見つかりません。config.php.sample をコピーして作成してください。');
}
require_once $configPath;

/**
 * コアサーバー用の PDO 接続を返す（シングルトン）
 */
function get_db_connection() {
    static $pdo = null;
    if ($pdo === null) {
        try {
            $pdo = new PDO(
                "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
                DB_USER,
                DB_PASS,
                [
                    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                    PDO::ATTR_EMULATE_PREPARES => false,
                ]
            );
        } catch (PDOException $e) {
            error_log('DB Connection Error: ' . $e->getMessage());
            throw $e;
        }
    }

    return $pdo;
}
