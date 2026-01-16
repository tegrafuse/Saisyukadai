import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models import User, Post, Message, db
import json


def _profiles_path():
    # store small profile bios in instance/profiles.json to avoid schema changes
    path = os.path.join(current_app.instance_path, 'profiles.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def _read_profiles():
    try:
        with open(_profiles_path(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _write_profiles(d):
    with open(_profiles_path(), 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def get_profile_bio(username):
    val = _read_profiles().get(username, {}).get('bio')
    # normalize non-meaningful values to None
    if not val or (isinstance(val, str) and val.strip().lower() in ('none','null')):
        return None
    return val


def set_profile_bio(username, bio):
    p = _read_profiles()
    # if bio is falsy (None or empty string), remove the user's bio entry to avoid stale defaults
    if not bio:
        if username in p:
            try:
                del p[username]['bio']
                # if the user object has no other keys, remove the user entirely
                if not p[username]:
                    del p[username]
            except KeyError:
                pass
    else:
        p.setdefault(username, {})
        p[username]['bio'] = bio
    _write_profiles(p)


def remove_profile(username):
    p = _read_profiles()
    if username in p:
        del p[username]
        _write_profiles(p)

bp = Blueprint('main', __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = User.query.get(user_id) if user_id else None
    # Calculate unread message count for logged-in users
    if g.user:
        g.unread_count = Message.query.filter_by(recipient_id=g.user.id, is_read=False).count()
    else:
        g.unread_count = 0


@bp.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts, search_active=False)


@bp.route('/search', methods=['GET', 'POST'])
def search_posts():
    query = Post.query
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
    
    posts = query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts, search_active=True, search_params=search_params)

# Posts
@bp.route('/post', methods=['POST'])
def create_post():
    if not g.user:
        flash('ログインが必要です')
        return redirect(url_for('main.login'))
    body = request.form.get('body')
    file = request.files.get('image')
    has_valid_image = bool(file and file.filename != '' and allowed_file(file.filename))
    if not body and not has_valid_image:
        flash('本文または画像が必要です')
        return redirect(url_for('main.index'))

    # create post instance
    p = Post(body=body or '', user_id=g.user.id)

    # handle image upload (optional single image)
    if file and file.filename != '':
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique)
            file.save(save_path)
            p.image_filename = unique
            p.image_caption = request.form.get('image_caption')
            # ensure body is at least empty string (already handled)
        else:
            flash('無効なファイルです')
            return redirect(url_for('main.index'))

    db.session.add(p)
    db.session.commit()
    flash('投稿しました')
    return redirect(url_for('main.index'))


@bp.route('/post/<int:post_id>')
def view_post(post_id):
    p = Post.query.get_or_404(post_id)
    return render_template('view_post.html', post=p)


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
    # remove attached image file
    if p.image_filename:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], p.image_filename))
        except Exception:
            pass
    db.session.delete(p)
    db.session.commit()
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

# Messages (unchanged)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        display_name = request.form.get('display_name')
        avatar = request.files.get('avatar')
        if not username or not password:
            flash('ユーザー名とパスワードが必要です')
            return redirect(url_for('main.register'))
        if User.query.filter_by(username=username).first():
            flash('ユーザー名は既に存在します')
            return redirect(url_for('main.register'))
        u = User(username=username)
        u.set_password(password)
        u.display_name = display_name or None
        # handle avatar upload
        if avatar and avatar.filename != '' and allowed_file(avatar.filename):
            filename = secure_filename(avatar.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique)
            avatar.save(save_path)
            u.avatar_filename = unique
        db.session.add(u)
        db.session.commit()
        # ensure there is no stale profile bio data for this username
        remove_profile(u.username)
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
        # save bio to profiles store (avoids DB schema change)
        set_profile_bio(g.user.username, bio or None)
        # handle avatar
        if request.form.get('remove_avatar'):
            if g.user.avatar_filename:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], g.user.avatar_filename))
                except Exception:
                    pass
                g.user.avatar_filename = None
        if avatar and avatar.filename != '' and allowed_file(avatar.filename):
            # remove old
            if g.user.avatar_filename:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], g.user.avatar_filename))
                except Exception:
                    pass
            filename = secure_filename(avatar.filename)
            unique = f"{uuid.uuid4().hex}_{filename}"
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique)
            avatar.save(save_path)
            g.user.avatar_filename = unique
        db.session.commit()
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
    bio = get_profile_bio(g.user.username)
    return render_template('settings.html', bio=bio)


@bp.route('/user/<username>')
def user(username):
    u = User.query.filter_by(username=username).first()
    if not u:
        flash('ユーザーが見つかりません')
        return redirect(url_for('main.index'))
    posts = Post.query.filter_by(user_id=u.id).order_by(Post.created_at.desc()).all()
    bio = get_profile_bio(u.username)
    return render_template('user.html', user=u, posts=posts, bio=bio)


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
        db.session.add(m)
        db.session.commit()
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
        db.session.add(m)
        db.session.commit()
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

    return render_template('messages.html', partners=partner_objs, other=other, messages_thread=thread)


@bp.route('/message/<int:msg_id>/delete', methods=['POST'])
def delete_message(msg_id):
    from urllib.parse import urlparse
    m = Message.query.get_or_404(msg_id)
    if not g.user or g.user.id != m.sender_id:
        flash('権限がありません')
        return redirect(url_for('main.messages'))
    db.session.delete(m)
    db.session.commit()
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
        messages_data.append({
            'id': m.id,
            'body': m.body,
            'sender_id': m.sender_id,
            'recipient_id': m.recipient_id,
            'created_at': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': m.is_read,
            'sender_avatar': m.sender.avatar_filename if m.sender else None,
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


@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
