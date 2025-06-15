import aiosqlite

DB_NAME = "kino_bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'uz',
                joined TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
      
        await db.execute("""
             CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_uz TEXT,
                description_uz TEXT,
                file_id TEXT,
                poster TEXT,
                video_type TEXT,
                genre TEXT,
                language TEXT DEFAULT 'uz',
                year INTEGER,
                duration INTEGER,
                rating REAL CHECK(rating >= 0 AND rating <= 10),
                added_by INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# --- Foydalanuvchi funksiyalari ---

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()

async def update_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (lang, user_id)
        )
        await db.commit()

async def get_language(user_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT language FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 'uz'

# --- Kino qo‘shish ---

async def add_movie(*, title_uz, description_uz, file_id, video_type=None, genre=None, year=None, duration=None, rating=None, added_by=None, poster=None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            INSERT INTO movies(title_uz, description_uz, file_id, poster,
                               video_type, genre, year, duration, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title_uz, description_uz, file_id, poster,
              video_type, genre, year, duration, rating))
        await db.commit()
        movie_id = cursor.lastrowid  # Shu yerda oxirgi qo‘shilgan kino ID sini olamiz
        return movie_id


# --- 🔍 Inline qidiruv ---

async def search_movies(text: str, lang: str):
    col  = f"title_{lang}" if lang in ("uz","ru","en") else "title_uz"
    desc = f"description_{lang}" if lang in ("uz","ru","en") else "description_uz"

    query = f"""SELECT id, {col} AS title, {desc} AS description,
                       year, rating, poster, file_id, genre
                FROM movies
                WHERE LOWER({col}) LIKE '%'||LOWER(?)||'%'
                LIMIT 50"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(query, (text,))

        return [
            {
                "id": row["id"],  # <- BU YANGI QATOR
                "title": row["title"],
                "description": row["description"],
                "year": row["year"],
                "rating": row["rating"],
                "poster": row["poster"],
                "file_id": row["file_id"],
            } for row in rows
        ]


async def get_movie_by_id(movie_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT id, title_uz, description_uz, file_id, video_type,
                   year, duration, rating, poster
            FROM movies WHERE id = ?
        """, (movie_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "title_uz": row[1],
                "description_uz": row[2],
                "file_id": row[3],
                "video_type": row[4],
                "year": row[5],
                "duration": row[6],
                "rating": row[7],
                "poster": row[8],
            }
        return None

# --- Statistika ---

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        movies = (await (await db.execute("SELECT COUNT(*) FROM movies")).fetchone())[0]
        return users, movies

async def get_total_users_count():
    async with aiosqlite.connect(DB_NAME) as db:
        row = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        return row[0] if row else 0

async def get_total_movies_count():
    async with aiosqlite.connect(DB_NAME) as db:
        row = await (await db.execute("SELECT COUNT(*) FROM movies")).fetchone()
        return row[0] if row else 0

async def get_all_users():
    async with aiosqlite.connect(DB_NAME) as db:
        rows = await (await db.execute("SELECT user_id FROM users")).fetchall()
        return [{"user_id": row[0]} for row in rows]

async def get_all_movies():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, title_uz FROM movies ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# delete_movie
async def delete_movie(movie_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        await db.commit()

# get_movie_by_id
async def get_movie_by_id(movie_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

# update_movie_title
async def update_movie_title(movie_id: int, new_title: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE movies SET title_uz = ? WHERE id = ?", (new_title, movie_id))
        await db.commit()
