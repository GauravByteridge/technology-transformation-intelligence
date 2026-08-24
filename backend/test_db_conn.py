import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

async def test():
    engine = create_async_engine("postgresql+asyncpg://postgres:master@localhost:5432/app_db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Try a simple query first
            result = await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=5)
            print(f"Simple query OK: {result.scalar()}")
            
            # Now try what the endpoint does
            from app.models.health_kpi import ProjectHealthKpi
            stmt = select(ProjectHealthKpi)
            result = await asyncio.wait_for(session.execute(stmt), timeout=5)
            rows = list(result.scalars().all())
            print(f"Health KPI query returned {len(rows)} rows")
    except asyncio.TimeoutError:
        print("ERROR: Query timed out after 5 seconds")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
    finally:
        await engine.dispose()

asyncio.run(test())
