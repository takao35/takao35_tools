<?php
// api/auth/is_admin.php
header('Content-Type: application/json');

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/firebase.php';
require_once __DIR__ . '/../auth/firebase_auth.php';

// Firebase認証
$auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
$user_info = verify_firebase_token($auth_header);

if (!$user_info) {
    http_response_code(401);
    echo json_encode(['is_admin' => false, 'error' => 'Unauthorized']);
    exit;
}

// 管理者権限チェック
$pdo = get_db_connection();
$is_admin = check_admin_permission($pdo, $user_info['uid']);

echo json_encode([
    'is_admin' => $is_admin,
    'uid' => $user_info['uid'],
    'email' => $user_info['email']
]);
?>
