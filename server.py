from flask import Flask, send_from_directory, request, session, jsonify, make_response
from flask_cors import CORS
import requests
from datetime import datetime,timedelta
import pymongo 
import json
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

myclient = pymongo.MongoClient("mongodb://localhost:27017")
print(myclient)
mydb = myclient["Cognalyst"]
print(mydb)
reviews_collection = mydb.reviews
keywords_collection = mydb.keywords

import json
from watson_developer_cloud import NaturalLanguageUnderstandingV1
from watson_developer_cloud.natural_language_understanding_v1 \
import Features, EntitiesOptions, KeywordsOptions
import operator

natural_language_understanding = NaturalLanguageUnderstandingV1(
  version='2017-02-27',
    iam_apikey='gWio-Ss_0qCLMDKg8-FcuaEdkTIazavGW7sREyFCeZcM',
    url='https://gateway-lon.watsonplatform.net/natural-language-understanding/api')

app = Flask(__name__)
CORS(app)

@app.route('/addreview', methods=['POST'])
def add_review():
    b_name = json.loads(request.data)['b_name']
    review = json.loads(request.data)['review']
    user = json.loads(request.data)['user']
    user_rating = json.loads(request.data)['user_rating']
    time = datetime.now()

    document = {
                "b_name" : b_name,
                "review" : review,
                "user" : user,
                "created_at" : time,
                "rating" : 0,
                "user_rating" : user_rating

            }
            
    reviews_collection.update_one({"b_name" : b_name,"review" : review,"user" : user,"created_at" : time},{"$set":document},upsert=True)
    review_doc_id = reviews_collection.find_one({"b_name" : b_name,
                "review" : review,
                "user" : user,
                "created_at" : time})["_id"]
    review_rating = 0
    count = 0

    for sub_line in review.split("."):
        print("subline:",sub_line,"len:",len(sub_line))
        if len(sub_line)>0:
            if len(sub_line)<=15:
                sub_line+=" is the thing i wanted to say."
            print(sub_line)
            response = natural_language_understanding.analyze(
            text=sub_line.lower(),
            features=Features(
                        keywords=KeywordsOptions(
                        sentiment=True,
                        emotion=True))).get_result()

    
    
            
            for i in response['keywords']:
                count+=1
                senti_score = i['sentiment']['score']
                relevancy_score = i['relevance']
                pos1 = i['emotion']['joy']
                neg1 = (i['emotion']['sadness'] + i['emotion']['fear'] + i['emotion']['fear'] + i['emotion']['disgust']) / 4
                # keyword_score = relevancy_score*((senti_score+(pos1-neg1))/2)
                keyword_score = relevancy_score*(senti_score)
                review_rating+= keyword_score
                time = datetime.now()
                kw_doc = {
                    "keyword" : i['text'],
                    "b_name" : b_name,
                    "score" : keyword_score,
                    "emotions" : i['emotion'],
                    "review_id" : review_doc_id,
                    "type" : i['sentiment']['label'],
                    "time" : time
                }
                keywords_collection.update_many({"b_name":b_name,"keyword" : i['text'],"time" : time}, {"$set":kw_doc} , upsert=True)
    print(count)
    if count>0:
        review_rating = review_rating/count

    reviews_collection.update_one({"_id":review_doc_id},{"$set": {"rating":review_rating}},upsert=True)
    return jsonify({"status":"success"})

@app.route('/getallreviews', methods=['POST'])
def get_all_reviews():
    b_name = json.loads(request.data)['b_name']
    all_reviews_docs = reviews_collection.find({"b_name":b_name})
    data = []
    for review in all_reviews_docs:
        review['_id'] = str(review['_id'])
        data.append(review)
    print(data)

@app.route('/gettopfivereviews', methods=['POST'])
def get_top_reviews():
    b_name = json.loads(request.data)['b_name']
    all_reviews_docs = reviews_collection.find({"b_name":b_name}).sort("rating",-1).limit(5)
    print(all_reviews_docs)
    data = []
    for review in all_reviews_docs:
        review['_id'] = str(review['_id'])
        data.append(review)
    print(data)

    return jsonify({"status":"success","data":data})
    

@app.route('/getbottomfivereviews', methods=['POST'])
def get_bottom_reviews():
    b_name = json.loads(request.data)['b_name']
    all_reviews_docs = reviews_collection.find({"b_name":b_name}).sort("rating",1).limit(5)
    print(all_reviews_docs)
    data = []
    for review in all_reviews_docs:
        review['_id'] = str(review['_id'])
        data.append(review)
    print(data)


@app.route('/getallpositive', methods=['POST'])
def get_all_positive():
    b_name = json.loads(request.data)['b_name']
    all_keys_docs = keywords_collection.find({"b_name":b_name,"type":"positive"}).sort("time",-1)
    print(all_keys_docs)
    data = []
    for keyword in all_keys_docs:
        keyword['_id'] = str(keyword['_id'])
        keyword['review_id'] = str(keyword['review_id'])
        
        data.append(keyword)
    print(data)

    return jsonify({"status":"success","data":data})

