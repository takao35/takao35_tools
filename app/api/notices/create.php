<?php
// api/notices/create.php
require_once '../config/database.php';
require_once '../auth/firebase_auth.php';

// Firebase認証
$uid = verify_firebase_token($_SERVER['HTTP_AUTHORIZATION'] ?? '');
if (!$uid) {
    http_response_code(401);
    echo json_encode(['error' => 'Unauthorized']);
    exit;
}

// 権限確認
$pdo = get_db_connection();
if (!check_permission($pdo, $uid, 'notices', 'create')) {
    http_response_code(403);
    echo json_encode(['error' => 'Forbidden: Admin access required']);
    exit;
}

// 以降、noticesのINSERT処理
// ...
?>