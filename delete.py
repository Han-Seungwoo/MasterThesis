import uvicorn, schemas, models
from elasticsearch import Elasticsearch
from typing import Optional, List
from fastapi import FastAPI, Query, Depends, Response, HTTPException, status, Body
from pydantic import BaseModel, validator
from database import engine, SessionLocal
from sqlalchemy.orm import Session

# give_answer intent fulfillment
@app.post("/")
async def create_user_query(body: schemas.Fulfillment,   # must use body for the variable name.
                            db: Session = Depends(get_db)):

    # update the threshold from database
    if db.query(models.UserSession.score).filter(models.UserSession.intent == "satisfy").count() > 0:
        min_score = db.query(func.min(models.UserSession.score)).filter(models.UserSession.intent == "satisfy").first()
    else:
        min_score = []

    # set threshold according to user satisfication
    # we need to increase threshold not to fast
    threshold = 10 if not min_score else 10 + 0.1*min_score[0]

    # get intent for dialogflow
    intent = body.queryResult.intent.displayName
    query_from_user = body.queryResult.queryText

    response_id = body.responseId
    session_id = body.session

    # add new query and score to database userQuery
    new_query = models.UserQuery(q = query_from_user)
    db.add(new_query)
    db.commit()
    db.refresh(new_query)

    # elasticsearch part
    code_example, score, id_selected, total_hit = read_user_query(query_from_user)

    if intent == "give_answer" or intent == "extend":

        while score < threshold:
            # add response_id, session_id, score to the database userSeeion
            new_session = models.UserSession(response_id=response_id, session_id=session_id, score=score,
                                             intent="not satisfy")
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            return {
                "fulfillmentMessages": [
                    {
                        "quickReplies": {
                            "title": f"I need more information. Total hit {total_hit}"
                                     f"\n \nPlease start with 'Add: blabla'",
                            # "quickReplies": [
                            #     "Add more",
                            #     "End"
                            # ]
                        },
                        "platform": "TELEGRAM"
                    }
                ]
            }

        if score >= threshold:
            # add response_id, session_id, score to the database userSeeion
            new_session = models.UserSession(response_id=response_id, session_id=session_id, score=score,
                                             intent="not satisfy")
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            return {
                # "fulfillmentText": text,
                "fulfillmentMessages": [
                    {
                        "quickReplies": {
                            "title": f"Here is what I found for you from your query{query_from_user}!"
                                     f"\n-------------------------"
                                     f" \n \n{code_example}. "
                                     f"\n \nscore {score}."
                                     f"\n \nTotal hit {total_hit}."
                                     f"\n \nthreshold {threshold}. \n-------------------------"
                                     f"\n \nLike this answer? Choose one below👇",
                            "quickReplies": [
                                "Yes",
                                "No"
                            ]
                        },
                        "platform": "TELEGRAM"
                    }
                    ]
                }

    # add_info intent case: new query is automatically updated
    if intent == "add_info":
        query_from_user = body.queryResult.queryText
        query_id = body.responseId
        session_id = body.session

        code_example, score, id_selected, total_hit = read_filter_query(query_from_user, id_selected)

        while score < threshold:
            # add response_id, session_id, score to the database userSeeion
            new_session = models.UserSession(response_id=response_id, session_id=session_id, score=score,
                                             intent="not satisfy")
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            return {
                "fulfillmentMessages": [
                    {
                        "quickReplies": {
                            "title": f"I need more information. \n \nTotal hit {total_hit}."
                                     f"\n \nPlease start with 'Add: how to'",
                            # "quickReplies": [
                            #     "Add more",
                            #     "End"
                            # ]
                        },
                        "platform": "TELEGRAM"
                    }
                ]
            }

        if score >= threshold:
            # add response_id, session_id, score to the database userSeeion
            new_session = models.UserSession(response_id=response_id, session_id=session_id, score=score,
                                             intent="not satisfy")
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            return {
                "fulfillmentMessages": [
                    {
                        "quickReplies": {
                                "title": f"Here is what I found for you from your query{query_from_user}!"
                                         f"\n-------------------------"
                                         f" \n \n{code_example}. "
                                         f"\n \nscore {score}."
                                         f"\n \nTotal hit {total_hit}."
                                         f"\n \nthreshold {threshold}. \n-------------------------"
                                         f"\n \nLike this answer? Choose one belbow👇",
                                "quickReplies": [
                                    "Yes",
                                    "No"
                                ]
                            },
                        "platform": "TELEGRAM"
                    }
                ]
            }

    if intent == "not_satisfy":
        return {
            "fulfillmentMessages": [
                {
                    "quickReplies": {
                        "title": f"I need more information."
                                 f"\n \nPlease start with 'New: blabla'",
                        # "quickReplies": [
                        #     "Add more",
                        #     "End"
                        # ]
                    },
                    "platform": "TELEGRAM"
                }
            ]
        }

    if intent == "satisfy":
        #change right above intent to satisfy
        # select last row in db
        last_row = db.query(models.UserSession).order_by(models.UserSession.id.desc()).first()

        # set intent to satisfy
        last_row.intent = "satisfy"
        db.commit()


        return {
            "fulfillmentMessages": [
                {
                    "quickReplies": {
                        "title": "Great to hear that!",
                        # "quickReplies": [
                        #     "Add more",
                        #     "End"
                        # ]
                    },
                    "platform": "TELEGRAM"
                }
            ]
        }


