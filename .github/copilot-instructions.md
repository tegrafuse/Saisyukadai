# AI Coding Agent Instructions for SNS Demo

## Architecture Overview

This is a Flask-based SNS (social network service) application with a flat structure:
- **Core files at root**: `models.py` (SQLAlchemy models), `run.py` (entry point)
- **app/ directory**: Factory pattern with `__init__.py` (create_app) and `routes.py` (all view logic)
- **Flat templates/**: Project-level templates folder referenced via absolute path in `app/__init__.py`
- **instance/ directory**: SQLite database (`sns.db`) and user uploads (avatars, post images)
- **No migrations tool**: Schema changes require manual handling (see comment in `app/__init__.py`)

## Data Model & Relationships

Defined in [models.py](../models.py):
- `User`: username (unique), password_hash, display_name, avatar_filename
- `Post`: body, created_at, image_filename, user_id (FK)
- `Message`: body, created_at, sender_id (FK), recipient_id (FK, nullable)
- User relationships use explicit `foreign_keys` parameter: `sent_messages` and `received_messages`

## File Storage Pattern

**Profile bio workaround**: Uses `instance/profiles.json` instead of DB schema change
- Helper functions in [routes.py](../app/routes.py): `get_profile_bio()`, `set_profile_bio()`, `_read_profiles()`, `_write_profiles()`
- Normalizes "none"/"null" string values to `None`
- Automatically removes empty entries to prevent stale data

**Upload handling**:
- All files (avatars, post images) saved to `instance/uploads/` with UUID prefix
- Use `secure_filename()` + `uuid.uuid4().hex` pattern
- Allowed extensions: png, jpg, jpeg, gif (validated by `allowed_file()`)

## Critical Patterns

### Post Deletion Flow
- Remove attached `image_filename` from filesystem before DB delete
- Redirect back to caller using `request.form.get('next')` or `request.referrer` (with host validation)
- See [routes.py](../app/routes.py) `delete_post()` and `delete_message()` for reference

### Edit Restrictions
- `edit_post()` route intentionally returns flash message: "Editing posts is not supported"
- This is a **design decision**, not a missing feature

### Session Management
- Uses Flask session with `g.user` populated via `@bp.before_app_request`
- `load_logged_in_user()` queries User by `session['user_id']`

### Message Threading
- Messages page shows conversation partners with last message
- Thread view loads bilateral message history: `(sender=A & recipient=B) | (sender=B & recipient=A)`
- Self-messaging blocked in both `messages_with()` and `messages()` routes

## Development Workflow

**Start server**:
```bash
python run.py
# or use start_server.bat
```
Access at http://127.0.0.1:5000 (debug mode enabled in `run.py`)

**Database reset**: Delete `instance/sns.db` and restart - `db.create_all()` in `app/__init__.py` recreates tables

**Dependencies**: Flask 2.0+, Flask-SQLAlchemy 2.5+, Werkzeug 2.0+ (see [requirements.txt](../requirements.txt))

**No automated tests or build pipeline** - manual testing required

## Key Conventions

- **Japanese language UI**: Templates use Japanese text, Bootstrap 5.3.2 for styling
- **Blueprint naming**: Single blueprint `bp` registered as `'main'` namespace
- **Error handling**: Flash messages + redirect pattern (no JSON API)
- **Image display**: Use `url_for('main.uploaded_file', filename=...)` in templates
- **Password hashing**: Werkzeug's `generate_password_hash()` and `check_password_hash()`

## Directory References

- Templates: [templates/](../templates/) - base.html, index.html, messages.html, user.html, etc.
- Static assets: [static/css/styles.css](../static/css/styles.css), [static/js/post_preview.js](../static/js/post_preview.js)
- System diagram: [SystemDiagram/SystemDiagram.md](../SystemDiagram/SystemDiagram.md) (Mermaid graph)
