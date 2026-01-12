<?php
// auth/firebase_auth.php

function verify_firebase_token($auth_header) {
    if (empty($auth_header)) {
        return false;
    }
    
    $token = str_replace('Bearer ', '', $auth_header);
    
    // Firebase REST APIでトークン検証
    $url = "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=" . FIREBASE_API_KEY;
    
    $postData = json_encode(['idToken' => $token]);
    
    // cURLを使用（file_get_contentsより確実）
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Content-Length: ' . strlen($postData)
    ]);
    
    $response = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($httpCode !== 200 || !$response) {
        return false;
    }
    
    $result = json_decode($response, true);
    
    if (isset($result['users'][0])) {
        $user = $result['users'][0];
        return [
            'uid' => $user['localId'],
            'email' => $user['email'] ?? null,
            'email_verified' => $user['emailVerified'] ?? false
        ];
    }
    
    return false;
}

function check_admin_permission($pdo, $firebase_uid) {
    $stmt = $pdo->prepare("
        SELECT firebase_uid
        FROM admin_users
        WHERE is_admin is True and firebase_uid = :uid
    ");
    $stmt->execute([':uid' => $firebase_uid]);

    return $stmt->fetch() !== false;
}
?>