@app.post("/")
async def create_user_query(body: schemas.Fulfillment,   # must use body for the variable name.
                            db: Session = Depends(get_db)):

    # get intent for dialogflow
    intent = body.queryResult.intent.displayName
    query_from_user = body.queryResult.queryText

    query_id = body.responseId
    session_id = body.session

    # add query to our database
    new_query = models.UserQuery(q = query_from_user)
    db.add(new_query)
    db.commit()
    db.refresh(new_query)

    # elasticsearch part
    code_example, score = read_user_query(query_from_user)

    if intent == "give_answer":
        return {
            # "fulfillmentText": text,
            "fulfillmentMessages": [
                {
                    "quickReplies": {
                        "title": f"Here is what I found for you!\n-------------------------"
                                 f" \n \n{code_example}. "
                                 f"\n \nscore {score}. \n-------------------------"
                                 f"\n \nquery_id {query_id}. \n-------------------------"
                                 f"\n \nsession_id {session_id}. \n-------------------------"
                                 f"\n \nLike this answer? Choose one belbow👇",
                        "quickReplies": [
                            "Yes",
                            "No"
                        ]
                    },
                    "platform": "TELEGRAM"
                }
                ]
            }


@app.post("/")
async def create_user_query(queryResult: schemas.Request = Body(..., embed=True),
                            db: Session = Depends(get_db)):

    # get intent for dialogflow
    intent = queryResult.intent.displayName
    query_from_user = queryResult.queryText


{
  "responseId": "14839f64-b4c9-4750-9629-bbbf19cb16eb-b9889856",
  "queryResult": {
    "queryText": "how to make",
    "parameters": {},
    "allRequiredParamsPresent": true,
    "fulfillmentMessages": [
      {
        "text": {
          "text": [
            ""
          ]
        }
      }
    ],
    "outputContexts": [
      {
        "name": "projects/codex-n9aw/agent/sessions/50e4782c-4980-cdbd-a178-00329145388a/contexts/__system_counters__",
        "lifespanCount": 1,
        "parameters": {
          "no-input": 0,
          "no-match": 0
        }
      }
    ],
    "intent": {
      "name": "projects/codex-n9aw/agent/intents/af8de522-b5eb-48a0-a365-e55ccc53f4de",
      "displayName": "give_answer"
    },
    "intentDetectionConfidence": 0.55341816,
    "languageCode": "en"
  },
  "originalDetectIntentRequest": {
    "source": "DIALOGFLOW_CONSOLE",
    "payload": {}
  },
  "session": "projects/codex-n9aw/agent/sessions/50e4782c-4980-cdbd-a178-00329145388a"
}


models.Base.metadata.create_all(bind=engine)

es = Elasticsearch()
app = FastAPI()

# dictionary {user_id: UserQuery}
user_query = {}

# id from the search result
id_selected = []

