import asyncio
from sqlalchemy import text
from app.db.session import engine

async def alter():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS detection_confidence FLOAT DEFAULT 0.45;"))
        await conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS model_variant VARCHAR(50) DEFAULT 'yolov8n';"))
        await conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS last_count INTEGER DEFAULT 0;"))
        await conn.execute(text("ALTER TABLE cameras ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP WITH TIME ZONE;"))
        print("Database patched successfully.")

if __name__ == "__main__":
    asyncio.run(alter())
