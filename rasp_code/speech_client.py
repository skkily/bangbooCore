"""
分为几个线程外加一个主线程
子线程分为: 音频录制与保存线程; 对话线程; 播放声音线程
各自线程对外接口:
    音频录制线程: 输出音频
    对话线程: 接收音频, 输出对话结果
    声音播放线程: 接收对话结果, 播放声音
线程内部实现:
    音频录制线程: 
        - 对语音进行判断, 截取真正的对话, 保存为音频文件
        - 在检测到对话时, 发出 ‘新对话开始’ 的提醒
        - 对话结束时, 发出 ‘对话结束’ 的提醒
    对话线程:
        - 当接收到 ‘对话结束’ 的提醒后, 发送音频文件到服务器, 接收服务器的对话结果
        - 当接收到 ‘新对话开始’ 的提醒后, 丢弃当前正在进行的任务
        - 当获得对话结果后, 发出 ‘对话结果输出’ 的提醒
    声音播放线程:
        - 当接收到 ‘对话结果输出’ 的提醒后, 播放声音
        - 当接收到 ‘新对话开始’ 的提醒后, 减小当前音量
"""

from audio_recoder import AudioRecoder
from talk_module import TalkModule
from tts_module import TtsModule

import queue
import os

AUDIO_FILE_PATH = "/tmp/speech_client" #音频文件保存路径
NET_ADDRESS = "http://服务器IP地址:端口/wav_test"

def mkDir(filePath):
    os.makedirs(filePath, exist_ok=True)
    pass

if __name__ == "__main__":
    mkDir(AUDIO_FILE_PATH)
    msgQueue = queue.Queue()

    audio = AudioRecoder(AUDIO_FILE_PATH, msgQueue)
    talk = TalkModule(msgQueue)
    tts = TtsModule()

    while True:
        msg = msgQueue.get()
        #print(f"msg queue recv: {msg}")
        if msg == "speech_over":
            print(f"speech over")
            talk.waveLoad(f"{AUDIO_FILE_PATH}/audio_0.wav", NET_ADDRESS)
            pass
        if msg == "speech_start":
            print(f"speech start")
            tts.reduceSpeak()
            pass
        if msg == "speech_skip":
            print(f"speech skip")
            tts.normalSpeak()
            pass
        if msg[0:8] == "ques_get":
            print(f"question:{msg[8:]}")
            pass
        if msg[0:8] == "talk_get":
            print(f"speech play")
            tts.speak(msg[8:], f"{AUDIO_FILE_PATH}/tts.mp3")
            pass
    
