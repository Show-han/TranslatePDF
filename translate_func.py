import time
import uuid
import hashlib
import requests
#from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer

def youdaoTranslate(translate_text,flag):
    youdao_url = 'https://openapi.youdao.com/api'
    input_text = ""

    if (len(translate_text) <= 20):
        input_text = translate_text

    elif (len(translate_text) > 20):
        input_text = translate_text[:10] + str(len(translate_text)) + translate_text[-10:]

    time_curtime = int(time.time())
    app_id = "1dd8bb8bb6cb63b6"
    uu_id = uuid.uuid4()
    app_key = "QZNU3sjPWBHYGSF86lLHLKrSagcMyiP2"

    sign = hashlib.sha256(
        (app_id + input_text + str(uu_id) + str(time_curtime) + app_key).encode('utf-8')).hexdigest()

    data = {
        'q': translate_text,
        'appKey': app_id,
        'salt': uu_id,
        'sign': sign,
        'signType': "v3",
        'curtime': time_curtime,
    }
    if flag:
        data['from'] = "zh-CHS"
        data['to'] = "en"
    else:
        data['from'] = "en"
        data['to'] = "zh-CHS"

    r = requests.get(youdao_url, params=data).json()
    return r["translation"][0]

'''
#maxlength < 512
def local_translate(content):
    model = AutoModelForSeq2SeqLM.from_pretrained("C:/Users/crescentcat/PytorchLearning/opus-mt-en-cn")
    tokenizer = AutoTokenizer.from_pretrained("C:/Users/crescentcat/PytorchLearning/opus-mt-en-cn")
    translation = pipeline("translation_en_to_zh", model=model, tokenizer=tokenizer)
    translated_text = translation(content)[0]['translation_text']
    return translated_text
'''