from elasticsearch import Elasticsearch

es = Elasticsearch()

# dictionary {user_id: UserQuery}
user_query = {}

# id from the search result
id_selected = []

# all session created
sessions = {}

def get_keywords(query):
    key_word_list = []
    res_search = es.search(index="test-index",
                           body={"size": 10,
                                 "query": {
                                     "bool": {
                                         "must": [
                                             {"match": {"docstring": query}},
                                         ]
                                     }
                                 },
                                 "stored_fields": []
                                 }
                           )

    response = []
    for hit in res_search['hits']['hits']:
        ids = hit["_id"]
        response.append(ids)

    return response



def read_user_query(query):
    #for user_id in user_query.keys():
    res_search = es.search(index="test-index",
                           body={"size" : 1000,
                               "query": {
                                   "bool": {
                                       "must": [
                                           {"match": {"docstring": query }},
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

    # id_selected[:] = response
    # result = es.get(index="test-index", id=id_selected[0])

    result = es.get(index="test-index", id=response[0])

    code_example = result['_source']["code"]
    score_highest = scores[0]

    # output = {"Total hit": total_hit, "Given query": user_query[user_id].q,
    #           "current code example": result['_source']["code"], "score": scores[0]}
    # sessions[session_id].es_output.append(output)

    # response = []
    # scores = []
    # for hit in res_search['hits']['hits']:
    #     code = hit["_source"]["code"]
    #     score = hit["_score"]
    #     response.append(code)
    #     scores.append(score)
    #
    # result = {"current code example": response[0], "score": scores[0]}
    return code_example, score_highest, response, total_hit


# filter
def read_filter_query(query, id_selected):

    #for user_id in user_query.keys():
    res_search = es.search(index="test-index",
                           body={
                               # "size" : 1000,
                               "query": {
                                   "bool": {
                                       "must": [
                                           {"match": {"docstring": query }},
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

    # id_selected[:] = response
    # result = es.get(index="test-index", id=id_selected[0])
    result = es.get(index="test-index", id=response[0])

    code_example = result['_source']["code"]
    score_highest = scores[0]

    # output = {"Total hit": total_hit, "Given query": user_query[user_id].q,
    #           "current code example": result['_source']["code"], "score": scores[0]}

    # sessions[session_id].es_output.append(output)

    # response = []
    # scores = []
    # for hit in res_search['hits']['hits']:
    #     code = hit["_source"]["code"]
    #     score = hit["_score"]
    #     response.append(code)
    #     scores.append(score)
    #
    # result = {"current code example": response[0], "score": scores[0]}
    return code_example, score_highest, response, total_hit


# # extend
# def read_extend_query(query):
#
#     #for user_id in user_query.keys():
#
#     res_search = es.search(index="test-index",
#                            body={"size" : 1000,
#                                "query": {
#                                    "bool": {
#                                        "should": [
#                                            {"match": {"docstring": query }},
#                                        ],
#                            # "filter": {
#                            #     "ids": {"values": id_selected}
#                            # }
#                                    }
#                                },
#                                "stored_fields": []
#                            }
#                            )
#
#
#     total_hit = res_search['hits']['total']['value']
#     response = []
#     scores = []
#     for hit in res_search['hits']['hits']:
#         ids = hit["_id"]
#         response.append(ids)
#         score = hit["_score"]
#         scores.append(score)
#
#     id_selected[:] = response
#     result = es.get(index="test-index", id=id_selected[0])
#     code_example = result['_source']["code"]
#     score_highest = scores[0]
#
#     # output = {"Total hit": total_hit, "current code example": result['_source']["code"], "score": scores[0]}
#
#     # response = []
#     # scores = []
#     # for hit in res_search['hits']['hits']:
#     #     code = hit["_source"]["code"]
#     #     score = hit["_score"]
#     #     response.append(code)
#     #     scores.append(score)
#     #
#     # result = {"current code example": response[0], "score": scores[0]}
#
#     return code_example, score_highest, id_selected, total_hit



