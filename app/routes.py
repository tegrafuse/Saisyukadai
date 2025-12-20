import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models import User, Post, Message, Image, db

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
    images = Image.query.order_by(Image.created_at.desc()).all()
    return render_template('index.html', posts=posts, images=images)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('Username and password required')
            return redirect(url_for('main.register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('main.register'))
        u = User(username=username)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
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


@bp.route('/post', methods=['POST'])
def create_post():
    if not g.user:
        flash('Login required')
        return redirect(url_for('main.login'))
    body = request.form.get('body')
    if not body:
        flash('Body required')
        return redirect(url_for('main.index'))
    p = Post(body=body, user_id=g.user.id)
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
    p = Post.query.get_or_404(post_id)
    if not g.user or g.user.id != p.user_id:
        flash('Permission denied')
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        body = request.form.get('body')
        if not body:
            flash('Body required')
            return redirect(url_for('main.edit_post', post_id=post_id))
        p.body = body
        db.session.commit()
        flash('Updated.')
        return redirect(url_for('main.view_post', post_id=post_id))
    return render_template('edit_post.html', post=p)


@bp.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    p = Post.query.get_or_404(post_id)
    if not g.user or g.user.id != p.user_id:
        flash('Permission denied')
        return redirect(url_for('main.index'))
    db.session.delete(p)
    db.session.commit()
    flash('Deleted.')
    return redirect(url_for('main.index'))


# Messages
@bp.route('/messages', methods=['GET', 'POST'])
def messages():
    if not g.user:
        flash('Login required')
        return redirect(url_for('main.login'))
    if request.method == 'POST':
        body = request.form.get('body')
        recipient = request.form.get('recipient')
        recipient_user = User.query.filter_by(username=recipient).first() if recipient else None
        m = Message(body=body, sender_id=g.user.id, recipient_id=(recipient_user.id if recipient_user else None))
        db.session.add(m)
        db.session.commit()
        flash('Message sent.')
        return redirect(url_for('main.messages'))
    # show messages sent or received
    msgs = Message.query.filter((Message.sender_id == g.user.id) | (Message.recipient_id == g.user.id)).order_by(Message.created_at.desc()).all()
    # prepare user map for template
    users = {u.id: u.username for u in User.query.all()}
    return render_template('messages.html', messages=msgs, users=users)


@bp.route('/message/<int:msg_id>/delete', methods=['POST'])
def delete_message(msg_id):
    m = Message.query.get_or_404(msg_id)
    if not g.user or g.user.id != m.sender_id:
        flash('Permission denied')
        return redirect(url_for('main.messages'))
    db.session.delete(m)
    db.session.commit()
    flash('Message deleted')
    return redirect(url_for('main.messages'))


# Image upload
@bp.route('/upload_image', methods=['POST'])
def upload_image():
    if not g.user:
        flash('Login required')
        return redirect(url_for('main.login'))
    if 'image' not in request.files:
        flash('No file part')
        return redirect(url_for('main.index'))
    file = request.files['image']
    caption = request.form.get('caption')
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('main.index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        img = Image(filename=filename, caption=caption, user_id=g.user.id)
        db.session.add(img)
        db.session.commit()
        flash('Image uploaded')
        return redirect(url_for('main.index'))
    flash('Invalid file')
    return redirect(url_for('main.index'))


@bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@bp.route('/image/<int:image_id>/delete', methods=['POST'])
def delete_image(image_id):
    im = Image.query.get_or_404(image_id)
    if not g.user or g.user.id != im.user_id:
        flash('Permission denied')
        return redirect(url_for('main.index'))
    # remove file
    try:
        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], im.filename))
    except Exception:
        pass
    db.session.delete(im)
    db.session.commit()
    flash('Image deleted')
    return redirect(url_for('main.index'))
