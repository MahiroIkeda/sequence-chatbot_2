# 仕様書

> 最終更新: 2026-05-12 23:43
> 生成ツール: SpecFlow（仕様駆動開発アシスタント）

---

# 要件定義書：図書館蔵書管理システム（改訂版 v1.1）

## Why（なぜ作るか）

### 現状の課題

現在、A市立図書館の貸出・返却管理は紙台帳で行っており、以下の課題が発生している：

1. **業務効率の低下**：
   - 蔋出処理に平均5分、在庫確認に平均3分を要している
   - 月間約3,000件の貸出に対し、司書の作業時間が400時間（約50人日）

2. **利用者の利便性低下**：
   - 在庫状況の確認に窓口での問い合わせが必要
   - 予約機能がないため、人気書籍の借り逃しが発生

3. **データの不正確性**：
   - 台帳の記入漏れにより、年間約50冊（蔵書の約0.5%）の所在不明が発生
   - 延滞図書の追跡が困難で、督促が不十分

### 期待される効果

システム化により以下の効果を期待する：

1. **業務効率化**：貸出処理時間を60%削減（5分→2分）、司書の作業時間を月間240時間に削減
2. **利用者満足度向上**：オンライン検索・予約機能により、利便性を向上
3. **蔵書管理の精度向上**：所在不明図書を年間10冊以下（0.1%以下）に削減

### 成功指標（KPI）

- 貸出処理時間：平均2分以内
- システム稼働率：99.5%以上
- 利用者満足度：アンケートで80%以上が「満足」と回答
- 所在不明図書：年間10冊以下

---

## What（何をするか）

### 0. 基本定義

#### 0.1 データ型定義

- **UserId**: 正の整数（1以上）。利用者を一意に識別する。
- **BookId**: 正の整数（1以上）。蔵書を一意に識別する。
- **LoanId**: 正の整数（1以上）。貸出レコードを一意に識別する。
- **ReservationId**: 正の整数（1以上）。予約レコードを一意に識別する。
- **Email**: 文字列。RFC 5322に準拠したメールアドレス形式。
- **ISBN**: 文字列。ISBN-10またはISBN-13形式（ハイフンあり・なし両方を許容）。
- **DateTime**: ISO 8601形式のタイムスタンプ（UTC）。例：`2024-01-15T10:30:00Z`
- **Date**: ISO 8601形式の日付。例：`2024-01-15`
- **PhoneNumber**: 文字列。10〜11桁の数字（ハイフンなし）。

#### 0.2 タイムゾーン戦略

- **内部処理**：すべての日時はUTCで保存・処理する
- **利用者向け表示**：JST（UTC+9）に変換して表示する
- **日付境界の定義**：
  - 「当日」「翌日」等の判定は、JSTの日付で行う
  - 例：UTC 2024-01-15 15:00:00（JST 2024-01-16 00:00:00）は、JST基準で2024-01-16とみなす

#### 0.3 書籍状態の定義

書籍は以下の3つの状態のいずれかを取る：

1. **AVAILABLE（貸出可能）**：図書館に在庫があり、貸出可能な状態
2. **BORROWED（貸出中）**：利用者が借りており、返却されていない状態
3. **RESERVED_AWAITING_PICKUP（予約者受取待ち）**：返却済みで、予約者に通知済み、かつ予約者がまだ受け取りに来ていない状態

#### 0.4 状態遷移規則

```
AVAILABLE → [貸出操作] → BORROWED
BORROWED → [返却操作：予約なし] → AVAILABLE
BORROWED → [返却操作：予約あり] → RESERVED_AWAITING_PICKUP
RESERVED_AWAITING_PICKUP → [予約者による貸出] → BORROWED
RESERVED_AWAITING_PICKUP → [予約期限切れ（自動処理）] → AVAILABLE
RESERVED_AWAITING_PICKUP → [予約キャンセル] → AVAILABLE
```

#### 0.5 システム定数

