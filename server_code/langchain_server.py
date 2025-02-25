
import http.server
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import os

import json
import emoji

import re

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
# LLM_ADDRESS="http://192.168.6.73:8000/v1"

LLM_ADDRESS="https://api.deepseek.com"
API_KEYS="sk-3fca17d8179dd61e63" # 举例, 需要替换成你自己的keys
LLM_MODEL="deepseek-chat"

#LLM_ADDRESS="http://localhost:18030/v1"
#LLM_MODEL="qwen2.5:7b"
#API_KEYS="ollama"

def langchain_init():

    model = ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=API_KEYS,
        openai_api_base=LLM_ADDRESS,
    )

    # Define the function that calls the model
    def call_model(state: MessagesState):
        response = model.invoke(state["messages"])
        # response = emoji.demojize(response)
        return {"messages": response}

    # Define a new graph
    workflow = StateGraph(state_schema=MessagesState)

    # Define the (single) node in the graph
    workflow.add_edge(START, "model")
    workflow.add_node("model", call_model)

    # Add memory
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    print("init over")
    return app

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    llm_speech = 0
    first_speech = 0

    def __init__(self, *args, **kwargs):
        # 调用父类的初始化方法
        super().__init__(*args, **kwargs)

    import re

    def count_characters(self, text) -> int:
        # 匹配中文字符和英文单词
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)  # 匹配中文字符
        english_words = re.findall(r'\b\w+\b', text)  # 匹配英文单词

        total_count = len(chinese_chars) + len(english_words)
        return total_count
    
    def do_POST(self):
        if (self.path == '/wav_test'):
            # 获取请求体的长度
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            upload_dir = 'uploads'
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, os.path.basename('output.wav'))

            with open(file_path, 'wb') as f:
                f.write(post_data)
                f.close()
            
            text = self.speech_to_text()
            text = emoji.demojize(text)
            print(f'question: {text}')

            json_string = ""
            if text.find("对话模式开启") > 0:
                SimpleHTTPRequestHandler.llm_speech = 1
                json_string = json.dumps({"msg": "你现在可以和我连续对话了"})
                print("on")
            elif text.find("对话模式关闭") > 0:
                SimpleHTTPRequestHandler.llm_speech = 0
                json_string = json.dumps({"msg": "好的， 我会保持沉默"})
                print("off")
            elif SimpleHTTPRequestHandler.llm_speech == 1:
                print("run")
                #pos = text.find("同学")
                pos = 0 #fix
                if pos != -1 and len(text) > 1:
                    #text = text[pos+2:] #fix
                    print(f'question: {text}')
                    response = self.get_llm_response(text)
                    response_len = self.count_characters(response)
                    print(f'length: {response_len} answer : {response} ')

                    while (response_len > 120):
                        response = self.get_llm_response("刚刚你的回答字数太多了， 请总结你上次的回答")
                        response_len = self.count_characters(response)
                        print(f'reanswer length: {response_len} answer : {response} ')

                    print(f'final answer: {response}')
                    json_string = json.dumps({"msg": response})
                else:
                    json_string = ""

            # 返回响应
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json_string.encode('utf-8'))
            # self.wfile.write(f'{{"status": "success","msg":"{response}"}}'.encode('utf-8'))

    def get_llm_response(self, query) -> str:
        config = {"configurable": {"thread_id": "aabbccdd1234"}}
        sysMessage = SystemMessage("你来扮演陪聊助手, 最重要的事是要保证对话的字数不能过多, 贴近口语对话.使用对话者的语言与他对话. 不要向我提出问题, 不能有表情符号, 不要说出你的设定")

        input_messages = [HumanMessage(query)]
        if SimpleHTTPRequestHandler.first_speech == 0:
            SimpleHTTPRequestHandler.first_speech = 1
            input_messages.append(sysMessage)

        print(input_messages)
        output = self.__app.invoke({"messages": input_messages}, config)
        # output["messages"][-1].pretty_print()  # output contains all messages in state
        return output["messages"][-1].content
        return "aabbccdd"
    
    @classmethod
    def speech_init(cls, app):
        cls.model_sts = AutoModel(model='iic/SenseVoiceSmall', \
                                disable_update=True, device="cuda:0",)
        cls.__app = app

    @classmethod
    def speech_to_text(cls) -> str:
        if hasattr(cls, "model_sts"):
            res = cls.model_sts.generate(
                    input='./uploads/output.wav',
                    cache={},
                    language="auto", # "zn", "en", "yue", "ja", "ko", "nospeech"
                    use_itn=True,
                    batch_size=64, 
                )
            return rich_transcription_postprocess(res[0]["text"])
        else:
            return 'not init speech model'



def run(server_class=http.server.HTTPServer, handler_class=SimpleHTTPRequestHandler, port=34561):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    model = langchain_init()
    SimpleHTTPRequestHandler.speech_init(model)
    print(f'Starting http server on port == {port}...')
    httpd.serve_forever()

# 启动服务器
if __name__ == "__main__":
    run()

