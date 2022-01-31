'''
1. install requirements.
2. connect to elastic search: /Users/hanseungwoo/Codex/elasticsearch-7.13.2/bin -> ./elasticsearch
3. run ngrok with same port with uvicorn: ./ngrok http 8080
4. if reconnect ngrok then https address is also changed, so need to save new https address in dialogflow

'''
import uvicorn, schemas, models
from fastapi import FastAPI, Query, Depends, Response, HTTPException, status, Body
from database import engine, SessionLocal
from sqlalchemy.orm import Session, Query
from elastic import read_user_query, read_filter_query, get_keywords
from sqlalchemy.sql import func
import pickle


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# {id of function: [list of ALL words from docstrings ordered by tf-idf score]}
with open('select_word_tf_no_stop.pickle', 'rb') as handle:
    select_word_tf_no_stop = pickle.load(handle)


# function for getting database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# give_answer intent fulfillment
@app.post("/")
async def create_user_query(body: schemas.Fulfillment,   # must use body for the variable name.
                            db: Session = Depends(get_db)):

    # update the threshold from database with the average scores users satisfy
    if db.query(models.UserSession.score).filter(models.UserSession.intent == "satisfy").count() > 0:
        avg_score = db.query(func.avg(models.UserSession.score)).filter(models.UserSession.intent == "satisfy").first()
    else:
        avg_score = []

    # set threshold according to user satisfication
    # we need to increase threshold not to fast
    initial_val_threshold = 20
    threshold = initial_val_threshold if not avg_score else avg_score[0]

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
        # multiply 0.5 to the threshold to show the results user may like even if it is below the threshold.
        while score < 0.5*threshold:
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
                                     f"\n \ngiven query {query_from_user}"
                                     f"\n \nPlease start with 'Add: any key words you want to input'",
                            # "quickReplies": [
                            #     "Add more",
                            #     "End"
                            # ]
                        },
                        "platform": "TELEGRAM"
                    }
                ]
            }

        if score >= 0.5*threshold:
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

        code_example, score, id_selected_filter, total_hit = read_filter_query(query_from_user, id_selected)

        while score < 0.5*threshold:
            id_selected = id_selected_filter
            # add response_id, session_id, score to the database userSeeion
            new_session = models.UserSession(response_id=response_id, session_id=session_id, score=score,
                                             intent="not satisfy")
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            id_list_keyword = get_keywords(query_from_user)
            # id is string so change it to int
            id_list_keyword = [int(id) for id in id_list_keyword]

            key_word_list = [select_word_tf_no_stop[id] for id in id_list_keyword]

            return {
                "fulfillmentMessages": [
                    {
                        "quickReplies": {
                            "title": f"I need more information. \n \nTotal hit {total_hit}."
                                     f"\n \ngiven query {query_from_user}"
                                     f"\n \nYou can give me inputs by 'Add:...' or "
                                     f"\n \nIf you want some relevant keywords you can use here you go!"
                                     # f"\n \n{id_selected_filter[:10]}"
                                     # f"\n \n{id_selected[:10]}"
                                     f"\n \n{key_word_list}",
                            # "quickReplies": [
                            #     # "Add input directly",
                            #     "Yes help me!"
                            # ]
                        },
                        "platform": "TELEGRAM"
                    }
                ]
            }

        if score >= 0.5*threshold:
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

# if intent == "get_keyword":
    #     # based on the initial user query, run elasticsearch first
    #     # get id of top 10 search results
    #     # show user the key words with highest score, i.e dict[id][0] from each of 10 search results
    #
    #     id_list_keyword = get_keywords(query_from_user)
    #     # id is string so change it to int
    #     id_list_keyword = [int(id) for id in id_list_keyword]
    #
    #     key_word_list = [select_word_tf_no_stop[id][0] for id in id_list_keyword]
    #
    #     if key_word_list:
    #         return {
    #             "fulfillmentMessages": [
    #                 {
    #                     "quickReplies": {
    #                         "title": f"Here you go!"
    #                                  f"\n \nYou can use one of these keywords {query_from_user} "
    #                                  f"given query {query_from_user}"
    #                                  f"which you think it is relevant to your problem as inputs, "
    #                                  f"\n \n and write your query like 'Add: key words you want to use' ",
    #                         # "quickReplies": [
    #                         #     "Add input directly",
    #                         #     "Yes help me!"
    #                         # ]
    #                     },
    #                     "platform": "TELEGRAM"
    #                 }
    #             ]
    #         }
    #     else:
    #         return {
    #             "fulfillmentMessages": [
    #                 {
    #                     "quickReplies": {
    #                         "title": f"Sorry I can't find any helpful keywords"
    #                                  f"\n \n Please write your query like 'Add: ",
    #                         # "quickReplies": [
    #                         #     "Add input directly",
    #                         #     "Yes help me!"
    #                         # ]
    #                     },
    #                     "platform": "TELEGRAM"
    #                 }
    #             ]
    #         }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