| 定数名 | 値 | 説明 |
|--------|-----|------|
| `MAX_CONCURRENT_LOANS` | 3 | 同時に借りられる最大冊数 |
| `LOAN_PERIOD_DAYS` | 14 | 貸出期間（日数） |
| `RESERVATION_PICKUP_PERIOD_DAYS` | 3 | 予約取置き期間（日数） |
| `OVERDUE_ALERT_THRESHOLD_DAYS` | 7 | 延滞アラート送信の閾値（返却期限後の日数） |
| `ALERT_CHECK_INTERVAL_HOURS` | 24 | 延滞アラート確認の間隔（時間） |
| `MAX_ACTIVE_RESERVATIONS_PER_USER` | 5 | 利用者あたりの同時予約可能冊数 |

#### 0.6 補助関数の定義

##### 0.6.1 日時・日付操作

```
// 日時から日付部分を抽出（JSTベース）
toJSTDate(dt: DateTime) : Date =
  date(dt + 9 hours)

// 日付の終了時刻を取得（JSTの23:59:59をUTCに変換）
endOfDayUTC(d: Date) : DateTime =
  d + "T23:59:59+09:00" を UTC に変換

// 現在の日時（UTC）
currentDateTime() : DateTime

// 現在の日付（JST）
currentJSTDate() : Date =
  toJSTDate(currentDateTime())
```

##### 0.6.2 ISBN正規化

```
normalizeISBN(isbn: String) : String =
  isbn.replace("-", "").replace(" ", "").toUpperCase()
```

#### 0.7 データモデル（エンティティ定義）

##### 0.7.1 Users（利用者）

| フィールド名 | 型 | 制約 | 説明 |
|-------------|-----|------|------|
| userId | UserId | PRIMARY KEY | 利用者ID |
| email | Email | UNIQUE, NOT NULL | メールアドレス |
| name | String(100) | NOT NULL | 氏名 |
| phoneNumber | PhoneNumber | NOT NULL | 電話番号 |
| registrationDate | DateTime | NOT NULL | 登録日時（UTC） |
| isActive | Boolean | NOT NULL, DEFAULT TRUE | アカウント有効フラグ |

##### 0.7.2 Books（蔵書）

| フィールド名 | 型 | 制約 | 説明 |
|-------------|-----|------|------|
| bookId | BookId | PRIMARY KEY | 書籍ID |
| isbn | ISBN | NOT NULL | ISBN |
| title | String(500) | NOT NULL | タイトル |
| author | String(200) | NOT NULL | 著者名 |
| publisher | String(200) | NULL | 出版社 |
| publicationYear | Integer | NULL | 出版年 |
| addedDate | DateTime | NOT NULL | 登録日時（UTC） |

**インデックス**：
- `idx_books_isbn` on `normalizeISBN(isbn)`
- `idx_books_title` on `LOWER(title)`
- `idx_books_author` on `LOWER(author)`

##### 0.7.3 Loans（貸出）

| フィールド名 | 型 | 制約 | 説明 |
|-------------|-----|------|------|
| loanId | LoanId | PRIMARY KEY | 貸出ID |
| bookId | BookId | FOREIGN KEY (Books), NOT NULL | 書籍ID |
| userId | UserId | FOREIGN KEY (Users), NOT NULL | 利用者ID |
| borrowedAt | DateTime | NOT NULL | 貸出日時（UTC） |
| dueDate | Date | NOT NULL | 返却期限（JST日付） |
| returnedAt | DateTime | NULL | 返却日時（UTC、未返却の場合NULL） |
| version | Integer | NOT NULL, DEFAULT 1 | 楽観的ロック用バージョン |

**インデックス**：
- `idx_loans_user_active` on `(userId, returnedAt)` WHERE `returnedAt IS NULL`
- `idx_loans_book_active` on `(bookId, returnedAt)` WHERE `returnedAt IS NULL`
- `idx_loans_overdue` on `(dueDate, returnedAt)` WHERE `returnedAt IS NULL`

##### 0.7.4 Reservations（予約）

| フィールド名 | 型 | 制約 | 説明 |
|-------------|-----|------|------|
| reservationId | ReservationId | PRIMARY KEY | 予約ID |
| bookId | BookId | FOREIGN KEY (Books), NOT NULL | 書籍ID |
| userId | UserId | FOREIGN KEY (Users), NOT NULL | 利用者ID |
| reservedAt | DateTime | NOT NULL | 予約日時（UTC） |
| status | Enum | NOT NULL | 予約状態（ACTIVE, FULFILLED, CANCELLED, EXPIRED） |
| notificationSentAt | DateTime | NULL | 通知送信日時（UTC） |
| expiryDate | Date | NULL | 取置き期限（JST日付、通知送信時に設定） |
| cancelledAt | DateTime | NULL | キャンセル日時（UTC） |
| priority | Integer | NOT NULL | 予約優先順位（予約日時の昇順で自動採番） |

