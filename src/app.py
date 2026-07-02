import psycopg2
import base64
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask application

app = Flask(__name__)
app.secret_key = 'k29photo_secret_key_2026'

# Database configuration credentials

DB_HOST = "Your_Host"
DB_NAME = "Your_DB_Name"
DB_USER = "Your_User_Name"
DB_PASS = "Your_PW"


# Establishes and returns a connection to the PostgreSQL database.

def get_db_connection():
    conn = psycopg2.connect(
        host = DB_HOST,
        database = DB_NAME,
        user = DB_USER,        
        password = DB_PASS,
    )
    return conn

# Configure Flask-Login manager

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class implementing Flask-Login UserMixin for session management
# Stores core profile attributes retrieved from the PostgreSQL 'Users' table

class User(UserMixin):
    def __init__(self, user_id, first_name, last_name, hometown, gender, birth_date):
        self.id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.hometown = hometown
        self.gender = gender
        self.birth_date = birth_date

# Loads a user from the database given their user ID.

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    cur.execute("SELECT user_id, first_name, last_name, hometown, gender, birth_date FROM Users WHERE user_id = %s", (int(user_id),))
    user_data = cur.fetchone()
    cur.close()
    conn.close()

    if user_data:
        return User(
            user_id=user_data['user_id'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            hometown=user_data['hometown'],
            gender=user_data['gender'],
            birth_date=user_data['birth_date']
        )

# Handles new user registration

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        hometown = request.form.get('hometown')
        gender = request.form.get('gender')
        birth_date = request.form.get('birth_date')
        
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
            if cur.fetchone():
                flash('Email already exists. Please choose another one','error')
                return redirect(url_for('register'))
            
            cur.execute("""
                INSERT INTO Users (email, password, first_name, last_name, hometown, gender, birth_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)       
            """,(email, hashed_password, first_name, last_name, hometown, gender, birth_date))

            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        
        except Exception as error:
            conn.rollback()
            flash(f'An error occured during registration: {str(error)}', 'error')
            return redirect(url_for('register'))
        
        finally:
            cur.close()
            conn.close()

    return render_template('auth.html', mode='register')

# Handles user login authentication

@app.route('/login', methods =['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        cur.execute("SELECT user_id, password FROM  Users WHERE email = %s", (email,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        if user_data and check_password_hash(user_data['password'], password):
            user_obj = load_user(user_data['user_id'])
            login_user(user_obj)

            flash('Logged in succesfully', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))
    
    return render_template('auth.html', mode='login')

# Logs out the current user and clears the session

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.' 'success')
    return redirect(url_for('login'))

# Renders the global homepage feed displaying all shared photographs, tags, and comments

@app.route("/")
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Fetch all photos along with metadata, total likes, accumulated tags, and listing of likers

    cur.execute("""
        SELECT P.photo_id, P.caption, P.data, A.album_id, A.album_name, U.first_name, U.last_name,
                U.user_id AS owner_id,
                (SELECT COUNT(*) FROM Likes L WHERE L.photo_id = P.photo_id) AS like_count,
                
                (SELECT string_agg(T.tag_name, ', ') 
                FROM Tags T, Photo_has_tags PHT 
                 WHERE T.tag_id = PHT.tag_id AND PHT.photo_id = P.photo_id) AS tags_string,
                 
                (SELECT string_agg(U_liker.first_name || ' ' || U_liker.last_name, ', ') 
                 FROM Likes L_join 
                 JOIN Users U_liker ON L_join.user_id = U_liker.user_id 
                 WHERE L_join.photo_id = P.photo_id) AS likers_string
                 
        FROM Photos P, Albums A, Users U
        WHERE P.album_id = A.album_id
                AND A.owner_id = U.user_id
        ORDER BY P.photo_id DESC;
    """)

    all_photos = cur.fetchall()
    photos = []

    # Iterate through photos to process binary image payloads and load corresponding comments

    for row in all_photos:
        photo_dict = dict(row)
        if photo_dict['data']:
            photo_dict['data'] = base64.b64encode(photo_dict['data']).decode('utf-8')
        photos.append(photo_dict)

    # Fetch all registered tags sorted by their usage count in descending order to find trending tags

    cur.execute("""
            SELECT T.tag_name, COUNT(PHT.photo_id) AS tag_count
            FROM Tags T, Photo_has_tags PHT
            WHERE T.tag_id = PHT.tag_id
            GROUP by T.tag_id, T.tag_name
            ORDER BY tag_count DESC
    """)

    popular_tags = cur.fetchall()

    # Calculate and fetch the top 10 users based on their contribution score (sum of uploaded photos and external comments)

    cur.execute("""
        SELECT U.user_id, U.first_name, U.last_name,
                ((SELECT COUNT(*)
                    FROM Photos P, Albums A
                    WHERE P.album_id = A.album_id
                        AND A.owner_id = U.user_id)
                +
                    (SELECT COUNT(*)
                        FROM Comments C, Photos P2, Albums A2
                        WHERE C.photo_id = P2.photo_id
                            AND P2.album_id = A2.album_id
                            AND C.comment_owner = U.user_id
                            AND A2.owner_id <> U.user_id)
                ) AS contribution_score
            FROM Users U
            ORDER BY contribution_score DESC;
    """)

    top_users = cur.fetchall()[:10]
    
    cur.close()
    conn.close()

    return render_template('index.html' , photos=photos, popular_tags=popular_tags, top_users=top_users)

# Filters the global homepage feed to present content bound to a selected collection album

@app.route("/album/<int:album_id>")
def view_album(album_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Fetch all photos belonging to this album, along with likes count and owner information

    cur.execute("SELECT album_name FROM Albums WHERE album_id = %s", (album_id,))
    album_row = cur.fetchone()
    album_name = album_row['album_name'] if album_row else "Unknown Album"

    cur.execute("""
        SELECT P.photo_id, P.caption, P.data, A.album_id, A.album_name, U.first_name, U.last_name,
                U.user_id AS owner_id,
                (SELECT COUNT (*) FROM Likes L WHERE L.photo_id = P.photo_id) AS like_count
        FROM Photos P, Albums A, Users U
        WHERE P.album_id = A.album_id
                AND A.owner_id = U.user_id
                AND A.album_id = %s
        ORDER BY P.photo_id DESC

    """, (album_id,))

    all_photos = cur.fetchall()
    photos = []

    # Process and encode binary photo payloads to base64 UTF-8 for template rendering

    for row in all_photos:
        photo_dict = dict(row)
        if photo_dict['data']:
            photo_dict['data'] = base64.b64encode(photo_dict['data']).decode('utf-8')
        photos.append(photo_dict)

    # Fetch the most popular tags in the system to populate the trending sidebar

    cur.execute("""
            SELECT T.tag_name, COUNT(PHT.photo_id) AS tag_count
            FROM Tags T, Photo_has_tags PHT
            WHERE T.tag_id = PHT.tag_id
            GROUP by T.tag_id, T.tag_name
            ORDER BY tag_count DESC
    """)

    popular_tags = cur.fetchall()

    # Calculate and fetch user leaderboard contribution rankings based on photos and comments

    cur.execute("""
        SELECT U.user_id, U.first_name, U.last_name,
                ((SELECT COUNT(*)
                    FROM Photos P, Albums A
                    WHERE P.album_id = A.album_id
                        AND A.owner_id = U.user_id)
                +
                    (SELECT COUNT(*)
                        FROM Comments C, Photos P2, Albums A2
                        WHERE C.photo_id = P2.photo_id
                            AND P2.album_id = A2.album_id
                            AND C.comment_owner = U.user_id
                            AND A2.owner_id <> U.user_id)
                ) AS contribution_score
            FROM Users U
            ORDER BY contribution_score DESC;
    """)

    top_users = cur.fetchall()[:10]
    
    cur.close()
    conn.close()

    return render_template('index.html' , photos=photos, popular_tags=popular_tags, top_users=top_users, album_id=album_id, album_name=album_name)

# Isolates a singular focus photograph entry to interact directly with historical text commentaries

@app.route("/photo/<int:photo_id>")
def view_photo(photo_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Fetch the main photo information, layout metadata, owner details, and total like count

    cur.execute("""
        SELECT P.photo_id, P.caption, P.data, A.album_id, A.album_name, U.first_name, U.last_name,
                U.user_id AS owner_id,
                (SELECT COUNT (*) FROM Likes L WHERE L.photo_id = P.photo_id) AS like_count
        FROM Photos P, Albums A, Users U
        WHERE P.album_id = A.album_id
                AND A.owner_id = U.user_id
                AND P.photo_id = %s;
    """, (photo_id,))

    row = cur.fetchone()

    photos = []
    if row:
        photo_dict = dict(row)
        if photo_dict['data']:
            photo_dict['data'] = base64.b64encode(photo_dict['data']).decode('utf-8')
        photos.append(photo_dict)

    # Fetch all corresponding comments for this specific photo, joining user data for registered members

    cur.execute("""
        SELECT C.comment_content, C.comment_date, C.guest_name, U.first_name, U.last_name
        FROM Comments C
        LEFT JOIN Users U On C.comment_owner = U.user_id
        WHERE C.photo_id = %s
        ORDER BY C.comment_date ASC
    """, (photo_id,))

    comments = cur.fetchall()

    # Fetch the most popular tags in the application to render in the trending sidebar slot

    cur.execute("""
            SELECT T.tag_name, COUNT(PHT.photo_id) AS tag_count
            FROM Tags T, Photo_has_tags PHT
            WHERE T.tag_id = PHT.tag_id
            GROUP by T.tag_id, T.tag_name
            ORDER BY tag_count DESC
    """)

    popular_tags = cur.fetchall()

    # Calculate and fetch the top users ordered by their global profile contribution score

    cur.execute("""
        SELECT U.user_id, U.first_name, U.last_name,
                ((SELECT COUNT(*)
                    FROM Photos P, Albums A
                    WHERE P.album_id = A.album_id
                        AND A.owner_id = U.user_id)
                +
                    (SELECT COUNT(*)
                        FROM Comments C, Photos P2, Albums A2
                        WHERE C.photo_id = P2.photo_id
                            AND P2.album_id = A2.album_id
                            AND C.comment_owner = U.user_id
                            AND A2.owner_id <> U.user_id)
                ) AS contribution_score
            FROM Users U
            ORDER BY contribution_score DESC;
    """)

    top_users = cur.fetchall()[:10]
    
    cur.close()
    conn.close()

    return render_template('index.html' , photos=photos, popular_tags=popular_tags, top_users=top_users, selected_photo_id=photo_id, comments=comments)

# Allows authenticated profile members to spawn empty photo showcase albums

@app.route('/create_album' , methods = ['POST', 'GET'])
@login_required
def create_album():

    # Check if the form has been submitted via a POST request

    if request.method == 'POST':
        album_name = request.form.get('album_name')
        
        # Validate that the album name field is not empty

        if not album_name:
            flash('Album name is required', 'error')
            return redirect(url_for('create_album'))
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        # Attempt to insert the new album record into the database mapping it to the current user

        try:
            cur.execute("INSERT INTO Albums (album_name, owner_id) VALUES (%s, %s)",(album_name, current_user.id))
            conn.commit()
            flash('Album created succesfully!', 'success')
            return redirect(url_for('profile'))
        
        # Roll back the database transaction in case an exception occurs during insertion

        except Exception as error:
            conn.rollback()
            flash(f'Error creating album: {str(error)}', 'error')
        
        # Ensure that database cursor and connection resources are always closed properly

        finally:
            cur.close()
            conn.close()

    # Render the album creation form page for GET requests

    return render_template('create_album.html')


# Deletes an entire collection album if executed by its authorized creator

@app.route('/delete_album/<int:album_id>', methods = ['POST'])
@login_required
def delete_album(album_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Fetch the owner_id of the target album to verify deletion permissions

    cur.execute("SELECT owner_id FROM Albums WHERE album_id = %s", (album_id,))
    album = cur.fetchone()

    # Check if the album exists and belongs to the currently authenticated user

    if album and album['owner_id'] == current_user.id:
        cur.execute("DELETE FROM Albums WHERE album_id = %s", (album_id,))
        conn.commit()
        flash('Album deleted succesfully' , 'success')
    
    # Flag an error if the user attempts to delete an album they do not own

    else:
        flash('You dont have permission to delete this album', 'error')

    cur.close()
    conn.close()
    return redirect(url_for('profile'))

# Processes newly uploaded files directly into database BYTEA structures mapping custom tag labels

@app.route('/upload', methods=['POST', 'GET'])
@login_required
def upload_photo():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Check if the form has been submitted via a POST request

    if request.method == 'POST':
        album_id = request.form.get('album_id')
        caption = request.form.get('caption')
        tags_input = request.form.get('tags')
        files = request.files.getlist('photos')

        # Validate that at least one file and a target album have been selected

        if not files or files[0].filename == '':
            flash('Please select at least one photo.', 'error')
            return redirect(request.url)
        if not album_id:
            flash('Please select an album', 'error')
            return redirect(request.url)

        try:

            # Iterate through all uploaded files to read their binary data and perform the database insertion

            for file in files:
                if file.filename != '':
                    photo_data = file.read()

                    cur.execute("""
                        INSERT INTO Photos (album_id, caption, data)
                        VALUES (%s, %s, %s) RETURNING photo_id
                    """, (album_id, caption, psycopg2.Binary(photo_data)))
                
                photo_id = cur.fetchone()['photo_id']

                # If tags are provided, split them by space and link them to the uploaded photo

                if tags_input:
                    tags = tags_input.strip().split()
                    for tag in tags:
                        tag_name = tag.strip()

                        # Insert new tags into the Tags table, ignoring duplicates using ON CONFLICT

                        if tag_name:
                            cur.execute("Insert Into Tags (tag_name) VALUES (%s) ON CONFLICT (tag_name) DO NOTHING;", (tag_name,))
                            cur.execute("SELECT tag_id FROM Tags WHERE tag_name = %s;", (tag_name,))
                            tag_row = cur.fetchone()
                            
                            # Map the relationship between the inserted photo and its tags

                            if tag_row:
                                tag_id = tag_row['tag_id']
                                cur.execute("INSERT INTO Photo_Has_Tags (photo_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (photo_id, tag_id))

            conn.commit()
            flash('Photos uploaded successfully!', 'success')
            return redirect(url_for('index'))
        
        # Roll back the active transaction if any database error occurs during the loop

        except Exception as error:
            conn.rollback()
            flash(f'Error uploading photos: {str(error)}', 'error')

    # Fetch all albums owned by the currently authenticated user to populate the form selection dropdown

    cur.execute("""
        SELECT album_id, album_name
        FROM Albums
        WHERE owner_id = %s;
    """, (current_user.id,))

    albums = cur.fetchall()

    cur.close()
    conn.close()

    # Capture any pre-selected album passed through the query parameters

    selected_album_id = request.args.get('album_id', type=int)

    return render_template('upload.html', albums=albums, selected_album_id=selected_album_id)


# Permanently drops target image items if launched by the proper album author resource

@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Resolve the owner of the album containing the target photograph to verify permissions

    cur.execute("""
        SELECT A.owner_id
        FROM Photos P, Albums A
        WHERE P.album_id = A.album_id
                AND P.photo_id = %s
    """, (photo_id,))
    
    result = cur.fetchone()

    # Check if the photograph exists and if the current user is the verified owner of the album

    if result and result['owner_id'] == current_user.id:
        cur.execute("""
            DELETE FROM Photos
            WHERE photo_id = %s;
        """, (photo_id,))

        conn.commit()
        flash('Photo deleted successfully', 'success')

    # Reject deletion if the authenticated user does not have owner permissions

    else:
        flash('You do not have permission to delete this photo', 'error')

    cur.close()
    conn.close()
    return redirect(url_for('index'))

# Registers written user or anonymous guest commentary text while verifying ownership rules

@app.route('/add_comment/<int:photo_id>', methods=['POST'])
def add_comment(photo_id):
    comment_content = request.form.get('comment_content', '').strip()

    # Check if the submitted comment content is empt

    if not comment_content:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Resolve owning author identifiers linked directly to target picture asset

    cur.execute("""
        SELECT A.owner_id
        FROM Photos P
        JOIN Albums A ON P.album_id = A.album_id
        WHERE P.photo_id = %s
    """, (photo_id,))
    photo = cur.fetchone()

    # Verify if the target photograph actually exists in the database

    if not photo:
        cur.close()
        conn.close()
        flash('Photo not found.', 'error')
        return redirect(url_for('index'))
    
    # Pre-emptively flag self-comments before hitting Postgres database trigger blocks

    if current_user.is_authenticated and photo['owner_id'] == current_user.id:
        cur.close()
        conn.close()
        flash('You cannot comment your own photos.', 'error')
        return redirect(url_for('index'))
    
    try:

        # Insert the comment mapping it to the user ID if authenticated, otherwise treat as a guest comment

        if current_user.is_authenticated:
            cur.execute("""
                INSERT INTO Comments (photo_id, comment_owner, comment_content, comment_date)
                VALUES (%s, %s, %s, CURRENT_DATE);
            """, (photo_id, current_user.id, comment_content))
        else:
            guest_name = request.form.get('guest_name', '').strip()
            if not guest_name:
                guest_name = 'Anonymus Guest'
            cur.execute("""
                INSERT INTO Comments (photo_id, comment_owner, guest_name, comment_content, comment_date)
                VALUES (%s, NULL, %s, %s, CURRENT_DATE);
            """, (photo_id, guest_name, comment_content))

        conn.commit()
        flash('Comment posted successfully!', 'success')
    
    # Handle database exceptions or trigger rollbacks safely

    except Exception as error:
        conn.rollback()
        flash(f'Error posting comment: {str(error)}', 'error')
    
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('index'))

# Applies a distinct user social like attribute entry tracking potential unique conflicts

@app.route('/like/<int:photo_id>')
@login_required
def like_photo(photo_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Check the Likes table to see if this user has already liked this specific photo

    cur.execute("SELECT * FROM Likes WHERE photo_id = %s AND user_id = %s;",(photo_id, current_user.id))
    existing_like = cur.fetchone()

    # If a record exists, notify the user that they cannot like the same photo again

    if existing_like:
        flash('You already liked this photo.' 'info')

    # Otherwise, attempt to insert the new like record into the database

    else:
        try:
            cur.execute("INSERT INTO Likes (photo_id, user_id) VALUES (%s, %s);", (photo_id, current_user.id))
            conn.commit()
            flash('You liked this photo!', 'success')

        # Roll back the transaction in case a database error or constraint violation occurs

        except Exception as error:
            conn.rollback()
            flash(f'Error liking photo: {str(error)}', 'error')

    cur.close()
    conn.close()

    return redirect(url_for('index'))

# Establishes bidirectional mapping logging unique peer tracking friendships

@app.route('/add_friend/<int:friend_id>', methods=['POST'])
@login_required
def add_friend(friend_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Check if a friendship records database entry already exists between these two users

    cur.execute("""
        SELECT * FROM Friends
        WHERE (user_id1 = %s AND user_id2 = %s) 
                OR (user_id1 = %s AND user_id2 = %s)
    """, (current_user.id, friend_id, friend_id,  current_user.id))

    existing_friendship = cur.fetchone()

    # If they are already friends, alert the user with an info flash message

    if existing_friendship:
        flash('You are already friend with this user!', 'info')

    # Otherwise, attempt to insert the new friendship relation into the database

    else:
        try:
            cur.execute("""
                INSERT INTO Friends (user_id1, user_id2)
                VALUES (%s, %s)
            """, (current_user.id, friend_id))
            
            conn.commit()
            flash('Friend added successfully', 'success')
        
        # Roll back the active transaction if any exception or failure occurs during execution

        except Exception as error:
            conn.rollback()
            flash(f'Error adding friend: {str(error)}', 'error')

    cur.close()
    conn.close()

    return redirect(request.referrer or url_for('profile'))

# Renders the global navigation text filters entry panel

@app.route('/search')
def search_page():
    return render_template('search.html', user=[], searched=False)

# Returns matched member name records matching exact wildcard filter conditions

@app.route('/search_users', methods=['GET'])
@login_required
def search_users():
    search_query = request.args.get('name', '')
    users = []

    # Check if a search term has been provided in the query parameters

    if search_query:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        # Execute a wild-card search query on the first_name or last_name fields, excluding the current user

        cur.execute("""
            SELECT Users.user_id, Users.first_name, Users.last_name
            FROM Users
            WHERE (Users.first_name LIKE %s OR Users.last_name LIKE %s)
                AND Users.user_id != %s
        """, (f"%{search_query}%", f"%{search_query}%", current_user.id))

        users = cur.fetchall()
        cur.close()
        conn.close()
    
    return render_template('search.html', users=users, searched=True)

# Isolates specific visual publications matching combinations of custom tags

@app.route('/search_tags', methods=['GET'])
def search_tags():
    search_query = request.args.get('tags', '').strip()
    scope = request.args.get('scope' , 'all')
    photos = []

    # Check if a search term containing tags has been provided

    if search_query:

        # Split the string by spaces to handle multiple tags simultaneously

        tags_list = search_query.split()
        format_strings = ','.join(['%s'] * len(tags_list))

        user_filter_sql = ""
        query_params = list(tags_list)

        # Apply an additional filter if the user requested to search only their own photos

        if scope == 'mine' and current_user.is_authenticated:
            user_filter_sql = "AND A.owner_id = %s"
            query_params.append(current_user.id)

        # Append the total number of distinct tags to ensure the photo matches ALL typed tags

        query_params.append(len(tags_list))

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        # Execute the retrieval query joining Photos, Albums, Users, and Tags tables

        cur.execute(f"""
            SELECT P.photo_id, P.caption, P.data, A.album_name, U.first_name, U.last_name, A.owner_id,
                   (SELECT COUNT(*) FROM Likes L WHERE L.photo_id = P.photo_id) AS like_count,
                   (SELECT string_agg(T2.tag_name, ', ') 
                    FROM Tags T2, Photo_has_tags PHT2 
                    WHERE T2.tag_id = PHT2.tag_id AND PHT2.photo_id = P.photo_id) AS tags_string
            FROM Photos P
            JOIN Albums A ON P.album_id = A.album_id
            JOIN Users U ON A.owner_id = U.user_id
            JOIN Photo_has_tags PHT ON P.photo_id = PHT.photo_id
            JOIN Tags T ON PHT.tag_id = T.tag_id
            WHERE T.tag_name IN ({format_strings}) {user_filter_sql}
            GROUP BY P.photo_id, A.album_name, U.first_name, U.last_name, A.owner_id
            HAVING COUNT(DISTINCT T.tag_name) = %s
            ORDER BY P.photo_id DESC;
        """, tuple(query_params))

        all_photos = cur.fetchall()

        # Iterate through the results to convert the binary image payload into a base64 string

        for row in all_photos:
            photo_dict = dict(row)
            if photo_dict['data']:
                photo_dict['data'] = base64.b64encode(photo_dict['data']).decode('utf-8')
            photos.append(photo_dict)

        cur.close()
        conn.close()

    # Render the search interface displaying the resulting photo cards

    return render_template('search.html', photos=photos, searched = True)

# Retrieves list of profiles grouped by total matched occurrences of target comment texts

@app.route('/search_comments', methods = ['GET'])
def search_comments():
    search_query = request.args.get('comment_text', '').strip()
    comment_users = []

    # Check if a comment text query has been provided in the search request

    if search_query:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=DictCursor)

        # Execute an aggregation query to count comment matches per user or guest name

        cur.execute("""
            SELECT
                COALESCE(U.first_name || ' ' || U.last_name, C.guest_name || ' (Guest)') AS commenter_name,
                COUNT(C.comment_id) AS match_count
            FROM Comments C
            LEFT JOIN Users U ON C.comment_owner = U.user_id
            WHERE C.comment_content LIKE %s
            GROUP BY commenter_name
            ORDER BY match_count DESC;
        """, (f"%{search_query}%",))

        comment_users = cur.fetchall()
        cur.close()
        conn.close()

    # Render the search results template with the compiled list of comment authors

    return render_template('search.html', comment_users=comment_users, comment_searched = True, comment_query=search_query)

# Generates personalized account dashboards collecting friends index list and graph recommendations

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    # Fetch all users who are friends with the currently authenticated user

    cur.execute("""
        SELECT Users.user_id, Users.first_name, Users.last_name
        FROM Friends, Users
        WHERE (Friends.user_id1 = %s AND Friends.user_id2 = Users.user_id)
                OR (Friends.user_id2 = %s AND Friends.user_id1 = Users.user_id );
    """, (current_user.id, current_user.id))

    friends = cur.fetchall()

    # Fetch all image albums created and owned by the currently authenticated user

    cur.execute("""
        SELECT Albums.album_id, Albums.album_name, Albums.creation_date
        FROM Albums
        WHERE Albums.owner_id = %s
    """, (current_user.id,))

    albums = cur.fetchall()

    # Formulate recursive graph intersection recommendations tracing overlapping friendship assets to find mutual connections

    cur.execute("""
        SELECT TargetUsers.user_id, TargetUsers.first_name, TargetUsers.last_name, COUNT(DISTINCT F2.friend_id) AS common_friends_count
        FROM Users TargetUsers,
             (SELECT user_id1 AS my_friend FROM Friends WHERE user_id2 = %s
              UNION
              SELECT user_id2 AS my_friend FROM Friends WHERE user_id1 = %s) AS F1,
             (SELECT user_id1 AS target, user_id2 AS friend_id FROM Friends
              UNION
              SELECT user_id2 AS target, user_id1 AS friend_id FROM Friends) AS F2
        
        WHERE F1.my_friend = F2.friend_id
          AND TargetUsers.user_id = F2.target
          AND TargetUsers.user_id != %s
          AND TargetUsers.user_id NOT IN (
              SELECT user_id1 FROM Friends WHERE user_id2 = %s
              UNION
              SELECT user_id2 FROM Friends WHERE user_id1 = %s
          )
        GROUP BY TargetUsers.user_id, TargetUsers.first_name, TargetUsers.last_name
        ORDER BY common_friends_count DESC;
    """, (current_user.id, current_user.id, current_user.id, current_user.id, current_user.id))

    recommendations = cur.fetchall()

    recommended_photos = []
    
    # Query the database to isolate and rank the current user's most frequently used tags

    cur.execute("""
        SELECT T.tag_id
        FROM Tags T
        JOIN Photo_Has_Tags PHT ON T.tag_id = PHT.tag_id
        JOIN Photos P ON PHT.photo_id = P.photo_id
        JOIN Albums A ON P.album_id = A.album_id
        WHERE A.owner_id = %s
        GROUP BY T.tag_id
        ORDER BY COUNT(PHT.photo_id) DESC;
    """, (current_user.id,))

    top_tags_result = cur.fetchall()

    # If the user has history with tags, fetch recommended external photos that share those top tags

    if top_tags_result:
        top_tag_ids = tuple([row['tag_id'] for row in top_tags_result])

        cur.execute("""
            SELECT P.photo_id, P.caption, P.data, U.first_name, U.last_name, A.album_name,
                COUNT(PHT1.tag_id) AS match_count,
                (SELECT COUNT(*) FROM Photo_has_tags PHT2 WHERE PHT2.photo_id = P.photo_id) AS total_tags,
                (SELECT string_agg(T_str.tag_name, ', ') 
                FROM Tags T_str 
                JOIN Photo_has_tags PHT3 ON T_str.tag_id = PHT3.tag_id 
                WHERE PHT3.photo_id = P.photo_id) AS tags_string
            FROM Photos P
            JOIN Albums A ON P.album_id = A.album_id
            JOIN Users U ON A.owner_id = U.user_id
            JOIN Photo_has_tags PHT1 ON P.photo_id = PHT1.photo_id
            WHERE PHT1.tag_id IN %s
                AND A.owner_id != %s
            GROUP BY P.photo_id, P.caption, P.data, U.first_name, U.last_name, A.album_name
            ORDER BY match_count DESC, total_tags ASC;
        """, (top_tag_ids, current_user.id))

        # Iterate through recommended photos to process binary data into base64 UTF-8 format

        all_recs = cur.fetchall()
        for row in all_recs:
            photo_dict = dict(row)
            if photo_dict:
                photo_dict['data'] = base64.b64encode(photo_dict['data']).decode('utf-8')
            recommended_photos.append(photo_dict)

    cur.close()
    conn.close()

    return render_template('profile.html', 
                           friends=friends, 
                           albums=albums, 
                           recommendations=recommendations, 
                           recommended_photos = recommended_photos)
        
# Initialize the Flask development server loop with active hot-reload monitoring

if __name__ == '__main__':
    app.run(debug=True)