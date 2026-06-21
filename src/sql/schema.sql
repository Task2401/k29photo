CREATE TABLE Users (
    user_id SERIAL PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    birth_date DATE,
    hometown VARCHAR(255),
    gender VARCHAR(10) CHECK (gender in ('male', 'female', 'other')),
    password VARCHAR(255) NOT NULL,
    CONSTRAINT check_birth_date CHECK ( birth_date <= CURRENT_DATE )
);

CREATE TABLE Friends (
  user_id1 INT NOT NULL,
  user_id2 INT NOT NULL,  
  PRIMARY KEY (user_id1, user_id2),
  FOREIGN KEY (user_id1) REFERENCES Users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id2) REFERENCES Users(user_id) ON DELETE CASCADE,
  CONSTRAINT user_cannot_friend_himself CHECK (user_id1 <> user_id2 )
);

CREATE TABLE Albums (
    album_id SERIAL PRIMARY KEY,
    album_name VARCHAR(255) NOT NULL,
    owner_id INT NOT NULL,
    creation_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (owner_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    CONSTRAINT check_creation_date CHECK (creation_date <= CURRENT_DATE)
);

CREATE TABLE Photos (
    photo_id SERIAL PRIMARY KEY,
    album_id INT NOT NULL,
    caption TEXT,
    data BYTEA NOT NULL,
    FOREIGN KEY (album_id) REFERENCES Albums(album_id) ON DELETE CASCADE
);

CREATE TABLE Tags (
    tag_id SERIAL PRIMARY KEY,
    tag_name VARCHAR(120) UNIQUE NOT NULL,
    CONSTRAINT no_spaces_on_tags CHECK (tag_name NOT LIKE '% %')
);

CREATE TABLE Photo_Has_Tags (
    photo_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (photo_id, tag_id),
    FOREIGN KEY (photo_id) REFERENCES Photos(photo_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES Tags(tag_id) ON DELETE CASCADE
);

CREATE TABLE Comments (
    comment_id SERIAL PRIMARY KEY,
    comment_content TEXT NOT NULL,
    comment_owner INT,
    guest_name VARCHAR(255),
    photo_id INT NOT NULL,
    comment_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (comment_owner) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (photo_id) REFERENCES Photos(photo_id) ON DELETE CASCADE,
    CONSTRAINT check_comment_length CHECK (char_length(comment_content) > 0),
    CONSTRAINT check_comment_crator CHECK (
        (comment_owner IS NOT NULL AND guest_name IS NULL) OR
        (comment_owner IS NULL AND guest_name IS NOT NULL)
    ) 
);

CREATE TABLE Likes (
    user_id INT NOT NULL,
    photo_id INT NOT NULL,
    PRIMARY KEY (user_id, photo_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (photo_id) REFERENCES Photos(photo_id) on DELETE CASCADE
);

CREATE OR REPLACE FUNCTION check_self_comment_func()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.comment_owner IS NOT NULL THEN
        IF EXISTS (
            SELECT *
            FROM Photos P
            JOIN Albums A ON P.album_id = A.album_id
            WHERE P.photo_id = NEW.photo_id
                AND A.owner_id = NEW.comment_owner
        ) THEN
            RAISE EXCEPTION 'A user cannot comment on their own photos.';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_self_comment_trigger
BEFORE INSERT ON Comments
FOR EACH ROW
EXECUTE FUNCTION check_self_comment_func();

CREATE OR REPLACE FUNCTION check_self_like_func()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT *
        FROM Photos P
        JOIN Albums A ON P.album_id = A.album_id
        WHERE P.photo_id = NEW.photo_id
            AND A.owner_id = NEW.user_id
    )THEN
        RAISE EXCEPTION 'A user cannot like their own photos.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_self_like_trigger
BEFORE INSERT ON Likes
FOR EACH ROW
EXECUTE FUNCTION check_self_like_func();