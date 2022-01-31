from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi import Query


class Intent(BaseModel):
    displayName: str


class Request(BaseModel):
    # format should be matched to fulfillment request from dialogflow
    intent: Intent
    queryText: str
    parameters: Dict[str, Any]


class Fulfillment(BaseModel):
    responseId: str
    queryResult: Request
    session: str


class User(BaseModel):
    name: str


# create natural language user query
class UserQuery(BaseModel):
    # q_id: int = None
    q: str = Query(None, min_length=1, max_length=100)


# session class which contains user, all query history, and elastic search output for all query history
class UserSession(BaseModel):
    # user_id: int
    query_history: List[UserQuery] = []
    es_output: list = []


# update user query for the further search
class UpdateUserQuery(BaseModel):
    q_id: Optional[int] = None
    q: Optional[str] = Query(None, min_length=1, max_length=100)


class FindCode(BaseModel):
    find: bool

