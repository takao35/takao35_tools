<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/config.php';

try {
    $headers = getallheaders();
    if (isset($headers['Authorization'])) {
        $userId = str_replace('Bearer ', '', $headers['Authorization']);
    } else {
        $userId = 'test_user';
    }

    // 入力チェック
    if (!isset($_FILES['photo'])) {
        throw new Exception('No photo uploaded');
    }

    // 位置情報は任意（削除）
    $latitude = isset($_POST['latitude']) ? floatval($_POST['latitude']) : null;
    $longitude = isset($_POST['longitude']) ? floatval($_POST['longitude']) : null;
    $takenAt = $_POST['taken_at'] ?? date('Y-m-d H:i:s');
    
    // タイトル、カテゴリ、説明
    $title = $_POST['title'] ?? null;
    $category = $_POST['category'] ?? null;
    $description = $_POST['description'] ?? null;

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
    $baseDir = dirname(__DIR__) . '/photos/';
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

    // DBに保存
    $relativeFilename = "$year/$month/$day/$filename";
    $stmt = $pdo->prepare(
        "INSERT INTO photos (user_id, filename, title, category, description, latitude, longitude, taken_at) 
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    );
    $stmt->execute([
        $userId, 
        $relativeFilename, 
        $title, 
        $category, 
        $description, 
        $latitude, 
        $longitude, 
        $takenAt
    ]);
    
    $photoId = $pdo->lastInsertId();
    $photoUrl = PHOTO_BASE_URL . $userId . '/' . $relativeFilename;
    
    echo json_encode([
        'success' => true,
        'photo_id' => $photoId,
        'url' => $photoUrl,
        'title' => $title,
        'category' => $category,
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