**インデックス**：
- `idx_reservations_book_active` on `(bookId, status, priority)` WHERE `status = 'ACTIVE'`
- `idx_reservations_user_active` on `(userId, status)` WHERE `status = 'ACTIVE'`
- `idx_reservations_awaiting_pickup` on `(status, expiryDate)` WHERE `status = 'ACTIVE' AND notificationSentAt IS NOT NULL`

**制約**：
- `UNIQUE(bookId, userId, status)` WHERE `status = 'ACTIVE'`（同一利用者が同じ本に複数のアクティブな予約を持てない）

##### 0.7.5 NotificationLog（通知ログ）

| フィールド名 | 型 | 制約 | 説明 |
|-------------|-----|------|------|
| notificationId | Integer | PRIMARY KEY | 通知ID |
| userId | UserId | FOREIGN KEY (Users), NOT NULL | 通知先利用者ID |
| notificationType | Enum | NOT NULL | 通知種別（RESERVATION_READY, OVERDUE_ALERT） |
| relatedId | Integer | NULL | 関連ID（reservationId または loanId） |
| sentAt | DateTime | NOT NULL | 送信日時（UTC） |
| status | Enum | NOT NULL | 送信状態（SUCCESS, FAILED, PENDING） |
| emailAddress | Email | NOT NULL | 送信先メールアドレス |
| retryCount | Integer | NOT NULL, DEFAULT 0 | 再送回数 |

---

### 1. 利用者登録

#### 1.1 機能概要

利用者は氏名・メールアドレス・電話番号を入力して会員登録を行う。
登録が完了すると、利用者ID（UserId）が自動発行され、登録完了メールが送信される。

#### 1.2 入力項目

| 項目名 | 必須 | 制約 | 備考 |
|--------|------|------|------|
| 氏名 | 必須 | 1文字以上100文字以内 | 全角・半角を許容 |
| メールアドレス | 必須 | RFC 5322準拠 | 重複不可 |
| 電話番号 | 必須 | 10〜11桁の数字 | ハイフンなし |

#### 1.3 入力値検証

**形式的定義**：
```
validateUserInput(input: UserInput) : ValidationResult =
  LET errors = []
  IN
    IF input.name.length < 1 OR input.name.length > 100 THEN
      errors.append("NAME_INVALID_LENGTH")
    IF NOT isValidEmail(input.email) THEN
      errors.append("EMAIL_INVALID_FORMAT")
    IF NOT matches(input.phone, "^[0-9]{10,11}$") THEN
      errors.append("PHONE_INVALID_FORMAT")
    
    IF errors.isEmpty THEN
      SUCCESS
    ELSE
      FAILURE(errors)
```

#### 1.4 重複登録の制約

**形式的定義**：
```
事前条件：
  ∀ u ∈ Users WHERE u.isActive = TRUE : u.email ≠ input.email
```

**自然言語での説明**：
アクティブな利用者の中に、入力されたメールアドレスと一致するものが存在しないこと。

**重複時の挙動**：
既に同じメールアドレスで登録されているアクティブな利用者が存在する場合：

```
HTTP Status: 409 Conflict
{
  "errorCode": "DUPLICATE_EMAIL",
  "message": "このメールアドレスは既に登録されています。",
  "existingUserId": 123,
  "suggestedAction": "LOGIN"
}
```

- 新規登録は行わない
- 既存の利用者IDを返し、ログイン画面への誘導を促す

**非アクティブなアカウントの扱い**：
過去に登録したが現在非アクティブ（`isActive = FALSE`）なアカウントが存在する場合：
- 再アクティブ化の選択肢を提示する
- 利用者の同意があれば、既存アカウントを再アクティブ化（新規IDは発行しない）

#### 1.5 登録成功時の処理

