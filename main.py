import os
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pymongo import MongoClient
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ==========================================
# CONFIGURATIONS
# ==========================================
BOT_TOKEN = "8820885916:AAHOQXbhi4mrs_f-LrlO_6DXs7xRzksBEXk" # আপনার বট টোকেন
MONGO_URI = "mongodb+srv://airdroptimer:sakib72542@movieboxpro.mi2hrkd.mongodb.net/?appName=movieboxpro" # আপনার MongoDB URI
BASE_URL = "https://movieboxstream.onrender.com" # আপনার Render URL
ADMIN_ID = 5169962212  # আপনার Telegram User ID

# আপনার প্রাইভেট চ্যানেলের আইডি (উদাহরণ: -1001234567890)
CHANNEL_ID = -1003573920353 

# Database Setup
client = MongoClient(MONGO_URI)
db = client["MovieBoxBD"]
movies_collection = db["movies"]

# ==========================================
# HTML/CSS/JS TEMPLATES
# ==========================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MovieBoxBD - {PAGE_TITLE}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #141414;
            --card-bg: #1f1f1f;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-color: #e50914;
            --btn-hover: #f40612;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }}
        body {{ background-color: var(--bg-color); color: var(--text-primary); min-height: 100vh; }}
        .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
        .navbar {{ display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-bottom: 1px solid #333; margin-bottom: 40px; }}
        .logo {{ font-size: 28px; font-weight: 800; color: var(--accent-color); letter-spacing: -1px; }}
        .movie-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }}
        .movie-card {{ background: var(--card-bg); border-radius: 8px; overflow: hidden; transition: transform 0.3s; cursor: pointer; }}
        .movie-card:hover {{ transform: scale(1.05); }}
        .movie-poster {{ width: 100%; height: 300px; background: linear-gradient(45deg, #333, #111); display: flex; align-items: center; justify-content: center; font-size: 40px; }}
        .movie-info {{ padding: 15px; }}
        .movie-info h3 {{ font-size: 16px; margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .movie-info p {{ font-size: 13px; color: var(--text-secondary); }}
        .hero-section {{ text-align: center; margin-bottom: 40px; }}
        .hero-section h1 {{ font-size: 2.5rem; margin-bottom: 10px; word-wrap: break-word; }}
        .meta-tags {{ display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; color: var(--text-secondary); font-size: 15px; margin-bottom: 30px; }}
        .meta-tags span {{ background: #333; padding: 5px 12px; border-radius: 20px; }}
        .btn-group {{ display: flex; flex-direction: column; gap: 15px; max-width: 500px; margin: 0 auto; }}
        .btn {{ display: flex; align-items: center; justify-content: center; gap: 10px; padding: 18px; font-size: 18px; font-weight: 600; border: none; border-radius: 8px; cursor: pointer; text-decoration: none; transition: 0.3s; }}
        .btn-watch {{ background-color: var(--accent-color); color: white; }}
        .btn-watch:hover {{ background-color: var(--btn-hover); }}
        .ad-container {{ margin: 40px 0; text-align: center; min-height: 100px; background: #1a1a1a; display: flex; align-items: center; justify-content: center; color: #444; border: 1px dashed #333; }}
    </style>
</head>
<body>
    <div class="container">
        <nav class="navbar"><div class="logo">MovieBoxBD</div></nav>
        {CONTENT}
        <div class="ad-container">Advertisement Space</div>
    </div>
    <script>
        window.onload = function() {{
            var script = document.createElement('script');
            script.src = 'https://pl21423250.effectivecpmnetwork.com/1d/c3/f8/1dc3f8acdb14ff956d47dfdf409aaeeb.js';
            script.async = true;
            document.head.appendChild(script);
        }};
    </script>
</body>
</html>
"""

def get_home_html(movies):
    if not movies:
        content = "<h2 style='text-align:center; margin-top:50px;'>No movies uploaded yet.</h2>"
    else:
        cards = ""
        for m in movies:
            cards += f"""
            <a href="/m/{m['slug']}" style="text-decoration: none; color: inherit;">
                <div class="movie-card">
                    <div class="movie-poster">🎬</div>
                    <div class="movie-info">
                        <h3>{m['title']}</h3>
                        <p>{m['size']}</p>
                    </div>
                </div>
            </a>"""
        content = f"<div class='movie-grid'>{cards}</div>"
    return BASE_HTML.replace("{PAGE_TITLE}", "Home").replace("{CONTENT}", content)

def get_movie_html(movie):
    title = movie.get('title', 'Untitled')
    size = movie.get('size', 'Unknown Size')
    watch_url = f"{BASE_URL}/watch/{movie['slug']}"
    
    content = f"""
    <div class="hero-section">
        <h1>{title}</h1>
        <div class="meta-tags"><span>📦 {size}</span></div>
    </div>
    <div class="btn-group">
        <a href="{watch_url}" class="btn btn-watch">▶️ Watch Online / Download</a>
    </div>"""
    return BASE_HTML.replace("{PAGE_TITLE}", title).replace("{CONTENT}", content)

# ==========================================
# FASTAPI WEB SERVER
# ==========================================
app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    movies = list(movies_collection.find().sort("_id", -1).limit(20))
    return get_home_html(movies)

@app.get("/m/{slug}", response_class=HTMLResponse)
async def movie_details(slug: str):
    movie = movies_collection.find_one({"slug": slug})
    if not movie: return "<h1>Movie Not Found</h1>"
    return get_movie_html(movie)

@app.get("/watch/{slug}")
async def watch_movie(slug: str):
    movie = movies_collection.find_one({"slug": slug})
    if not movie or "channel_link" not in movie:
        return HTMLResponse("<h1>Movie Not Found</h1>")
    return RedirectResponse(url=movie["channel_link"])

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    await application.process_update(Update.de_json(data, application.bot))
    return {"status": "ok"}

# ==========================================
# TELEGRAM BOT LOGIC
# ==========================================
application = Application.builder().token(BOT_TOKEN).updater(None).build()

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("⚠️ Unauthorized Access!")

    file = update.message.document or update.message.video
    if not file:
        return await update.message.reply_text("⚠️ এটি একটি ভিডিও ফাইল নয়।")

    await update.message.reply_text("⏳ ফাইল প্রসেস হচ্ছে এবং চ্যানেলে আপলোড করা হচ্ছে... অনুগ্রহ করে অপেক্ষা করুন।")
    
    try:
        slug = str(uuid.uuid4())[:8]
        size_mb = round(file.file_size / (1024 * 1024), 2)
        file_name = file.file_name if file.file_name else "Untitled Movie"
        title = os.path.splitext(file_name)[0]

        msg = await context.bot.send_document(
            chat_id=CHANNEL_ID, 
            document=file.file_id,
            caption=f"🎬 {title}\n📦 Size: {size_mb} MB\n🌐 MovieBoxBD"
        )

        channel_link = f"https://t.me/c/{str(CHANNEL_ID).replace('-100', '')}/{msg.message_id}"

        movies_collection.insert_one({
            "slug": slug,
            "title": title,
            "size": f"{size_mb} MB",
            "channel_link": channel_link
        })

        link = f"{BASE_URL}/m/{slug}"
        
        # ERROR FIX: Markdown এর বদলে HTML ব্যবহার করা হয়েছে
        await update.message.reply_text(
            f"🎉 <b>সফলভাবে আপলোড হয়েছে!</b>\n\n"
            f"📎 <b>নাম:</b> {title}\n"
            f"📦 <b>সাইজ:</b> {size_mb} MB\n\n"
            f"🔗 <b>Public Link:</b>\n{link}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ এরর হয়েছে: {str(e)}\n\nবটকে কি চ্যানেলে অ্যাডমিন করা হয়েছে?")

application.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO, handle_file))

@app.on_event("startup")
async def startup_event():
    await application.initialize()
    await application.bot.set_webhook(url=f"{BASE_URL}/webhook")
    print("✅ Bot Webhook Set & Channel Storage Active!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
