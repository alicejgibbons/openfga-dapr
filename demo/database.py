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


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, default="member")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True, index=True)
    resource_type = Column(String, nullable=False)
    organization_id = Column(String, nullable=False, index=True)


# Database initialization
def init_db():
    Base.metadata.create_all(engine)

    with Session() as session:
        session.merge(Organization(id="kubecon"))
        session.merge(TeamMember(id="alice", organization_id="kubecon", role="admin"))
        session.merge(TeamMember(id="bob", organization_id="kubecon", role="member"))
        session.merge(
            Resource(id="report.pdf", resource_type="file", organization_id="kubecon")
        )
        session.commit()

    authz_service.assign_user_to_organization("alice", "kubecon", "admin")
    authz_service.assign_user_to_organization("bob", "kubecon", "member")
    authz_service.assign_resource_to_organization("report.pdf", "kubecon")
