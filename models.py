from database import Base
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)


class UserQuery(Base):
    __tablename__ = "user query"
    q_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)  #Todo: change to foreign key
    q = Column(String)



class UserSession(Base):
    __tablename__ = "user session"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String)
    user_id = Column(Integer)  #Todo: change to foreign key
    response_id = Column(String)
    score = Column(Float)
    intent = Column(String)


