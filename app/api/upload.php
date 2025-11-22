<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// OPTIONSリクエスト対応
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/config.php';

try {
    // Firebase認証トークンの検証（一旦スキップ、後で実装）
    // 本番ではFirebase Admin SDKで検証が必要
    
    // テスト用: Authorization headerからuser_idを取得
    $headers = getallheaders();
    if (isset($headers['Authorization'])) {
        // "Bearer user_id" 形式を想定
        $userId = str_replace('Bearer ', '', $headers['Authorization']);
    } else {
        // テスト用: デフォルトユーザー
        $userId = 'test_user';
    }

    // 入力チェック
    if (!isset($_FILES['photo'])) {
        throw new Exception('No photo uploaded');
    }

    if (!isset($_POST['latitude']) || !isset($_POST['longitude'])) {
        throw new Exception('Location data required');
    }

    $latitude = floatval($_POST['latitude']);
    $longitude = floatval($_POST['longitude']);
    $takenAt = $_POST['taken_at'] ?? date('Y-m-d H:i:s');

    // ファイルタイプチェック
    $allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    $fileType = $_FILES['photo']['type'];
    
    if (!in_array($fileType, $allowedTypes)) {
        throw new Exception('Invalid file type. Only JPG and PNG allowed.');
    }

    // ファイルサイズチェック (10MB)
    if ($_FILES['photo']['size'] > 10 * 1024 * 1024) {
        throw new Exception('File too large. Maximum 10MB.');
    }

    // 日付からパス生成
    $date = new DateTime($takenAt);
    $year = $date->format('Y');
    $month = $date->format('m');
    $day = $date->format('d');

    // ディレクトリ作成
    $baseDir = dirname(__DIR__) . '/photos/';  // /app/photos/
    $photoDir = $baseDir . $userId . '/' . $year . '/' . $month . '/' . $day . '/';
    
    if (!is_dir($photoDir)) {
        mkdir($photoDir, 0755, true);
    }

    // ファイル名生成
    $extension = pathinfo($_FILES['photo']['name'], PATHINFO_EXTENSION);
    $filename = uniqid() . '.' . strtolower($extension);
    $filepath = $photoDir . $filename;

    // ファイル保存
    if (!move_uploaded_file($_FILES['photo']['tmp_name'], $filepath)) {
        throw new Exception('Failed to save photo');
    }

    // データベース接続
    $pdo = new PDO(
        "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
        DB_USER,
        DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );

    // DBに保存（相対パス）
    $relativeFilename = "$year/$month/$day/$filename";
    $stmt = $pdo->prepare(
        "INSERT INTO photos (user_id, filename, latitude, longitude, taken_at) 
         VALUES (?, ?, ?, ?, ?)"
    );
    $stmt->execute([$userId, $relativeFilename, $latitude, $longitude, $takenAt]);
    
    $photoId = $pdo->lastInsertId();

    // URL返却
    $photoUrl = PHOTO_BASE_URL . $userId . '/' . $relativeFilename;
    
    echo json_encode([
        'success' => true,
        'photo_id' => $photoId,
        'url' => $photoUrl,
        'message' => 'Photo uploaded successfully'
    ], JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>