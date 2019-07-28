from models.base import Base, Column


class Infraction(Base):
    user = Column("INTEGER")
    type = Column("TEXT")
    reason = Column("TEXT", optional=True)
    moderator = Column("INTEGER")
    date = Column("INTEGER")
