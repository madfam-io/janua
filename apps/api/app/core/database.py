from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
import structlog

# Import config with error handling
try:
    from app.config import settings
except Exception as e:
    print(f"Failed to import settings: {e}")
    raise

logger = structlog.get_logger()

# Database naming conventions
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
Base = declarative_base(metadata=metadata)

# Create async engine with error handling
try:
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured")
    
    # Auto-fix Railway PostgreSQL URL format for SQLAlchemy async
    if settings.DATABASE_URL.startswith('postgresql://'):
        database_url = settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
    else:
        database_url = settings.DATABASE_URL
    
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_pre_ping=True
    )
    
    # Create async session maker
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
except Exception as e:
    print(f"Failed to create database engine: {e}")
    print(f"DATABASE_URL: {getattr(settings, 'DATABASE_URL', 'NOT SET')}")
    raise


async def init_db():
    """Initialize database connection and create tables if needed"""
    try:
        async with engine.begin() as conn:
            if settings.AUTO_MIGRATE:
                await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()