**形式的定義**：
```
事後条件：
  ∃ newUser ∈ Users : 
    newUser.userId = generateNewUserId()
    ∧ newUser.email = input.email
    ∧ newUser.name = input.name
    ∧ newUser.phoneNumber = normalizePhoneNumber(input.phone)
    ∧ newUser.registrationDate = currentDateTime()
    ∧ newUser.isActive = TRUE

generateNewUserId() : UserId =
  (MAX({u.userId | u ∈ Users}) OR 0) + 1
```

**自然言語での説明**：
1. 新しい利用者IDは、既存の最大利用者IDに1を加えた値とする（既存データがない場合は1）
2. 電話番号はハイフンを除去して正規化する
3. 登録日時はシステムの現在日時（UTC）を記録する
4. アカウントは有効（isActive = TRUE）な状態で作成する

**成功時のレスポンス**：
```
HTTP Status: 201 Created
{
  "userId": 123,
  "message": "登録が完了しました。登録確認メールを送信しました。",
  "email": "user@example.com"
}
```

**登録完了メールの送信**：
- 件名：「【図書館システム】会員登録が完了しました」
- 内容：利用者ID、ログインURL、利用開始の案内
- 送信失敗時はリトライ（最大3回、指数バックオフ：1分、2分、4分）
- 3回失敗後は管理者にアラートを送信し、手動での対応を依頼

#### 1.6 同時実行制御

**楽観的ロック（推奨）**：
- メールアドレスのUNIQUE制約により、データベースレベルで重複を防止
- 同時登録があった場合、後勝ちがDUPLICATE_KEYエラーとなり、1.4の重複エラーとして処理

**トランザクション境界**：
```
BEGIN TRANSACTION
  1. 入力値検証
  2. 重複チェック（SELECT ... FOR UPDATE をかけない、UNIQUE制約に依存）
  3. ユーザーレコード挿入
  4. 通知ログレコード挿入（status = PENDING）
COMMIT

// トランザクション成功後、非同期でメール送信
ASYNC: sendRegistrationEmail(userId)
```

---

### 2. 蔵書検索

#### 2.1 機能概要

利用者および司書は、タイトル・著者名・ISBNのいずれかまたは組み合わせで蔵書を検索できる。
検索結果には在庫状況と、貸出中または予約待ちの場合の予定日が表示される。

#### 2.2 検索条件

| 検索項目 | 検索方法 | 詳細 |
|---------|---------|------|
| タイトル | 部分一致 | 大文字小文字を区別しない、前方一致・中間一致を許容 |
| 著者名 | 部分一致 | 大文字小文字を区別しない、前方一致・中間一致を許容 |
| ISBN | 完全一致 | ハイフンの有無を許容（内部で正規化して比較） |

**複数条件の扱い**：
- 複数の検索条件が指定された場合、AND条件で絞り込む
- 検索条件が一つも指定されていない場合はエラー（全件取得を防ぐ）

**形式的定義**：
```
searchBooks(criteria: SearchCriteria) : Set<Book> =
  LET results = Books
  IN
    IF criteria.title IS NOT NULL THEN
      results = {b ∈ results | LOWER(b.title) LIKE '%' + LOWER(criteria.title) + '%'}
    IF criteria.author IS NOT NULL THEN
      results = {b ∈ results | LOWER(b.author) LIKE '%' + LOWER(criteria.author) + '%'}
    IF criteria.isbn IS NOT NULL THEN
      results = {b ∈ results | normalizeISBN(b.isbn) = normalizeISBN(criteria.isbn)}
    
    IF criteria is empty THEN
      ERROR("SEARCH_CRITERIA_REQUIRED")
    ELSE
      results
```

#### 2.3 検索結果の表示項目

各蔵書について以下の情報を表示：

| 項目名 | 説明 |
|--------|------|
| 書籍ID | BookId |
| タイトル | Books.title |
| 著者名 | Books.author |
| ISBN | Books.isbn（ハイフンを含む元の形式） |
| 出版社 | Books.publisher |
| 出版年 | Books.publicationYear |
| **在庫状況** | 計算値（2.4節参照） |
| 返却予定日 | BORROWED状態の場合のみ表示（Loans.dueDate） |
| 予約取置き期限 | RESERVED_AWAITING_PICKUP
