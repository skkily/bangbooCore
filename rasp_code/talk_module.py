import requests
import json
import threading


class TalkModule:
    def __init__(self, msgQueue) -> None:
        self.__msg = msgQueue

        self.__cond = threading.Condition()
        self.__speech_data = []
        self.__msg_text = ""
        self.__ques_text = ""

        self.__stop_event = threading.Event()
        self.__thread = threading.Thread(target=self.__run)
        self.__thread.start()
        pass

    def __net_request(self, path, url) -> bool:
        # 打开二进制文件
        with open(path, 'rb') as file:
            # 读取文件内容
            file_data = file.read()
            
            try:
                # 发送 POST 请求
                response = requests.post(url, file_data)

                if response.status_code == 200:
                    # print('响应内容:', response.text)
                    try:
                        msg_text = json.loads(response.text)
                        if 'user' in msg_text:
                            ques_text = msg_text["user"]
                            self.__ques_text = ques_text.strip()
                            self.__msg.put(f"ques_get{self.__ques_text}")
                        if 'msg' in msg_text:
                            msg_text = msg_text["msg"]
                            self.__msg_text = msg_text.strip()
                            # self.__msg_text = msg_text[msg_text.find("/think") + 7:].strip()
                            return True
                    except json.decoder.JSONDecodeError as e:
                        return False
            except Exception as e:
                return False
        return False
        pass

    def __run(self):
        rpath = ""
        rurl = ""
        while not self.__stop_event.is_set():
            with self.__cond:
                while len(self.__speech_data) == 0:
                    self.__cond.wait()
                if self.__stop_event.is_set():
                        break
                rpath = self.__speech_data[-1][0]
                rurl = self.__speech_data[-1][1]
                self.__speech_data.clear()
            # bug tobe fix
            if self.__net_request(rpath, rurl):
                if len(self.__speech_data) == 0:
                    self.__msg.put(f"talk_get{self.__msg_text}")
            else:
                self.__msg.put("speech_skip")

                
        pass

    def stop(self) -> None:
        print("TalkModule exit")
        self.__stop_event.set()  # 设置停止事件
        with self.__cond:
            self.__cond.notify_all()
        self.__thread.join()     # 等待线程结束

    def waveLoad(self, file_path, url) -> None:
        with self.__cond:
            self.__speech_data.clear()
            self.__speech_data.append((file_path, url))
            self.__cond.notify_all()
        pass

if __name__ == "__main__":
    import queue
    msg = queue.Queue()
    talk = TalkModule(msg)
    talk.waveLoad("/tmp/output.wav", "http://192.168.6.73:18080/wav_test")
    print(msg.get())
    talk.stop()
    print("exit")
