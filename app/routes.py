import os
import shutil
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models import User, Post, Message, PostImage, Community, Reply, CommunityFollow, PostLike, ReplyLike, ReplyImage, db
from sqlalchemy import func
import json

bp = Blueprint('main', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov', 'avi', 'mkv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_upload_dir(upload_type):
    """用途別のアップロードディレクトリを取得・作成"""
    valid_types = {
        'avatars': 'ユーザープロフィール画像',
        'community_icons': 'コミュニティアイコン',
        'posts': '投稿画像・動画',
        'replies': '返信画像・動画'
    }
    if upload_type not in valid_types:
        raise ValueError(f"Invalid upload type: {upload_type}")
    
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], upload_type)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_upload_file(file, upload_type):
    """ファイルを用途別ディレクトリに保存し、ファイル名を返す"""
    if not file or file.filename == '' or not allowed_file(file.filename):
        return None
    
    filename = secure_filename(file.filename)
    unique = f"{uuid.uuid4().hex}_{filename}"
    upload_dir = get_upload_dir(upload_type)
    save_path = os.path.join(upload_dir, unique)
    file.save(save_path)
    return unique


def delete_upload_file(filename, upload_type):
    """用途別ディレクトリからファイルを削除"""
    if not filename:
        return
    
    upload_dir = get_upload_dir(upload_type)
    file_path = os.path.join(upload_dir, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass



def ensure_default_communities():
    """Create a couple of starter communities if none exist."""
    defaults = [
        {'name': '食べ物', 'description': '食に関する話題'},
        {'name': 'ペット', 'description': 'ペットに関する話題'},
        {'name': '日常', 'description': '日常の話題'},
    ]
    created = False
    changed = False
    # Create communities if missing
    for d in defaults:
        c = Community.query.filter_by(name=d['name']).first()
        if not c:
            c = Community(name=d['name'], description=d['description'])
            db.session.add(c)
            created = True
        # Attach preset icon if missing and resource exists
        if c and not c.icon_filename:
            try:
                # Look for preset icons in static/resources/community_icons/
                # e.g., 食べ物 -> food.png, ペット -> pet.png
                name_map = {
                    '食べ物': ['food.png', 'food.jpg', 'food.jpeg', 'food.gif'],
                    'ペット': ['pet.png', 'pet.jpg', 'pet.jpeg', 'pet.gif'],
                    '日常': ['daily.png', 'daily.jpg', 'daily.jpeg', 'daily.gif'],
                }
                src_dir = os.path.join(os.path.dirname(current_app.root_path), 'static', 'resources', 'community_icons')
                candidates = name_map.get(d['name'], [])
                for fname in candidates:
                    src_path = os.path.join(src_dir, fname)
                    if os.path.isfile(src_path) and allowed_file(fname):
                        # Save into uploads/community_icons with UUID prefix
                        base = secure_filename(fname)
                        unique = f"{uuid.uuid4().hex}_{base}"
                        dest_dir = get_upload_dir('community_icons')
                        dest_path = os.path.join(dest_dir, unique)
                        try:
                            shutil.copyfile(src_path, dest_path)
                            c.icon_filename = unique
                            changed = True
                            break
                        except Exception:
                            pass
            except Exception:
                # Ignore preset icon errors silently
                pass
    if created or changed:
        db.session.commit()


def build_reply_tree(replies):
    nodes = {r.id: {'reply': r, 'children': []} for r in replies}
    roots = []
    for r in replies:
        node = nodes[r.id]
        if r.parent_id and r.parent_id in nodes:
            nodes[r.parent_id]['children'].append(node)
        else:
            roots.append(node)
    return roots


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = User.query.get(user_id) if user_id else None
    # Calculate unread message count for logged-in users
    if g.user:
        g.unread_count = Message.query.filter_by(recipient_id=g.user.id, is_read=False).count()
        g.following_ids = {f.community_id for f in CommunityFollow.query.filter_by(user_id=g.user.id).all()}
        # Get all liked post and reply IDs for templates
        g.liked_post_ids = {like.post_id for like in PostLike.query.filter_by(user_id=g.user.id).all()}
        g.liked_reply_ids = {like.reply_id for like in ReplyLike.query.filter_by(user_id=g.user.id).all()}
    else:
        g.unread_count = 0
        g.following_ids = set()
        g.liked_post_ids = set()
        g.liked_reply_ids = set()


@bp.route('/')
def index():
    ensure_default_communities()
    tab = request.args.get('tab', 'home')  # home, latest, search
    sort_by = request.args.get('sort', 'latest')  # latest, likes, replies
    
    # If not logged in, default to 'latest' tab instead of 'home'
    if not g.user and tab == 'home':
        tab = 'latest'
    
    communities = Community.query.order_by(Community.name.asc()).all()
    
    # Get official communities (created_by is NULL)
    official_communities = Community.query.filter(Community.created_by.is_(None)).order_by(Community.name.asc()).all()
    
    # Get followed communities for logged-in users
    followed_communities = []
    if g.user:
        followed_ids = {f.community_id for f in CommunityFollow.query.filter_by(user_id=g.user.id).all()}
        followed_communities = Community.query.filter(Community.id.in_(followed_ids)).order_by(Community.name.asc()).all() if followed_ids else []
    
    posts = []
    selected_community = None
    
    if tab == 'home':
        # Show only posts from followed communities
        if g.user and followed_communities:
            followed_ids = [c.id for c in followed_communities]
            query = Post.query.filter(Post.community_id.in_(followed_ids))
            posts = query.all()
        # If not logged in or no follows, show nothing
    elif tab == 'latest':
        # Show all posts
        query = Post.query.filter(Post.community_id.isnot(None))
        posts = query.all()
    elif tab == 'search':
        # Search functionality
        if g.user:
            community_name = request.args.get('community_name', '').strip()
            followers_min = request.args.get('followers_min', type=int)
            followers_max = request.args.get('followers_max', type=int)
            sort_by = request.args.get('sort', 'name')  # name, followers, created_at
            
            query = Community.query
            if community_name:
                query = query.filter(Community.name.ilike(f'%{community_name}%'))
            
            # Apply sorting
            if sort_by == 'followers':
                # Sort by followers count (requires Python sorting after query)
                search_communities = query.all()
                search_communities = sorted(search_communities, key=lambda c: len(c.follows), reverse=True)
            elif sort_by == 'created_at':
                # Sort by creation date (newest first)
                search_communities = query.order_by(Community.created_at.desc()).all()
            else:  # 'name' (default)
                search_communities = query.order_by(Community.name.asc()).all()
            
            # Filter by follower count
            if followers_min is not None or followers_max is not None:
                filtered = []
                for c in search_communities:
                    count = len(c.follows)
                    if followers_min is not None and count < followers_min:
                        continue
                    if followers_max is not None and count > followers_max:
                        continue
                    filtered.append(c)
                search_communities = filtered
            
            return render_template('search_communities.html', 
                                 communities=communities,
                                 official_communities=official_communities,
                                 followed_communities=followed_communities,
                                 search_results=search_communities,
                                 search_params={'community_name': community_name, 'followers_min': followers_min, 'followers_max': followers_max},
                                 sort_by=sort_by)
    
    # Sort posts
    if posts:
        if sort_by == 'likes':
            posts = sorted(posts, key=lambda p: len(p.likes), reverse=True)
        elif sort_by == 'replies':
            posts = sorted(posts, key=lambda p: len(p.replies), reverse=True)
        else:  # latest (default)
            posts = sorted(posts, key=lambda p: p.created_at, reverse=True)
    
    return render_template('index.html', 
                         posts=posts, 
                         communities=communities,
                         official_communities=official_communities,
                         followed_communities=followed_communities,
                         selected_community=selected_community,
                         sort_by=sort_by,
                         current_tab=tab)


@bp.route('/search', methods=['GET', 'POST'])
def search_posts():
    ensure_default_communities()
    query = Post.query.filter(Post.community_id.isnot(None))
    search_params = {
        'username': request.args.get('username', '').strip(),
        'body': request.args.get('body', '').strip(),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', '')
    }
    
    # ユーザー名で検索
    if search_params['username']:
        user = User.query.filter(User.username.ilike(f"%{search_params['username']}%")).all()
        user_ids = [u.id for u in user]
        if user_ids:
            query = query.filter(Post.user_id.in_(user_ids))
        else:
            query = query.filter(Post.user_id == -1)  # 結果なし
    
    # 投稿本文で検索
    if search_params['body']:
        query = query.filter(Post.body.ilike(f"%{search_params['body']}%"))
    
    # 開始日時で検索
    if search_params['date_from']:
        try:
            from datetime import datetime
            date_from = datetime.strptime(search_params['date_from'], '%Y-%m-%d')
            query = query.filter(Post.created_at >= date_from)
        except (ValueError, TypeError):
            pass
    
    # 終了日時で検索
    if search_params['date_to']:
        try:
            from datetime import datetime
            date_to = datetime.strptime(search_params['date_to'], '%Y-%m-%d')
            # 翌日の開始までを含める
            from datetime import timedelta
            date_to = date_to + timedelta(days=1)
            query = query.filter(Post.created_at < date_to)
        except (ValueError, TypeError):
            pass

    sort_by = request.args.get('sort', 'latest')  # latest, likes, replies
    communities = Community.query.order_by(Community.name.asc()).all()
    posts = query.all()
    
    # Sort posts based on sort_by parameter
    if sort_by == 'likes':
        posts = sorted(posts, key=lambda p: len(p.likes), reverse=True)
    elif sort_by == 'replies':
        posts = sorted(posts, key=lambda p: len(p.replies), reverse=True)
    else:  # latest (default)
        posts = sorted(posts, key=lambda p: p.created_at, reverse=True)
    
    return render_template('index.html', posts=posts, communities=communities, selected_community=None, search_active=True, search_params=search_params, sort_by=sort_by)


@bp.route('/communities/new', methods=['GET', 'POST'])
def create_community():
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip()
        icon = request.files.get('icon')
        
        if not name:
            flash('コミュニティ名を入力してください')
            return redirect(url_for('main.create_community'))
        
        if Community.query.filter_by(name=name).first():
            flash('同名のコミュニティが既に存在します')
            return redirect(url_for('main.create_community'))
        
        c = Community(name=name, description=description or None, created_by=g.user.id)
        # 先にアイコンファイルを保存（失敗時は中止）
        if icon and icon.filename != '':
            icon_filename = save_upload_file(icon, 'community_icons')
            c.icon_filename = icon_filename
        try:
            db.session.add(c)
            # flush して ID を取得
            db.session.flush()
            follow = CommunityFollow(user_id=g.user.id, community_id=c.id)
            db.session.add(follow)
            db.session.commit()
        except Exception:
            db.session.rollback()
            # アイコンファイルをクリーンアップ
            if c.icon_filename:
                delete_upload_file(c.icon_filename, 'community_icons')
            flash('コミュニティ作成に失敗しました')
            return redirect(url_for('main.create_community'))
        
        flash('コミュニティを作成しました')
        return redirect(url_for('main.community_page', community_id=c.id))
    
    return render_template('create_community.html')


@bp.route('/communities/<int:community_id>', methods=['GET'])
def community_page(community_id):
    c = Community.query.get_or_404(community_id)
    
    # Get statistics
    posts_count = len(c.posts)
    followers_count = len(c.follows)
    
    # Get sort parameter
    sort_by = request.args.get('sort', 'latest')  # latest, likes, replies
    posts = c.posts
    
    # Sort posts based on sort_by parameter
    if sort_by == 'likes':
        posts = sorted(posts, key=lambda p: len(p.likes), reverse=True)
    elif sort_by == 'replies':
        posts = sorted(posts, key=lambda p: len(p.replies), reverse=True)
    else:  # latest (default)
        posts = sorted(posts, key=lambda p: p.created_at, reverse=True)
    
    communities = Community.query.order_by(Community.name.asc()).all()
    official_communities = Community.query.filter(Community.created_by.is_(None)).order_by(Community.name.asc()).all()
    followed_communities = []
    if g.user:
        followed_ids = {f.community_id for f in CommunityFollow.query.filter_by(user_id=g.user.id).all()}
        followed_communities = Community.query.filter(Community.id.in_(followed_ids)).order_by(Community.name.asc()).all() if followed_ids else []
    
    # Get creator info
    creator = User.query.get(c.created_by) if c.created_by else None
    
    return render_template('community.html', 
                         community=c, 
                         posts=posts,
                         posts_count=posts_count,
                         followers_count=followers_count,
                         communities=communities,
                         followed_communities=followed_communities,
                         official_communities=official_communities,
                         creator=creator,
                         sort_by=sort_by)



@bp.route('/communities/<int:community_id>/follow', methods=['POST'])
def follow_community(community_id):
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    community = Community.query.get_or_404(community_id)
    existing = CommunityFollow.query.filter_by(user_id=g.user.id, community_id=community.id).first()
    if not existing:
        try:
            db.session.add(CommunityFollow(user_id=g.user.id, community_id=community.id))
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('フォローに失敗しました')
            next_url = request.form.get('next') or url_for('main.index', community=community.id)
            return redirect(next_url)
        flash(f'{community.name} をフォローしました')
    next_url = request.form.get('next') or url_for('main.index', community=community.id)
    return redirect(next_url)


@bp.route('/communities/<int:community_id>/unfollow', methods=['POST'])
def unfollow_community(community_id):
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    community = Community.query.get_or_404(community_id)
    
    # 設立者はフォロー解除できない
    if community.created_by == g.user.id:
        flash('設立者はこのコミュニティをフォロー解除できません')
        next_url = request.form.get('next') or url_for('main.community_page', community_id=community.id)
        return redirect(next_url)
    
    existing = CommunityFollow.query.filter_by(user_id=g.user.id, community_id=community.id).first()
    if existing:
        try:
            db.session.delete(existing)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('フォロー解除に失敗しました')
            next_url = request.form.get('next') or url_for('main.index', community=community.id)
            return redirect(next_url)
        flash(f'{community.name} のフォローを解除しました')
    next_url = request.form.get('next') or url_for('main.index', community=community.id)
    return redirect(next_url)


@bp.route('/communities/<int:community_id>/delete', methods=['POST'])
def delete_community(community_id):
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    community = Community.query.get_or_404(community_id)
    # Only creator can delete
    if community.created_by != g.user.id:
        flash('コミュニティを削除する権限がありません')
        return redirect(url_for('main.index', community=community.id))
    name = community.name
    try:
        db.session.delete(community)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('コミュニティの削除に失敗しました')
        return redirect(url_for('main.index', community=community.id))
    flash(f'{name} を削除しました')
    return redirect(url_for('main.index'))

# Posts
@bp.route('/post', methods=['POST'])
def create_post():
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    body = request.form.get('body')
    community_id_raw = request.form.get('community_id')
    try:
        community_id = int(community_id_raw) if community_id_raw else None
    except ValueError:
        community_id = None
    if not community_id:
        flash('コミュニティを選択してください')
        return redirect(url_for('main.index'))
    community = Community.query.get(community_id)
    if not community:
        flash('選択したコミュニティが見つかりません')
        return redirect(url_for('main.index'))
    # Require follow to create a thread
    is_following = CommunityFollow.query.filter_by(user_id=g.user.id, community_id=community.id).first()
    if not is_following:
        flash('このコミュニティをフォローするとスレッドを立てられます')
        return redirect(url_for('main.index', community=community.id))
    
    # Get all uploaded files
    uploaded_files = request.files.getlist('files')
    
    # Separate images and video
    image_files = []
    video_file = None
    
    for file in uploaded_files:
        if not file or file.filename == '':
            continue
        
        if not allowed_file(file.filename):
            flash('無効なファイル形式です：' + file.filename)
            return redirect(url_for('main.index'))
        
        if file.content_type.startswith('image/'):
            if len(image_files) < 4:
                image_files.append(file)
            else:
                flash('画像は最大4個までです')
                return redirect(url_for('main.index'))
        elif file.content_type.startswith('video/'):
            if video_file is None:
                video_file = file
            else:
                flash('動画は1つまでです')
                return redirect(url_for('main.index'))
    
    # Validation: must have body or files
    if not body and not image_files and not video_file:
        flash('本文、画像、または動画が必要です')
        return redirect(url_for('main.index'))
    
    # Validation: can't have both images and video
    if image_files and video_file:
        flash('画像と動画は同時に添付できません')
        return redirect(url_for('main.index'))

    # Create post instance
    p = Post(body=body or '', user_id=g.user.id, community_id=community.id)
    saved_images = []
    saved_video = None

    # Handle image uploads (up to 4)
    for order, image_file in enumerate(image_files):
        if image_file and image_file.filename != '':
            image_filename = save_upload_file(image_file, 'posts')
            if image_filename:
                img = PostImage(filename=image_filename, order=order)
                p.images.append(img)
                saved_images.append(image_filename)
            else:
                flash('画像の保存に失敗しました')
                return redirect(url_for('main.index'))
    
    # Handle video upload (max 1)
    if video_file and video_file.filename != '':
        video_filename = save_upload_file(video_file, 'posts')
        if video_filename:
            p.video_filename = video_filename
            saved_video = video_filename
        else:
            flash('動画の保存に失敗しました')
            return redirect(url_for('main.index'))

    try:
        db.session.add(p)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # cleanup saved files if DB write fails
        for fn in saved_images:
            delete_upload_file(fn, 'posts')
        if saved_video:
            delete_upload_file(saved_video, 'posts')
        flash('投稿の保存に失敗しました')
        return redirect(url_for('main.index'))
    flash('投稿しました')
    return redirect(url_for('main.view_post', post_id=p.id))


@bp.route('/post/<int:post_id>')
def view_post(post_id):
    p = Post.query.get_or_404(post_id)
    replies = Reply.query.filter_by(post_id=p.id).order_by(Reply.created_at.asc()).all()
    reply_tree = build_reply_tree(replies)
    communities = Community.query.order_by(Community.name.asc()).all()
    official_communities = Community.query.filter(Community.created_by.is_(None)).order_by(Community.name.asc()).all()
    followed_communities = []
    if g.user:
        followed_ids = {f.community_id for f in CommunityFollow.query.filter_by(user_id=g.user.id).all()}
        followed_communities = Community.query.filter(Community.id.in_(followed_ids)).order_by(Community.name.asc()).all() if followed_ids else []
    return render_template('view_post.html', post=p, reply_tree=reply_tree, communities=communities, followed_communities=followed_communities, official_communities=official_communities)


@bp.route('/post/<int:post_id>/reply', methods=['POST'])
def reply_post(post_id):
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    body = (request.form.get('body') or '').strip()
    parent_reply_raw = request.form.get('parent_reply_id')
    parent_reply_id = None
    try:
        parent_reply_id = int(parent_reply_raw) if parent_reply_raw else None
    except ValueError:
        parent_reply_id = None

    post = Post.query.get_or_404(post_id)
    parent_reply = None
    if parent_reply_id:
        parent_reply = Reply.query.filter_by(id=parent_reply_id, post_id=post_id).first()
        if not parent_reply:
            flash('返信先が見つかりません')
            return redirect(url_for('main.view_post', post_id=post_id))

    # Handle attachments (up to 4 images OR 1 video)
    uploaded_files = request.files.getlist('files')
    image_files = []
    video_file = None

    for file in uploaded_files:
        if not file or file.filename == '':
            continue
        if not allowed_file(file.filename):
            flash('無効なファイル形式です：' + file.filename)
            return redirect(url_for('main.view_post', post_id=post_id))

        if file.content_type.startswith('image/'):
            if len(image_files) < 4:
                image_files.append(file)
            else:
                flash('画像は最大4個までです')
                return redirect(url_for('main.view_post', post_id=post_id))
        elif file.content_type.startswith('video/'):
            if video_file is None:
                video_file = file
            else:
                flash('動画は1つまでです')
                return redirect(url_for('main.view_post', post_id=post_id))

    # Require body or at least one attachment
    if not body and not image_files and not video_file:
        flash('返信本文、画像、または動画が必要です')
        return redirect(url_for('main.view_post', post_id=post_id))

    # Cannot mix images and video
    if image_files and video_file:
        flash('画像と動画は同時に添付できません')
        return redirect(url_for('main.view_post', post_id=post_id))

    r = Reply(body=body or '', post_id=post.id, user_id=g.user.id, parent_id=(parent_reply.id if parent_reply else None))
    saved_images = []
    saved_video = None

    # Save images
    for order, image_file in enumerate(image_files):
        image_filename = save_upload_file(image_file, 'replies')
        if image_filename:
            img = ReplyImage(filename=image_filename, order=order)
            r.images.append(img)
            saved_images.append(image_filename)
        else:
            flash('画像の保存に失敗しました')
            return redirect(url_for('main.view_post', post_id=post_id))

    # Save video
    if video_file and video_file.filename != '':
        video_filename = save_upload_file(video_file, 'replies')
        if video_filename:
            r.video_filename = video_filename
            saved_video = video_filename
        else:
            flash('動画の保存に失敗しました')
            return redirect(url_for('main.view_post', post_id=post_id))

    try:
        db.session.add(r)
        db.session.commit()
    except Exception:
        db.session.rollback()
        for fn in saved_images:
            delete_upload_file(fn, 'replies')
        if saved_video:
            delete_upload_file(saved_video, 'replies')
        flash('返信の保存に失敗しました')
        return redirect(url_for('main.view_post', post_id=post_id))
    flash('返信しました')
    return redirect(url_for('main.view_post', post_id=post_id))


@bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    # Editing posts is not supported in this app by design
    flash('投稿の編集はサポートされていません')
    return redirect(url_for('main.view_post', post_id=post_id))


@bp.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    from urllib.parse import urlparse
    p = Post.query.get_or_404(post_id)
    if not g.user or g.user.id != p.user_id:
        flash('権限がありません')
        return redirect(url_for('main.index'))
    
    # Remove attached image files
    for img in p.images:
        delete_upload_file(img.filename, 'posts')
    
    # Remove attached video file
    if p.video_filename:
        delete_upload_file(p.video_filename, 'posts')

    # Remove reply attachments (images/videos)
    for reply in p.replies:
        for rimg in reply.images:
            delete_upload_file(rimg.filename, 'replies')
        if reply.video_filename:
            delete_upload_file(reply.video_filename, 'replies')
    
    try:
        db.session.delete(p)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('投稿の削除に失敗しました')
        next_url = request.form.get('next')
        if next_url:
            return redirect(next_url)
        ref = request.referrer
        if ref:
            parsed = urlparse(ref)
            if parsed.netloc == request.host:
                path = parsed.path or url_for('main.index')
                return redirect(path)
        return redirect(url_for('main.index'))
    flash('削除しました')
    # redirect back to caller when possible
    next_url = request.form.get('next')
    if next_url:
        return redirect(next_url)
    ref = request.referrer
    if ref:
        parsed = urlparse(ref)
        if parsed.netloc == request.host:
            path = parsed.path or url_for('main.index')
            return redirect(path)
    return redirect(url_for('main.index'))


@bp.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    from flask import jsonify
    if not g.user:
        return jsonify({'error': 'ログインが必要です'}), 401
    post = Post.query.get_or_404(post_id)
    existing = PostLike.query.filter_by(user_id=g.user.id, post_id=post.id).first()
    if not existing:
        try:
            db.session.add(PostLike(user_id=g.user.id, post_id=post.id))
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({'error': 'いいねに失敗しました'}), 500
    like_count = PostLike.query.filter_by(post_id=post.id).count()
    return jsonify({'success': True, 'liked': True, 'like_count': like_count})


@bp.route('/post/<int:post_id>/unlike', methods=['POST'])
def unlike_post(post_id):
    from flask import jsonify
    if not g.user:
        return jsonify({'error': 'ログインが必要です'}), 401
    post = Post.query.get_or_404(post_id)
    existing = PostLike.query.filter_by(user_id=g.user.id, post_id=post.id).first()
    if existing:
        try:
            db.session.delete(existing)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({'error': 'いいね解除に失敗しました'}), 500
    like_count = PostLike.query.filter_by(post_id=post.id).count()
    return jsonify({'success': True, 'liked': False, 'like_count': like_count})


@bp.route('/reply/<int:reply_id>/like', methods=['POST'])
def like_reply(reply_id):
    from flask import jsonify
    if not g.user:
        return jsonify({'error': 'ログインが必要です'}), 401
    reply = Reply.query.get_or_404(reply_id)
    existing = ReplyLike.query.filter_by(user_id=g.user.id, reply_id=reply.id).first()
    if not existing:
        try:
            db.session.add(ReplyLike(user_id=g.user.id, reply_id=reply.id))
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({'error': '返信へのいいねに失敗しました'}), 500
    like_count = ReplyLike.query.filter_by(reply_id=reply.id).count()
    return jsonify({'success': True, 'liked': True, 'like_count': like_count})


@bp.route('/reply/<int:reply_id>/unlike', methods=['POST'])
def unlike_reply(reply_id):
    from flask import jsonify
    if not g.user:
        return jsonify({'error': 'ログインが必要です'}), 401
    reply = Reply.query.get_or_404(reply_id)
    existing = ReplyLike.query.filter_by(user_id=g.user.id, reply_id=reply.id).first()
    if existing:
        try:
            db.session.delete(existing)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({'error': '返信のいいね解除に失敗しました'}), 500
    like_count = ReplyLike.query.filter_by(reply_id=reply.id).count()
    return jsonify({'success': True, 'liked': False, 'like_count': like_count})

# Messages (unchanged)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        avatar = request.files.get('avatar')
        if not username or not password:
            flash('ユーザー名とパスワードが必要です')
            return redirect(url_for('main.register'))
        # 大小文字差を無視して重複をチェック
        if User.query.filter(func.lower(User.username) == username.lower()).first():
            flash('ユーザー名は既に存在します')
            return redirect(url_for('main.register'))
        u = User(username=username)
        u.set_password(password)
        u.display_name = display_name or None
        # handle avatar upload
        if avatar and avatar.filename != '':
            avatar_filename = save_upload_file(avatar, 'avatars')
            if avatar_filename:
                u.avatar_filename = avatar_filename
            else:
                flash('アバターの保存に失敗しました')
                return redirect(url_for('main.register'))
        try:
            db.session.add(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
            # cleanup avatar if saved
            if u.avatar_filename:
                delete_upload_file(u.avatar_filename, 'avatars')
            flash('登録に失敗しました')
            return redirect(url_for('main.register'))
        session['user_id'] = u.id
        flash('登録してログインしました')
        return redirect(url_for('main.index'))
    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        u = User.query.filter_by(username=username).first()
        if not u or not u.check_password(password):
            flash('ユーザー名またはパスワードが無効です')
            return redirect(url_for('main.login'))
        session['user_id'] = u.id
        flash('ログインしました')
        return redirect(url_for('main.index'))
    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('ログアウトしました')
    return redirect(url_for('main.index'))


@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if not g.user:
        flash('Login required')
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        display_name = request.form.get('display_name')
        bio = request.form.get('bio')
        avatar = request.files.get('avatar')
        # update fields
        g.user.display_name = display_name or None
        g.user.bio = bio or None
        # handle avatar
        remove_flag = request.form.get('remove_avatar')
        new_avatar_filename = None
        # 先に新規アバター保存（失敗時は中止）
        if avatar and avatar.filename != '':
            avatar_filename = save_upload_file(avatar, 'avatars')
            if not avatar_filename:
                flash('アバターの保存に失敗しました')
                return redirect(url_for('main.settings'))
            new_avatar_filename = avatar_filename
        try:
            if remove_flag and g.user.avatar_filename:
                # DBだけ先に消す（ファイル削除はコミット後に実施）
                old = g.user.avatar_filename
                g.user.avatar_filename = None
            if new_avatar_filename:
                # 古いファイル名はコミット後に削除
                old = g.user.avatar_filename
                g.user.avatar_filename = new_avatar_filename
            db.session.commit()
        except Exception:
            db.session.rollback()
            # 新規アバターが保存済みならクリーンアップ
            if new_avatar_filename:
                delete_upload_file(new_avatar_filename, 'avatars')
            flash('設定更新に失敗しました')
            # redirect back
            next_url = request.form.get('next')
            if next_url:
                return redirect(next_url)
            from urllib.parse import urlparse
            ref = request.referrer
            if ref:
                parsed = urlparse(ref)
                if parsed.netloc == request.host:
                    path = parsed.path or url_for('main.settings')
                    return redirect(path)
            return redirect(url_for('main.settings'))
        # コミット後にファイル削除（選択されていた場合）
        if remove_flag and g.user.avatar_filename is None:
            # 直前の古いファイル名を推定できない場合は何もしない
            pass
        # 古いアバターがある場合の削除はテンプレート側フラグとUIで扱うためここでは控える
        flash('設定を更新しました')
        # redirect back to caller when possible (modal or next param)
        next_url = request.form.get('next')
        if next_url:
            return redirect(next_url)
        from urllib.parse import urlparse
        ref = request.referrer
        if ref:
            parsed = urlparse(ref)
            if parsed.netloc == request.host:
                path = parsed.path or url_for('main.settings')
                return redirect(path)
        return redirect(url_for('main.settings'))
    # GET: include current bio for the form
    bio = g.user.bio
    return render_template('settings.html', bio=bio)


@bp.route('/account/delete', methods=['POST'])
def delete_account():
    """Delete user account and transfer community ownership to oldest follower"""
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    
    # Get password confirmation
    password = request.form.get('password')
    if not g.user.check_password(password):
        flash('パスワードが正しくありません')
        return redirect(url_for('main.settings'))
    
    username = g.user.username
    user_id = g.user.id
    
    # 先に削除対象ファイル名を収集（DBトランザクション成功後に削除）
    files_to_delete = []
    user_posts = Post.query.filter_by(user_id=user_id).all()
    for post in user_posts:
        for img in post.images:
            files_to_delete.append(('posts', img.filename))
        if post.video_filename:
            files_to_delete.append(('posts', post.video_filename))
        for reply in post.replies:
            for rimg in reply.images:
                files_to_delete.append(('replies', rimg.filename))
            if reply.video_filename:
                files_to_delete.append(('replies', reply.video_filename))
    user_replies = Reply.query.filter_by(user_id=user_id).all()
    for reply in user_replies:
        for rimg in reply.images:
            files_to_delete.append(('replies', rimg.filename))
        if reply.video_filename:
            files_to_delete.append(('replies', reply.video_filename))
    communities_created = Community.query.filter_by(created_by=user_id).all()
    for community in communities_created:
        if community.icon_filename:
            files_to_delete.append(('community_icons', community.icon_filename))
    if g.user.avatar_filename:
        files_to_delete.append(('avatars', g.user.avatar_filename))

    try:
        # Delete user's posts and replies
        for post in user_posts:
            for reply in post.replies:
                db.session.delete(reply)
            db.session.delete(post)
        for reply in user_replies:
            db.session.delete(reply)
        # Delete messages
        sent_messages = Message.query.filter_by(sender_id=user_id).all()
        for msg in sent_messages:
            db.session.delete(msg)
        received_messages = Message.query.filter_by(recipient_id=user_id).all()
        for msg in received_messages:
            db.session.delete(msg)
        # Transfer or delete communities
        for community in communities_created:
            oldest_follow = CommunityFollow.query.filter_by(community_id=community.id).filter(
                CommunityFollow.user_id != user_id
            ).order_by(CommunityFollow.created_at.asc()).first()
            if oldest_follow:
                community.created_by = oldest_follow.user_id
            else:
                db.session.delete(community)
        # Delete the user
        db.session.delete(g.user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('アカウント削除に失敗しました')
        return redirect(url_for('main.settings'))

    # コミット成功後にファイル削除
    for typ, fn in files_to_delete:
        delete_upload_file(fn, typ)
    
    # Clear session
    session.clear()
    
    flash(f'アカウント「{username}」を削除しました')
    return redirect(url_for('main.index'))


@bp.route('/user/<username>')
def user(username):
    u = User.query.filter_by(username=username).first()
    if not u:
        flash('ユーザーが見つかりません')
        return redirect(url_for('main.index'))
    sort_by = request.args.get('sort', 'latest')  # latest, likes, replies
    posts = Post.query.filter_by(user_id=u.id).all()
    
    # Sort posts based on sort_by parameter
    if sort_by == 'likes':
        posts = sorted(posts, key=lambda p: len(p.likes), reverse=True)
    elif sort_by == 'replies':
        posts = sorted(posts, key=lambda p: len(p.replies), reverse=True)
    else:  # latest (default)
        posts = sorted(posts, key=lambda p: p.created_at, reverse=True)
    
    communities = Community.query.order_by(Community.name.asc()).all()
    official_communities = Community.query.filter(Community.created_by.is_(None)).order_by(Community.name.asc()).all()
    followed_communities = []
    if g.user:
        followed_ids = {f.community_id for f in CommunityFollow.query.filter_by(user_id=g.user.id).all()}
        followed_communities = Community.query.filter(Community.id.in_(followed_ids)).order_by(Community.name.asc()).all() if followed_ids else []
    
    # Get communities followed by the displayed user
    user_followed_ids = {f.community_id for f in CommunityFollow.query.filter_by(user_id=u.id).all()}
    user_followed_communities = Community.query.filter(Community.id.in_(user_followed_ids)).order_by(Community.name.asc()).all() if user_followed_ids else []
    
    bio = u.bio
    return render_template('user.html', user=u, posts=posts, bio=bio, sort_by=sort_by, communities=communities, followed_communities=followed_communities, official_communities=official_communities, user_followed_communities=user_followed_communities)


@bp.route('/messages/<username>', methods=['GET', 'POST'])
def messages_with(username):
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    other = User.query.filter_by(username=username).first_or_404()
    if request.method == 'POST':
        body = request.form.get('body')
        if not body:
            flash('メッセージ本文が必要です')
            return redirect(url_for('main.messages_with', username=username))
        # prevent messaging yourself
        if other.id == g.user.id:
            flash('自分自身にメッセージを送信することはできません')
            return redirect(url_for('main.messages'))
        m = Message(body=body, sender_id=g.user.id, recipient_id=other.id)
        try:
            db.session.add(m)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('メッセージ送信に失敗しました')
            return redirect(url_for('main.messages_with', username=username))
        flash('メッセージを送信しました')
        return redirect(url_for('main.messages_with', username=username))
    # conversation between g.user and other
    conv = Message.query.filter(
        ((Message.sender_id == g.user.id) & (Message.recipient_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.recipient_id == g.user.id))
    ).order_by(Message.created_at.asc()).all()
    # mark received messages as read
    from datetime import datetime
    for msg in conv:
        if msg.recipient_id == g.user.id and not msg.is_read:
            msg.is_read = True
            msg.read_at = datetime.utcnow()
    db.session.commit()
    return render_template('messages_thread.html', other=other, messages=conv)


# Messages
@bp.route('/messages', methods=['GET', 'POST'])
def messages():
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        body = request.form.get('body')
        recipient = request.form.get('recipient')
        if not body:
            flash('メッセージ本文が必要です')
            return redirect(url_for('main.messages'))
        recipient_user = None
        if recipient:
            recipient_user = User.query.filter_by(username=recipient).first()
            if not recipient_user:
                flash('送信先ユーザーが見つかりません')
                return redirect(url_for('main.messages'))
            if recipient_user.id == g.user.id:
                flash('自分自身にメッセージを送信することはできません')
                return redirect(url_for('main.messages'))
        m = Message(body=body, sender_id=g.user.id, recipient_id=(recipient_user.id if recipient_user else None))
        try:
            db.session.add(m)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('メッセージ送信に失敗しました')
            if recipient and recipient_user:
                return redirect(url_for('main.messages', username=recipient_user.username))
            return redirect(url_for('main.messages'))
        flash('メッセージを送信しました')
        # if a recipient username was provided and found, show the thread
        if recipient and recipient_user:
            return redirect(url_for('main.messages', username=recipient_user.username))
        return redirect(url_for('main.messages'))

    # Build conversation threads: partners and last message
    msgs = Message.query.filter((Message.sender_id == g.user.id) | (Message.recipient_id == g.user.id)).order_by(Message.created_at.desc()).all()
    partners = {}
    for m in msgs:
        other_id = m.sender_id if m.sender_id != g.user.id else m.recipient_id
        if other_id is None:
            other_key = None
        else:
            other_key = other_id
        if other_key not in partners:
            partners[other_key] = m
    partner_objs = []
    for k, last_msg in partners.items():
        if k is None:
            partner_objs.append({'user': None, 'last': last_msg, 'unread_count': 0})
        else:
            u = User.query.get(k)
            # Count unread messages from this specific user
            unread_count = Message.query.filter_by(sender_id=k, recipient_id=g.user.id, is_read=False).count()
            partner_objs.append({'user': u, 'last': last_msg, 'unread_count': unread_count})

    # if username param is present, load the thread for that user to show on the right column
    username = request.args.get('username')
    other = None
    thread = None
    if username:
        other = User.query.filter_by(username=username).first()
        if other:
            thread = Message.query.filter(
                ((Message.sender_id == g.user.id) & (Message.recipient_id == other.id)) |
                ((Message.sender_id == other.id) & (Message.recipient_id == g.user.id))
            ).order_by(Message.created_at.asc()).all()
            # mark received messages as read
            from datetime import datetime
            for msg in thread:
                if msg.recipient_id == g.user.id and not msg.is_read:
                    msg.is_read = True
                    msg.read_at = datetime.utcnow()
            db.session.commit()

    communities = Community.query.order_by(Community.name.asc()).all()
    official_communities = Community.query.filter(Community.created_by.is_(None)).order_by(Community.name.asc()).all()
    followed_communities = []
    if g.user:
        followed_ids = {f.community_id for f in CommunityFollow.query.filter_by(user_id=g.user.id).all()}
        followed_communities = Community.query.filter(Community.id.in_(followed_ids)).order_by(Community.name.asc()).all() if followed_ids else []
    return render_template('messages.html', partners=partner_objs, other=other, messages_thread=thread, communities=communities, followed_communities=followed_communities, official_communities=official_communities)


@bp.route('/message/<int:msg_id>/delete', methods=['POST'])
def delete_message(msg_id):
    from urllib.parse import urlparse
    m = Message.query.get_or_404(msg_id)
    if not g.user or g.user.id != m.sender_id:
        flash('権限がありません')
        return redirect(url_for('main.messages'))
    try:
        db.session.delete(m)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('メッセージ削除に失敗しました')
        next_url = request.form.get('next')
        if next_url:
            return redirect(next_url)
        ref = request.referrer
        if ref:
            parsed = urlparse(ref)
            if parsed.netloc == request.host:
                path = parsed.path or url_for('main.messages')
                return redirect(path)
        return redirect(url_for('main.messages'))
    flash('メッセージを削除しました')
    # Prefer an explicit next param, otherwise fall back to referrer if internal, else messages
    next_url = request.form.get('next')
    if next_url:
        return redirect(next_url)
    ref = request.referrer
    if ref:
        parsed = urlparse(ref)
        # if same host, redirect back to path
        if parsed.netloc == request.host:
            path = parsed.path or url_for('main.messages')
            return redirect(path)
    return redirect(url_for('main.messages'))


@bp.route('/api/messages/<username>')
def api_get_messages(username):
    """API endpoint to fetch messages with a specific user (for real-time updates)"""
    from flask import jsonify
    if not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    other = User.query.filter_by(username=username).first()
    if not other:
        return jsonify({'error': 'User not found'}), 404
    
    # Get all messages between current user and the other user
    conv = Message.query.filter(
        ((Message.sender_id == g.user.id) & (Message.recipient_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.recipient_id == g.user.id))
    ).order_by(Message.created_at.asc()).all()
    
    # Mark received messages as read
    from datetime import datetime
    for msg in conv:
        if msg.recipient_id == g.user.id and not msg.is_read:
            msg.is_read = True
            msg.read_at = datetime.utcnow()
    db.session.commit()
    
    # Convert messages to JSON format
    messages_data = []
    for m in conv:
        avatar_path = None
        if m.sender and m.sender.avatar_filename:
            avatar_path = f"avatars/{m.sender.avatar_filename}"
        messages_data.append({
            'id': m.id,
            'body': m.body,
            'sender_id': m.sender_id,
            'recipient_id': m.recipient_id,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': m.is_read,
            'sender_avatar': avatar_path,
            'sender_display_name': m.sender.display_name or m.sender.username if m.sender else None
        })
    
    return jsonify({'messages': messages_data})


@bp.route('/api/unread-count')
def api_unread_count():
    """API endpoint to fetch unread message count"""
    from flask import jsonify
    if not g.user:
        return jsonify({'unread_count': 0}), 401
    
    unread_count = Message.query.filter_by(recipient_id=g.user.id, is_read=False).count()
    return jsonify({'unread_count': unread_count})


@bp.route('/api/partner-unread-count/<username>')
def api_partner_unread_count(username):
    """API endpoint to fetch unread message count for a specific partner"""
    from flask import jsonify
    if not g.user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get the partner user
    partner = User.query.filter_by(username=username).first()
    if not partner:
        return jsonify({'error': 'User not found'}), 404
    
    # Count unread messages from this specific partner
    unread_count = Message.query.filter_by(sender_id=partner.id, recipient_id=g.user.id, is_read=False).count()
    return jsonify({'unread_count': unread_count, 'username': username})


@bp.route('/api/post/<int:post_id>/images')
def api_post_images(post_id):
    """API endpoint to fetch all images for a post"""
    from flask import jsonify
    post = Post.query.get_or_404(post_id)
    
    # Get all images sorted by order, with upload_type for proper URL construction
    images = [{'filename': img.filename, 'order': img.order, 'upload_type': 'posts'} for img in sorted(post.images, key=lambda x: x.order)]
    return jsonify({'post_id': post_id, 'images': images})


@bp.route('/api/reply/<int:reply_id>/images')
def api_reply_images(reply_id):
    """API endpoint to fetch all images for a reply"""
    from flask import jsonify
    reply = Reply.query.get_or_404(reply_id)
    
    # Get all images sorted by order, with upload_type for proper URL construction
    images = [{'filename': img.filename, 'order': img.order, 'upload_type': 'replies'} for img in sorted(reply.images, key=lambda x: x.order)]
    return jsonify({'reply_id': reply_id, 'images': images})


@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