@app.route('/getallnegative', methods=['POST'])
def get_all_negative():
    b_name = json.loads(request.data)['b_name']
    all_keys_docs = keywords_collection.find({"b_name":b_name,"type":"negative"}).sort("time",-1)
    print(all_keys_docs)
    data = []
    for keyword in all_keys_docs:
        keyword['_id'] = str(keyword['_id'])
        keyword['review_id'] = str(keyword['review_id'])
        data.append(keyword)
    print(data)

    return jsonify({"status":"success","data":data})

@app.route('/gettenpositive', methods=['POST'])
def get_ten_positive():
    b_name = json.loads(request.data)['b_name']
    all_keys_docs = keywords_collection.find({"b_name":b_name,"type":"positive"}).sort("score",-1).limit(10)
    print(all_keys_docs)
    data = []
    for keyword in all_keys_docs:
        keyword['_id'] = str(keyword['_id'])
        keyword['review_id'] = str(keyword['review_id'])
        
        data.append(keyword)
    print(data)

    return jsonify({"status":"success","data":data})

@app.route('/gettennegative', methods=['POST'])
def get_ten_negative():
    b_name = json.loads(request.data)['b_name']
    all_keys_docs = keywords_collection.find({"b_name":b_name,"type":"negative"}).sort("score",1).limit(10)
    print(all_keys_docs)
    data = []
    for keyword in all_keys_docs:
        keyword['_id'] = str(keyword['_id'])
        keyword['review_id'] = str(keyword['review_id'])
        data.append(keyword)
    print(data)

    return jsonify({"status":"success","data":data})

@app.route('/getrecentkeywords', methods=['POST']) #takes business name and since(number of seconds) and gives you the recent keywords
def get_recent():
    b_name = json.loads(request.data)['b_name']
    since = json.loads(request.data)['since']
    if since == "week":
        seconds = 604800
    elif since == "fortnight":
        seconds = 604800*2
    elif since == "month":
        seconds = 86400*30
    week_stamp = timedelta(seconds)
    x = datetime.now() - datetime(1970,1,1)
    x_secs = x.total_seconds()
    print(x_secs)
    since_secs = x_secs - seconds
    print(since_secs)
    since_stamp =  datetime.fromtimestamp(int(since_secs))
    print(since_stamp)


    all_keys_docs = keywords_collection.find({"b_name":b_name,"time": { "$gt": since_stamp }}).sort("time",-1)
    print(all_keys_docs)
    data = []
    for keyword in all_keys_docs:
        print(keyword)
        keyword['_id'] = str(keyword['_id'])
        keyword['review_id'] = str(keyword['review_id'])
        data.append(keyword)
    print(data)

    return jsonify({"status":"success","data":data})

@app.route('/getrecentposkeywords', methods=['POST']) #takes business name and since(number of seconds) and gives you the recent keywords which are positive
def get_recent_pos():
    b_name = json.loads(request.data)['b_name']
    since = json.loads(request.data)['since']
    if since == "week":
        seconds = 604800
    elif since == "fortnight":
        seconds = 604800*2
    elif since == "month":
        seconds = 86400*30
    week_stamp = timedelta(seconds)
    x = datetime.now() - datetime(1970,1,1)
    x_secs = x.total_seconds()
    print(x_secs)
    since_secs = x_secs - seconds
    print(since_secs)
    since_stamp =  datetime.fromtimestamp(int(since_secs))
    print(since_stamp)


    all_keys_docs = keywords_collection.find({"b_name":b_name,"type":"positive","time": { "$gt": since_stamp }}).sort("time",-1)
    print(all_keys_docs)
    data = []
    for keyword in all_keys_docs:
        print(keyword)
        keyword['_id'] = str(keyword['_id'])
        keyword['review_id'] = str(keyword['review_id'])
        data.append(keyword)
    print(data)

    return jsonify({"status":"success","data":data})


@app.route('/getrecentnegkeywords', methods=['POST']) #takes business name and since(number of seconds) and gives you the recent keywords which are postive
def get_recent_neg():
    b_name = json.loads(request.data)['b_name']
    since = json.loads(request.data)['since']
    if since == "week":
        seconds = 604800
    elif since == "fortnight":
        seconds = 604800*2
    elif since == "month":
        seconds = 86400*30
    week_stamp = timedelta(seconds)
    x = datetime.now() - datetime(1970,1,1)
    x_secs = x.total_seconds()
    print(x_secs)
    since_secs = x_secs - seconds
    print(since_secs)
    since_stamp =  datetime.fromtimestamp(int(since_secs))
    print(since_stamp)


    all_keys_docs = keywords_collection.find({"b_name":b_name,"type":"negative","time": { "$gt": since_stamp }}).sort("time",1)
    print(all_keys_docs)
    data = []
    for keyword in all_keys_docs:
        print(keyword)
        keyword['_id'] = str(keyword['_id'])
        keyword['review_id'] = str(keyword['review_id'])
        data.append(keyword)
    print(data)

    return jsonify({"status":"success","data":data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

        








