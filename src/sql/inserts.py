import psycopg2
from psycopg2.extras import DictCursor

DB_HOST = "Your_Host"
DB_NAME = "Your_DB_Name"
DB_USER = "Your_User_Name" 
DB_PASS = "Your_PW"

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,        
        password=DB_PASS
    )

def run_inserts():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    try:
        cur.execute("""
            INSERT INTO Users (user_id, first_name, last_name, email, birth_date, hometown, gender, password) VALUES
            (1, 'John', 'Smith', 'john.smith@example.com', '1995-05-12', 'New York', 'male', 'pbkdf2:sha256:260000$examplehash123'),
            (2, 'Emma', 'Watson', 'emma.w@example.com', '1998-08-24', 'London', 'female', 'pbkdf2:sha256:260000$examplehash456'),
            (3, 'Michael', 'Jordan', 'mj23@example.com', '1988-02-17', 'Chicago', 'male', 'pbkdf2:sha256:260000$examplehash789'),
            (4, 'Sophia', 'Miller', 'sophia.m@example.com', '2001-11-02', 'Los Angeles', 'female', 'pbkdf2:sha256:260000$examplehash012')
            ON CONFLICT (user_id) DO NOTHING;
        """)
        cur.execute("SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM Users));")

        cur.execute("""
            INSERT INTO Friends (user_id1, user_id2) VALUES
            (1, 2), (1, 3), (2, 4), (3, 4)
            ON CONFLICT DO NOTHING;
        """)

        cur.execute("""
            INSERT INTO Albums (album_id, album_name, owner_id, creation_date) VALUES
            (1, 'Epic Landscapes', 1, '2026-05-10'),
            (2, 'Nature Wanderlust', 2, '2026-05-15'),
            (3, 'Empty Adventure', 3, '2026-06-01')
            ON CONFLICT (album_id) DO NOTHING;
        """)
        cur.execute("SELECT setval('albums_album_id_seq', (SELECT MAX(album_id) FROM Albums));")

        # Καθαρά μονοπάτια χωρίς τελείες για να δουλεύει όταν το τρέχεις μέσα από το src
        images = [
            (1, 1, 'A breathtaking desert storm passing over the majestic monolithic peak at sunset.', 'src/static/img/photo1.png'),
            (2, 1, 'Golden sunbeams piercing through the valley over a wild rocky riverbed.', 'src/static/img/photo2.png'),
            (3, 2, 'Perfect symmetry. Crystal clear river reflecting the snow-capped mountain peaks.', 'src/static/img/photo3.png'),
            (4, 2, 'A solitary pine tree standing proud on a frost-covered hill above the sea of clouds.', 'src/static/img/photo4.png')
        ]

        for photo_id, album_id, caption, img_path in images:
            try:
                with open(img_path, "rb") as image_file:
                    binary_data = image_file.read()
                
                cur.execute("""
                    INSERT INTO Photos (photo_id, album_id, caption, data)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (photo_id) DO NOTHING;
                """, (photo_id, album_id, caption, psycopg2.Binary(binary_data)))
            except FileNotFoundError:
                print(f"File not found: {img_path}")
                continue

        cur.execute("SELECT setval('photos_photo_id_seq', (SELECT MAX(photo_id) FROM Photos));")

        tags = ['desert', 'storm', 'epic', 'sunset', 'river', 'sunrays', 'mountains', 'reflection', 'winter', 'frost', 'clouds', 'nature']
        for tag in tags:
            cur.execute("INSERT INTO Tags (tag_name) VALUES (%s) ON CONFLICT (tag_name) DO NOTHING;", (tag,))

        photo_tags = [
            (1, 'desert'), (1, 'storm'), (1, 'epic'), (1, 'sunset'),
            (2, 'river'), (2, 'sunrays'), (2, 'nature'),
            (3, 'mountains'), (3, 'reflection'), (3, 'nature'),
            (4, 'winter'), (4, 'frost'), (4, 'clouds')
        ]
        for photo_id, tag_name in photo_tags:
            cur.execute("SELECT tag_id FROM Tags WHERE tag_name = %s;", (tag_name,))
            tag_row = cur.fetchone()
            if tag_row:
                cur.execute("""
                    INSERT INTO Photo_Has_Tags (photo_id, tag_id)
                    VALUES (%s, %s) ON CONFLICT DO NOTHING;
                """, (photo_id, tag_row['tag_id']))

        cur.execute("""
            INSERT INTO Comments (comment_content, comment_owner, guest_name, photo_id, comment_date) VALUES
            ('Wow, the lighting in this storm is absolutely unreal!', 2, NULL, 1, '2026-05-11'),
            ('This looks like a movie poster. Incredible shot John!', 3, NULL, 1, '2026-05-12'),
            ('Stunning composition! I love the contrast.', NULL, 'AdventureTraveler', 1, '2026-05-12'),
            ('Those sunrays are hitting perfectly!', 4, NULL, 2, '2026-05-16'),
            ('The reflection is as sharp as a mirror. Fantastic job Emma!', 1, NULL, 3, '2026-05-17'),
            ('I want to camp right there! Magnificent view.', NULL, 'WildernessFan', 3, '2026-05-18'),
            ('Brrr, feels freezing just looking at it. Beautiful minimalism.', 3, NULL, 4, '2026-05-20')
            ON CONFLICT DO NOTHING;
        """)

        cur.execute("""
            INSERT INTO Likes (user_id, photo_id) VALUES
            (2, 1), (3, 1), (4, 1),
            (3, 2), (4, 2),
            (1, 3), (4, 3),
            (1, 4)
            ON CONFLICT DO NOTHING;
        """)

        conn.commit()
        print("Success: Database populated.")

    except Exception as db_error:
        conn.rollback()
        print(f"Error: {db_error}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_inserts()