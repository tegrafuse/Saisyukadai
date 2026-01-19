# グループC
メンバー 原匠生 2442067 , 渡辺海斗 2442099<br>
使い方 :<br>
1. 任意のディレクトリにて`git clone https://github.com/tegrafuse/Saisyukadai.git`<br>
2. 構築を構築する。Windowsの場合は`./setupproject.bat`<br>
Windows以外の場合は`python -m venv venv`, `source venv/bin/activate`, `pip install -r requirements.txt`<br>
3. `python run.py`　※Windowsの場合は`./start.bat`<br>
4. ブラウザにて[http://127.0.0.1:5000](http://127.0.0.1:5000)<br>

---

## デモ動画

https://github.com/user-attachments/assets/demomovie.mp4

---

## アーキテクチャ

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

## システムダイアグラム

### 全体構造

```mermaid
graph LR;
    Root["📁 Finalkadai<br/>(Flask SNS Project)"]
    
    %% Core Python files
    Root --> run_py["📄 run.py<br/>(エントリーポイント)"];
    Root --> models_py["📄 models.py<br/>(DBモデル)"];
    Root --> req_txt["📄 requirements.txt"];
    
    %% App package
    Root --> AppPkg["📁 app/<br/>(Application Logic)"];
    AppPkg --> app_init["📄 __init__.py<br/>(Factory + DB Setup)"];
    AppPkg --> app_routes["📄 routes.py<br/>(全ルーティング)"];
    
    %% Templates
    Root --> TempDir["📁 templates/"];
    TempDir --> base["📄 base.html"];
    TempDir --> index["📄 index.html<br/>(ホーム/フィード)"];
    TempDir --> community["📄 community.html"];
    TempDir --> view_post["📄 view_post.html"];
    TempDir --> messages["📄 messages.html"];
    TempDir --> user["📄 user.html"];
    TempDir --> settings["📄 settings.html"];
    TempDir --> auth["📄 login.html<br/>register.html"];
    
    %% Static assets
    Root --> Static["📁 static/"];
    Static --> CSS["📁 css/"];
    Static --> JS["📁 js/"];
    Static --> Resources["📁 resources/"];
    CSS --> styles["📄 styles.css"];
    JS --> like["📄 like_handler.js"];
    JS --> carousel["📄 image_carousel.js"];
    JS --> preview["📄 post_preview.js"];
    JS --> realtime["📄 realtime_messages.js"];
    JS --> reply["📄 reply_toggle.js"];
    Resources --> icons["📁 community_icons/"];
    
    %% Instance (runtime data)
    Root --> InstDir["📁 instance/"];
    InstDir --> db["🗄️ sns.db<br/>(SQLite DB)"];
    InstDir --> uploads["📁 uploads/<br/>(ユーザー画像等)"];

    style Root fill:#6366f1,stroke:#333,stroke-width:3px,color:#fff
    style AppPkg fill:#3b82f6,stroke:#333,stroke-width:2px,color:#fff
    style TempDir fill:#10b981,stroke:#333,stroke-width:2px,color:#fff
    style Static fill:#f59e0b,stroke:#333,stroke-width:2px,color:#fff
    style InstDir fill:#ef4444,stroke:#333,stroke-width:2px,color:#fff
    style Docs fill:#8b5cf6,stroke:#333,stroke-width:2px,color:#fff
```

### ファイルアップロード構成

```mermaid
graph LR;
    Uploads["📁 instance/uploads/"]
    
    Avatars["📁 avatars/<br/>ユーザープロフィール画像"]
    Communities["📁 community_icons/<br/>コミュニティアイコン"]
    Posts["📁 posts/<br/>投稿の画像・動画"]
    Replies["📁 replies/<br/>返信の画像・動画"]
    
    AvatarEx["📷 {uuid}_{name}<br/>avatar.jpg"]
    CommunityEx["🏷️ {uuid}_{name}<br/>icon.png"]
    PostEx["🖼️ {uuid}_{name}<br/>photo.jpg"]
    VideoEx["🎬 {uuid}_{name}<br/>video.mp4"]
    ReplyEx["📸 {uuid}_{name}<br/>screenshot.png"]
    
    Uploads --> Avatars
    Uploads --> Communities
    Uploads --> Posts
    Uploads --> Replies
    
    Avatars --> AvatarEx
    Communities --> CommunityEx
    Posts --> PostEx
    Posts --> VideoEx
    Replies --> ReplyEx
    
    style Uploads fill:#dc2626,stroke:#333,stroke-width:2px,color:#fff
    style Avatars fill:#7c3aed,stroke:#333,stroke-width:2px,color:#fff
    style Communities fill:#0891b2,stroke:#333,stroke-width:2px,color:#fff
    style Posts fill:#f59e0b,stroke:#333,stroke-width:2px,color:#fff
    style Replies fill:#06b6d4,stroke:#333,stroke-width:2px,color:#fff
    style AvatarEx fill:#a78bfa,stroke:#333,stroke-width:1px
    style CommunityEx fill:#06d6d4,stroke:#333,stroke-width:1px
    style PostEx fill:#fbbf24,stroke:#333,stroke-width:1px
    style VideoEx fill:#fb923c,stroke:#333,stroke-width:1px
    style ReplyEx fill:#67e8f9,stroke:#333,stroke-width:1px
```

---

## ER図

```mermaid
erDiagram
    User ||--o{ Post : "creates (user_id)"
    User ||--o{ Reply : "writes (user_id)"
    User ||--o{ Message : "sends (sender_id)"
    User ||--o{ Message : "receives (recipient_id)"
    User ||--o{ CommunityFollow : "follows (user_id)"
    User ||--o{ PostLike : "likes (user_id)"
    User ||--o{ ReplyLike : "likes (user_id)"
    User ||--o{ Community : "creates (created_by)"
    
    Community ||--o{ Post : "contains (community_id)"
    Community ||--o{ CommunityFollow : "followed by (community_id)"
    
    Post ||--o{ PostImage : "has (post_id)"
    Post ||--o{ Reply : "replied by (post_id)"
    Post ||--o{ PostLike : "liked by (post_id)"
    
    Reply ||--o{ Reply : "parent of (parent_id)"
    Reply ||--o{ ReplyLike : "liked by (reply_id)"
    Reply ||--o{ ReplyImage : "has (reply_id)"
    
    User {
        int id PK
        string username UK "NOT NULL"
        string password_hash "NOT NULL"
        string display_name
        string avatar_filename
        text bio
    }
    
    Community {
        int id PK
        string name UK "NOT NULL"
        text description
        string icon_filename
        int created_by FK "NULL可(公式用)"
        datetime created_at
    }
    
    Post {
        int id PK
        text body "NOT NULL"
        datetime created_at
        int user_id FK "NOT NULL, CASCADE"
        int community_id FK "NULL可, CASCADE"
        string video_filename
    }
    
    PostImage {
        int id PK
        int post_id FK "NOT NULL, CASCADE"
        string filename "NOT NULL"
        int order "表示順"
    }
    
    Reply {
        int id PK
        int post_id FK "NOT NULL, CASCADE"
        int parent_id FK "NULL可, 自己参照, CASCADE"
        int user_id FK "NOT NULL"
        text body "NOT NULL"
        datetime created_at
        string video_filename
    }
    
    ReplyImage {
        int id PK
        int reply_id FK "NOT NULL, CASCADE"
        string filename "NOT NULL"
        int order "表示順"
    }
    
    Message {
        int id PK
        text body "NOT NULL"
        datetime created_at
        int sender_id FK "NOT NULL"
        int recipient_id FK "NULL可"
        boolean is_read
        datetime read_at
    }
    
    CommunityFollow {
        int id PK
        int user_id FK "NOT NULL, CASCADE"
        int community_id FK "NOT NULL, CASCADE"
        datetime created_at
        string UNIQUE "user_id + community_id"
    }
    
    PostLike {
        int id PK
        int user_id FK "NOT NULL, CASCADE"
        int post_id FK "NOT NULL, CASCADE"
        datetime created_at
        string UNIQUE "user_id + post_id"
    }
    
    ReplyLike {
        int id PK
        int user_id FK "NOT NULL, CASCADE"
        int reply_id FK "NOT NULL, CASCADE"
        datetime created_at
        string UNIQUE "user_id + reply_id"
    }
```