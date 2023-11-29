import pandas as pd
import re
import sqlite3
from flask import Flask, jsonify, request
from flasgger import Swagger, LazyString, LazyJSONEncoder, swag_from

class CustomFlaskAppWithEncoder(Flask):
    json_provider_class = LazyJSONEncoder

app = CustomFlaskAppWithEncoder(__name__)

swagger_template = dict(
    info = {
        'title' : LazyString(lambda: "API Documentation for Text cleansing "),
        'version' : LazyString(lambda: "1.0.0"),
        'description' : LazyString(lambda: "Dokumentasi API untuk Data Processing & Text cleansing"),
    },
    host = LazyString(lambda: request.host)
)

swagger_config = {
    "headers" : [],
    "specs" : [
        {
            "endpoint": "docs",
            "route" : "/docs.json",
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}
swagger = Swagger(app, template=swagger_template, config = swagger_config)

def clean_text(text):
    text = re.sub('@[^\text]+', ' ', text)
    text = re.sub(r'(?:\@|http?\://|https?\://|www)\S+', '', text)
    text = re.sub('<.*?>', ' ', text)
    text = re.sub('[^a-zA-Z]', ' ', text)
    text = re.sub('\n',' ',text)
    text = text.lower()
    text = re.sub(r'\b[a-zA-Z]\b', ' ', text)
    text = ' '.join(text.split())
    text = re.sub(r'pic.twitter.com.[\w]+', '', text)
    text = re.sub('user',' ', text)
    text = re.sub('RT',' ', text)
    return text

conn = sqlite3.connect('database_gold.db', check_same_thread = False)
df_kamusalay = pd.read_sql_query('SELECT * FROM kamusalay', conn)
df_abusive = pd.read_sql_query('SELECT * FROM abusive', conn)

kamusalay = dict(zip(df_kamusalay['alay'], df_kamusalay['normal']))
def alay_to_normal(text):
    for word in kamusalay:
        return ' '.join([kamusalay[word] if word in kamusalay else word for word in text.split(' ')])

list_abusive = df_abusive['ABUSIVE'].str.lower().tolist()
def normalize_abusive(text):
    list_word = text.split()#Split data yg masuk ke variable text
    return ' '.join([text for text in list_word if text not in list_abusive])

def text_cleansing(text):
    text = clean_text(text)
    text = alay_to_normal(text)
    text = normalize_abusive(text)
    return text

@app.route('/', methods=['GET'])
def hello_world():
    json_response = {
        'status_code': 200,
        'description': "Text cleansing API",
        'data': "Halo",
    }

    response_data = jsonify(json_response)
    return response_data

@swag_from("docs/swagger_input.yml", methods=['POST'])
@app.route('/input_text', methods=['POST'])
def text_processing():
    input_txt = str(request.form["input_teks"])
    output_txt = text_cleansing(input_txt)

    conn.execute('create table if not exists input_teks (input_text varchar(255), output_text varchar(255))')
    query_txt = 'INSERT INTO input_teks (input_text, output_text) values (?,?)'
    val = (input_txt, output_txt)
    conn.execute(query_txt, val)
    conn.commit()

    return_txt = {"input":input_txt, "output": output_txt}
    return jsonify (return_txt)

@swag_from("docs/swagger_upload.yml", methods=['POST'])
@app.route('/upload_file', methods=['POST'])
def upload_file():
    file = request.files["upload_file"]
    df_csv = (pd.read_csv(file, encoding="cp1252"))

    df_csv['new_tweet'] = df_csv['Tweet'].apply(text_cleansing)
    df_csv.to_sql("clean_tweet", con=conn, index=False, if_exists='append')
    conn.close()

    cleansing_tweet = df_csv.new_tweet.to_list()

    return_file = {
        'output': cleansing_tweet}
    return jsonify(return_file)


if __name__ == '__main__':
	app.run(debug=True)