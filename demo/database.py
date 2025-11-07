from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import Column, String, Text, create_engine, select
from .config import settings
from .services.authorization_service import authz_service

# Create sync engine
engine = create_engine(settings.database_url)

# Create sync session factory
Session = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, index=True)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    organization_id = Column(String, nullable=False, index=True)


# Database initialization
def init_db():
    Base.metadata.create_all(engine)

    with Session() as session:
        existing_org_query = session.execute(
            select(Organization).where(Organization.id == "acme")
        )
        existing_org = existing_org_query.scalars().first()

        if not existing_org:
            session.add(Organization(id="acme"))

    authz_service.assign_user_to_organization("alice", "acme", "admin")

    authz_service.assign_user_to_organization("bob", "acme", "member")
