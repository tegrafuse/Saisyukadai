# ユーザー・技術スタック連携フロー

## ユーザー・技術スタック連携フロー（簡易版）

```mermaid
graph LR
    User["👤 ユーザー<br/>ブラウザ操作"]
    
    Browser["🌐 Webブラウザ<br/>HTML/CSS/JS"]
    
    Flask["🐍 Flask<br/>Webサーバー<br/>ルーティング・ビュー"]
    
    Werkzeug["🔧 Werkzeug<br/>- password hash<br/>- file upload<br/>- secure_filename"]
    
    SQLAlchemy["🔗 SQLAlchemy<br/>ORM・モデル<br/>クエリビルダー"]
    
    SQL["🗃️ SQL<br/>INSERT/SELECT<br/>UPDATE/DELETE"]
    
    SQLite["🗄️ SQLite<br/>データベース<br/>テーブル保存"]
    
    Storage["📁 ファイルシステム<br/>uploads/"]
    
    Response["📤 JSON/HTML<br/>レスポンス"]
    
    User -->|クリック<br/>フォーム送信| Browser
    Browser -->|HTTP<br/>POST/GET| Flask
    
    Flask -->|バリデーション| Werkzeug
    Flask -->|モデル操作| SQLAlchemy
    
    Werkzeug -->|ハッシュ化<br/>ファイル保存| Storage
    
    SQLAlchemy -->|クエリ生成| SQL
    SQL -->|実行| SQLite
    
    SQLite -->|データ返却| SQL
    SQL -->|マッピング| SQLAlchemy
    
    SQLAlchemy -->|オブジェクト| Flask
    Storage -->|ファイルパス| Flask
    
    Flask -->|レンダリング| Response
    Response -->|画面表示| Browser
    Browser -->|ユーザーに表示| User
    
    style User fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style Browser fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    style Flask fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style Werkzeug fill:#ffe0b2,stroke:#e65100,stroke-width:2px
    style SQLAlchemy fill:#f0f4c3,stroke:#827717,stroke-width:2px
    style SQL fill:#ffccbc,stroke:#bf360c,stroke-width:2px
    style SQLite fill:#cfd8dc,stroke:#37474f,stroke-width:2px
    style Storage fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    style Response fill:#fce4ec,stroke:#880e4f,stroke-width:2px
```

---

## 各技術の役割

### 👤 ユーザー
- ブラウザでアプリケーションを操作
- フォーム入力やボタンクリックでアクション実行

### 🌐 Webブラウザ
- HTML/CSS/JavaScriptを実行
- HTTPリクエストをサーバーに送信
- サーバーからのレスポンスを表示

### 🐍 Flask
- HTTPリクエストを受け取りルーティング
- ビュー関数でビジネスロジック実行
- テンプレートをレンダリング

### 🔧 Werkzeug
- **password hash**: ユーザーパスワードの暗号化
- **file upload**: ファイルアップロード処理
- **secure_filename**: セキュアなファイル名生成

### 🔗 SQLAlchemy
- Pythonのモデルオブジェクトとデータベース間のマッピング
- SQL文の自動生成
- データベースクエリの抽象化

### 🗃️ SQL
- INSERT: 新規データ挿入
- SELECT: データ取得
- UPDATE: データ更新
- DELETE: データ削除

### 🗄️ SQLite
- 実際のデータベース
- テーブルにデータを永続保存
- トランザクション管理

### 📁 ファイルシステム
- ユーザーアップロード画像の保存
- instance/uploads/ ディレクトリに格納

### 📤 レスポンス
- JSON: AJAX通信用
- HTML: ページ表示用
- クライアントに返送
