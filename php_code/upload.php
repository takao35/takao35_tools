<?php
$userId = $verifiedToken->claims()->get('sub');
$takenAt = $_POST['taken_at'] ?? date('Y-m-d H:i:s');

// 日付からパス生成
$date = new DateTime($takenAt);
$year = $date->format('Y');
$month = $date->format('m');
$day = $date->format('d');

// ディレクトリ作成
$photoDir = "/home/account/public_html/app/photos/$userId/$year/$month/$day/";
if (!is_dir($photoDir)) {
    mkdir($photoDir, 0755, true);
}

// ファイル名生成
$filename = uniqid() . '.jpg';
$filepath = $photoDir . $filename;

// ファイル保存
move_uploaded_file($_FILES['photo']['tmp_name'], $filepath);

// DBに保存（相対パス）
$relativeFilename = "$year/$month/$day/$filename";
$stmt = $pdo->prepare("INSERT INTO photos (user_id, filename, latitude, longitude, taken_at) VALUES (?, ?, ?, ?, ?)");
$stmt->execute([$userId, $relativeFilename, $lat, $lng, $takenAt]);

// URL返却
$photoUrl = "https://takaosan-go.jp/app/photos/$userId/$relativeFilename";
echo json_encode(['url' => $photoUrl]);
?>