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


@bp.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

# Posts
@bp.route('/post', methods=['POST'])
def create_post():
    if not g.user:
        flash('Login required')
        return redirect(url_for('main.login'))
    body = request.form.get('body')
    file = request.files.get('image')
    has_valid_image = bool(file and file.filename != '' and allowed_file(file.filename))
    if not body and not has_valid_image:
        flash('Body or image required')
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
            flash('Invalid file')
            return redirect(url_for('main.index'))

    db.session.add(p)
    db.session.commit()
    flash('Posted.')
    return redirect(url_for('main.index'))


@bp.route('/post/<int:post_id>')
def view_post(post_id):
    p = Post.query.get_or_404(post_id)
    return render_template('view_post.html', post=p)


@bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    # Editing posts is not supported in this app by design
    flash('Editing posts is not supported.')
    return redirect(url_for('main.view_post', post_id=post_id))


@bp.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    from urllib.parse import urlparse
    p = Post.query.get_or_404(post_id)
    if not g.user or g.user.id != p.user_id:
        flash('Permission denied')
        return redirect(url_for('main.index'))
    # remove attached image file
    if p.image_filename:
        try:
            os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], p.image_filename))
        except Exception:
            pass
    db.session.delete(p)
    db.session.commit()
    flash('Deleted.')
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
            flash('Username and password required')
            return redirect(url_for('main.register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
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
        flash('Registered and logged in.')
        return redirect(url_for('main.index'))
    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        u = User.query.filter_by(username=username).first()
        if not u or not u.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        session['user_id'] = u.id
        flash('Logged in.')
        return redirect(url_for('main.index'))
    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out.')
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
        flash('Settings updated.')
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
        flash('User not found')
        return redirect(url_for('main.index'))
    posts = Post.query.filter_by(user_id=u.id).order_by(Post.created_at.desc()).all()
    bio = get_profile_bio(u.username)
    return render_template('user.html', user=u, posts=posts, bio=bio)


@bp.route('/messages/<username>', methods=['GET', 'POST'])
def messages_with(username):
    if not g.user:
        flash('Login required')
        return redirect(url_for('main.login'))
    other = User.query.filter_by(username=username).first_or_404()
    if request.method == 'POST':
        body = request.form.get('body')
        if not body:
            flash('Body required')
            return redirect(url_for('main.messages_with', username=username))
        # prevent messaging yourself
        if other.id == g.user.id:
            flash('Cannot send message to yourself')
            return redirect(url_for('main.messages'))
        m = Message(body=body, sender_id=g.user.id, recipient_id=other.id)
        db.session.add(m)
        db.session.commit()
        flash('Message sent.')
        return redirect(url_for('main.messages_with', username=username))
    # conversation between g.user and other
    conv = Message.query.filter(
        ((Message.sender_id == g.user.id) & (Message.recipient_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.recipient_id == g.user.id))
    ).order_by(Message.created_at.asc()).all()
    return render_template('messages_thread.html', other=other, messages=conv)


# Messages
@bp.route('/messages', methods=['GET', 'POST'])
def messages():
    if not g.user:
        flash('Login required')
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        body = request.form.get('body')
        recipient = request.form.get('recipient')
        if not body:
            flash('Body required')
            return redirect(url_for('main.messages'))
        recipient_user = None
        if recipient:
            recipient_user = User.query.filter_by(username=recipient).first()
            if not recipient_user:
                flash('Recipient not found')
                return redirect(url_for('main.messages'))
            if recipient_user.id == g.user.id:
                flash('Cannot send message to yourself')
                return redirect(url_for('main.messages'))
        m = Message(body=body, sender_id=g.user.id, recipient_id=(recipient_user.id if recipient_user else None))
        db.session.add(m)
        db.session.commit()
        flash('Message sent.')
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
            partner_objs.append({'user': None, 'last': last_msg})
        else:
            u = User.query.get(k)
            partner_objs.append({'user': u, 'last': last_msg})

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

    return render_template('messages.html', partners=partner_objs, other=other, messages_thread=thread)


@bp.route('/message/<int:msg_id>/delete', methods=['POST'])
def delete_message(msg_id):
    from urllib.parse import urlparse
    m = Message.query.get_or_404(msg_id)
    if not g.user or g.user.id != m.sender_id:
        flash('Permission denied')
        return redirect(url_for('main.messages'))
    db.session.delete(m)
    db.session.commit()
    flash('Message deleted')
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


@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
