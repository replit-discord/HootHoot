from models.base import Base, Column


class Mute(Base):
    target = Column("INTEGER")
    end_time = Column("INTEGER")