# all session created
sessions = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/user")
def create_user(request: schemas.User, db: Session = Depends(get_db)):
    new_user = models.User(name = request.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# create session with db
@app.post("/session")
def create_session(request: schemas.UserSession, db: Session = Depends(get_db)):
    new_session = models.UserSession()
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


# create user query with db
@app.post("/user-query")
def create_user_query(request: schemas.UserQuery, db: Session = Depends(get_db)):
    # add query to our database
    new_query = models.UserQuery(q = request.q)
    db.add(new_query)
    db.commit()
    db.refresh(new_query)
    return new_query


# # create session with global dictionary
# @app.post("/session")
# def create_session(session_id: int, request: schemas.UserSession):
#     if session_id in sessions:
#         return {"Error": "This session already exists, create another session!"}
#
#     sessions[session_id] = request
#     return sessions[session_id]
#
#
# # create user query with global dictionary
# @app.post("/user-query/{user_id}")
# def create_user_query(session_id: int, user_id: int, request: schemas.UserQuery):
#     # userquery.user_id = user_id
#     if session_id not in sessions:
#         return {"Error": "No session exists, create session first!"}
#
#     user_query[user_id] = request
#     sessions[session_id].query_history.append(request)  # add query to the query history
#     return user_query[user_id], sessions[session_id]


# # update user query
# @app.put("/update-query/{user_id}")
# def update_user_query(session_id: int, user_id: int, userquery: UpdateUserQuery, findcode: FindCode):
#     if findcode.find == False:
#
#         if user_id not in user_query:
#             return {"Error": "User does not exist"}
#
#         # user_query[user_id].update(userquery)
#         else:
#             if userquery.q_id != None:
#                 user_query[user_id].q_id = userquery.q_id
#
#             if userquery.q != None:
#                 user_query[user_id].q = userquery.q
#                 # sessions[session_id].query_history.append(userquery)
#
#             return user_query[user_id], sessions[session_id]
#
#     return {"You already find a code!"}


# get user by id from the db
@app.get("/user/{id}", status_code=200)
def get_user(id, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {id} is not available")
    return user


# get query by id from the db
@app.get("/query/{id}", status_code=200)
def get_query(id: int, response: Response, db: Session = Depends(get_db)):
    query = db.query(models.UserQuery).filter(models.UserQuery.q_id == id).first()
    if not query:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Query with id {id} is not available")
    return query


# get es result of query in db
@app.get("/get-user-query")
def read_user_query():
    pass


# get es result
@app.get("/get-user-query")
def read_user_query(session_id: int, user_id: int):

    #for user_id in user_query.keys():
    if user_id in user_query:
        res_search = es.search(index="test-index",
                               body={"size" : 1000,
                                   "query": {
                                       "bool": {
                                           "must": [
                                               {"match": {"docstring": user_query[user_id].q }},
                                           ]
                                       }
                                   },
                                   "stored_fields": []
                               }
                               )


        total_hit = res_search['hits']['total']['value']
        response = []
        scores = []
        for hit in res_search['hits']['hits']:
            ids = hit["_id"]
            response.append(ids)
            score = hit["_score"]
            scores.append(score)

        id_selected[:] = response
        result = es.get(index="test-index", id=id_selected[0])
        output = {"Total hit": total_hit, "Given query": user_query[user_id].q,
                  "current code example": result['_source']["code"], "score": scores[0]}

        sessions[session_id].es_output.append(output)

        # response = []
        # scores = []
        # for hit in res_search['hits']['hits']:
        #     code = hit["_source"]["code"]
        #     score = hit["_score"]
        #     response.append(code)
        #     scores.append(score)
        #
        # result = {"current code example": response[0], "score": scores[0]}
        return output, sessions[session_id]

    else:
        return {"Error": "User does not exist!"}


# filter
@app.get("/get-filter-query")
def read_filter_query(session_id: int, user_id: int):

    #for user_id in user_query.keys():
    if user_id in user_query:
        res_search = es.search(index="test-index",
                               body={"size" : 1000,
                                   "query": {
                                       "bool": {
                                           "must": [
                                               {"match": {"docstring": user_query[user_id].q }},
                                           ],
                               "filter": {
                                   "ids": {"values": id_selected}
                               }
                                       }
                                   },
                                   "stored_fields": []
                               }
                               )


        total_hit = res_search['hits']['total']['value']
        response = []
        scores = []
        for hit in res_search['hits']['hits']:
            ids = hit["_id"]
            response.append(ids)
            score = hit["_score"]
            scores.append(score)

        id_selected[:] = response
        result = es.get(index="test-index", id=id_selected[0])
        output = {"Total hit": total_hit, "Given query": user_query[user_id].q,
                  "current code example": result['_source']["code"], "score": scores[0]}

        sessions[session_id].es_output.append(output)

        # response = []
        # scores = []
        # for hit in res_search['hits']['hits']:
        #     code = hit["_source"]["code"]
        #     score = hit["_score"]
        #     response.append(code)
        #     scores.append(score)
        #
        # result = {"current code example": response[0], "score": scores[0]}
        return output, sessions[session_id]

    else:
        return {"Error": "User does not exist!"}


# extend
@app.get("/get-extend-query")
def read_extend_query(user_id: int):

    #for user_id in user_query.keys():
    if user_id in user_query:
        res_search = es.search(index="test-index",
                               body={"size" : 1000,
                                   "query": {
                                       "bool": {
                                           "should": [
                                               {"match": {"docstring": user_query[user_id].q }},
                                               # Todo: add second query here if necessary
                                           ],
                               # "filter": {
                               #     "ids": {"values": id_selected}
                               # }
                                       }
                                   },
                                   "stored_fields": []
                               }
                               )


        total_hit = res_search['hits']['total']['value']
        response = []
        scores = []
        for hit in res_search['hits']['hits']:
            ids = hit["_id"]
            response.append(ids)
            score = hit["_score"]
            scores.append(score)

        id_selected[:] = response
        result = es.get(index="test-index", id=id_selected[0])
        output = {"Total hit": total_hit, "current code example": result['_source']["code"], "score": scores[0]}

        # response = []
        # scores = []
        # for hit in res_search['hits']['hits']:
        #     code = hit["_source"]["code"]
        #     score = hit["_score"]
        #     response.append(code)
        #     scores.append(score)
        #
        # result = {"current code example": response[0], "score": scores[0]}
        return output

    else:
        return {"Error": "User does not exist!"}



# # request about find a right code from user
# @app.post("/find-code")
# async def ask_find_code(findcode: FindCode):
#     if findcode.find == True:
#         return {"Success": "This is what you need!"}
#
#     return {"Give me more information!"}



@app.delete('/delete-user')
def delete_query(user_id: int = Query(..., description="The ID of query to delete")):
    if user_id not in user_query.keys():
        return {"Error": "User does not exist"}

    del user_query[user_id]
    return {"Success": "User deleted!"}

