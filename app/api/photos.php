<?php
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// OPTIONSリクエスト対応（CORS preflight）
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/config.php';

try {
    // データベース接続
    $pdo = new PDO(
        "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
        DB_USER,
        DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );

    // パラメータ取得
    $latitude = isset($_GET['lat']) ? floatval($_GET['lat']) : null;
    $longitude = isset($_GET['lng']) ? floatval($_GET['lng']) : null;
    $radius = isset($_GET['radius']) ? floatval($_GET['radius']) : 10; // デフォルト10km
    $userId = isset($_GET['user_id']) ? $_GET['user_id'] : null;
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 100;

    // SQL構築
    if ($latitude && $longitude) {
        // 位置情報による範囲検索（簡易版：緯度経度の差分で計算）
        // 1度 ≈ 111km として計算
        $latDiff = $radius / 111.0;
        $lngDiff = $radius / (111.0 * cos(deg2rad($latitude)));
        
        $sql = "SELECT 
                    id,
                    user_id,
                    filename,
                    latitude,
                    longitude,
                    taken_at,
                    uploaded_at
                FROM photos
                WHERE latitude BETWEEN :lat_min AND :lat_max
                  AND longitude BETWEEN :lng_min AND :lng_max";
        
        $params = [
            ':lat_min' => $latitude - $latDiff,
            ':lat_max' => $latitude + $latDiff,
            ':lng_min' => $longitude - $lngDiff,
            ':lng_max' => $longitude + $lngDiff
        ];
    } else {
        // 全写真取得（最新順）
        $sql = "SELECT 
                    id,
                    user_id,
                    filename,
                    latitude,
                    longitude,
                    taken_at,
                    uploaded_at
                FROM photos
                WHERE 1=1";
        
        $params = [];
    }

    // ユーザー指定がある場合
    if ($userId) {
        $sql .= " AND user_id = :user_id";
        $params[':user_id'] = $userId;
    }

    // 並び順と件数制限
    $sql .= " ORDER BY taken_at DESC LIMIT :limit";
    
    $stmt = $pdo->prepare($sql);
    
    // パラメータバインド
    foreach ($params as $key => $value) {
        $stmt->bindValue($key, $value);
    }
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    
    $stmt->execute();
    $photos = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // URLを付与
    foreach ($photos as &$photo) {
        $photo['url'] = PHOTO_BASE_URL . $photo['user_id'] . '/' . $photo['filename'];
    }

    echo json_encode([
        'success' => true,
        'count' => count($photos),
        'photos' => $photos
    ], JSON_UNESCAPED_UNICODE);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Database error: ' . $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ], JSON_UNESCAPED_UNICODE);
}
?>