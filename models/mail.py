from models.base import Base, Column


class MailRoom(Base):
    user = Column("INTEGER", unique=True)
    channel = Column("INTEGER")
    date = Column("INTEGER")
    message = Column("TEXT")
