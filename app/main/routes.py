from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app
from flask_login import current_user, login_required
from PIL import Image
from app import db
from app.models import User, Post, Activity, Event
from app.main.forms import EditProfileForm, PostForm, ActivityForm
from flask_babel import _, get_locale
from flask_babel import lazy_gettext as _l
from googletrans import Translator
from app.translate import translate
from app.main import bp
from app.main.forms import MessageForm
from app.models import Message, Notification
import os
from flask import send_from_directory
import secrets
from json import dumps


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        transt = Translator()
        language = transt.detect(form.post.data).lang
        if language == "UNKNOWN" or len(language) > 5:
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_l('Your post is now live!'))
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join('static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    image_file = url_for('static', filename='profile_pics/'+current_user.image_file)
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items, image_file=image_file,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_l('You cannot follow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are following %(username)s!', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_l('You cannot unfollow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are not following %(username)s.', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_popup.html', user=user)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    }for n in notifications])


def del_old_picture(user):
    picture_path = os.path.join(current_app.config['BASEDIR'], 'app', 'static', 'profile_pics', user)
    print(picture_path)
    os.remove(picture_path)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join('.', current_app.config['BASEDIR'], 'app', 'static', 'profile_pics', picture_fn)
    output_size = (200, 200)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        if form.picture.data:
            if current_user.image_file != 'default.jpg':
                del_old_picture(current_user.image_file)
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_l('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('edit_profile.html', title='Edit Profile',
                           image_file=image_file, form=form)


@bp.route('/todolist', methods=['GET', 'POST'])
@login_required
def todolist():
    form = ActivityForm()
    if form.validate_on_submit():
        activity = Activity(body=form.activity.data, author=current_user)
        db.session.add(activity)
        db.session.commit()
        flash(_l('Your activity is now live!'))
        return redirect(url_for('main.todolist'))
    page = request.args.get('page', 1, type=int)
    cases = current_user.followed_activity().paginate(
        page, 10, False)
    
    
    next_url = url_for('main.todolist', page=cases.next_num) \
        if cases.has_next else None
    prev_url = url_for('main.todolist', page=cases.prev_num) \
        if cases.has_prev else None
    return render_template('todolist.html', title='Todo list', form=form,
                           activity=cases.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/complete', methods=['POST'])
@login_required
def complete():
    case_id = request.form['case_id']
    case = Activity.query.filter_by(id=case_id).first()
    case.complete = not case.complete
    db.session.commit()
    return redirect(url_for('main.todolist'))


@bp.route('/delete_case', methods=['POST'])
@login_required
def delete_case():
    case_id = request.form['case_id']
    Activity.query.filter_by(id=case_id).delete()
    db.session.commit()
    return redirect(url_for('main.todolist'))


@bp.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html', title='Calendar')

@bp.route('/data')
@login_required
def return_data():

    events = current_user.followed_events()
    l = []
    for i in events:
        l.append({"id": i.id, "title": i.title, "start": i.start, "end":i.end, "color": i.color, "allDay": i.allDay, "url": i.url})
    return dumps(l)


@bp.route('/calendar_add', methods=['POST'])
@login_required
def calendar_add():
    title = request.form['title']
    start = request.form['start']
    end = request.form['end']
    color = request.form['color']
    url = request.form['url']
    if url!="":
        url = "http://" + url
    allDay = bool(int(request.form['allDay']))
    event = Event(title=title, author=current_user, start=start, end=end, color=color, allDay=allDay, url=url)
    db.session.add(event)
    db.session.commit()
    # flash(_l('Your event is now live!'))
    return jsonify(id=event.id)

@bp.route('/calendar_delete', methods=['POST'])
@login_required
def calendar_delete():
    event_id = request.form['id']
    Event.query.filter_by(id=event_id).delete()
    db.session.commit()
    return jsonify(success=True)

@bp.route('/calendar_delete_all', methods=['POST'])
@login_required
def calendar_delete_all():
    # event_id = request.form['id']
    # # print(event_id
    Event.query.filter_by(author=current_user).delete()
    db.session.commit()
    return jsonify(success=True)

@bp.route('/countdown')
def countdown():
    return render_template('countdown.html')
