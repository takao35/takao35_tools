<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/../config/firebase.php';
require_once __DIR__ . '/../auth/firebase_auth.php';

try {
    // Firebase<
    $auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    $user_info = verify_firebase_token($auth_header);

    if (!$user_info) {
        http_response_code(401);
        echo json_encode([
            'success' => false,
            'error' => 'Unauthorized'
        ], JSON_UNESCAPED_UNICODE);
        exit;
    }

    $firebase_uid = $user_info['uid'];
    $email = $user_info['email'];

    // POSTÇü¿Ö—
    $input = json_decode(file_get_contents('php://input'), true);

    $display_name = $input['display_name'] ?? 'No Name';
    $folder_name = $input['folder_name'] ?? null;

    // Çü¿Ùü¹¥š
    $pdo = get_db_connection();

    // âXæü¶üÁ§Ã¯
    $stmt = $pdo->prepare("SELECT id FROM users WHERE firebase_uid = ?");
    $stmt->execute([$firebase_uid]);
    $existing_user = $stmt->fetch();

    if ($existing_user) {
        // âXæü¶ünô°
        $stmt = $pdo->prepare("
            UPDATE users
            SET display_name = ?,
                folder_name = ?
            WHERE firebase_uid = ?
        ");
        $stmt->execute([$display_name, $folder_name, $firebase_uid]);

        echo json_encode([
            'success' => true,
            'user_id' => $existing_user['id'],
            'firebase_uid' => $firebase_uid,
            'message' => 'User updated successfully'
        ], JSON_UNESCAPED_UNICODE);

    } else {
        // °æü¶ü{2
        $stmt = $pdo->prepare("
            INSERT INTO users (firebase_uid, display_name, folder_name)
            VALUES (?, ?, ?)
        ");
        $stmt->execute([$firebase_uid, $display_name, $folder_name]);

        $user_id = $pdo->lastInsertId();

        echo json_encode([
            'success' => true,
            'user_id' => $user_id,
            'firebase_uid' => $firebase_uid,
            'message' => 'User registered successfully'
        ], JSON_UNESCAPED_UNICODE);
    }

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>
