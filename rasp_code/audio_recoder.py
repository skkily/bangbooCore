import pyaudio
import os
import time
import wave
import webrtcvad
import threading
import queue

# 参数设置
AUDIO_RATE = 16000        # 音频采样率
AUDIO_CHANNELS = 1        # 单声道
CHUNK = 1024              # 音频块大小
VAD_MODE = 3              # VAD 模式 (0-3, 数字越大越敏感)
NO_SPEECH_THRESHOLD = 1.5   # 无效语音阈值，单位：秒
SAVE_SPEECH_THRESHOLD = 1 # 低于该值不保存

# 全局变量
saved_intervals = []

class AudioRecoder:
    def __init__(self, audio_path, msg_queue) -> None:
        self.__audio_path = audio_path
        self.__msg_queue = msg_queue
        print("audiorecorder start")

        # 初始化 WebRTC VAD
        self.__vad = webrtcvad.Vad()
        self.__vad.set_mode(VAD_MODE)

        self.__stop_event = threading.Event()
        self.__thread = threading.Thread(target=self.__run)
        self.__thread.start()

    # 保存音频
    def __save_audio(self, segments_to_save):

        global saved_intervals
        audio_output_path = f"{self.__audio_path}/audio_0.wav"

        if not segments_to_save:
            return
            
        # 获取有效段的时间范围
        start_time = segments_to_save[0][1]
        end_time = segments_to_save[-1][1]
        
        # 检查是否与之前的片段重叠
        if saved_intervals and saved_intervals[-1][1] >= start_time:
            print("当前片段与之前片段重叠，跳过保存")
            segments_to_save.clear()
            return
        
        # 保存音频
        audio_frames = [seg[0] for seg in segments_to_save]

        wf = wave.open(audio_output_path, 'wb')
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(AUDIO_RATE)
        wf.writeframes(b''.join(audio_frames))
        wf.close()
        #print(f"音频保存至 {audio_output_path}")
        
        # 记录保存的区间
        saved_intervals.append((start_time, end_time))

        self.__msg_queue.put("speech_over")

    # 检测 VAD 活动
    def __check_vad_activity(self, audio_data):
        # 将音频数据分块检测
        num, rate = 0, 0.4
        step = int(AUDIO_RATE * 0.02)  # 20ms 块大小
        flag_rate = round(rate * len(audio_data) // step)

        for i in range(0, len(audio_data), step):
            chunk = audio_data[i:i + step]
            if len(chunk) == step:
                if self.__vad.is_speech(chunk, sample_rate=AUDIO_RATE):
                    num += 1

        if num > flag_rate:
            return True
        return False


    # 音频录制线程
    def __audio_recorder(self):
        segments_to_save = []

        last_active_time = time.time()
        last_save_time = last_active_time
        
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=AUDIO_CHANNELS,
                        rate=AUDIO_RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
        
        audio_buffer = []
        print("microphone work start")

        have_audio = 0
        
        while not self.__stop_event.is_set():
            data = stream.read(CHUNK)
            audio_buffer.append(data)
            
            if not have_audio:
                last_save_time = time.time()

            # 每 0.5 秒检测一次 VAD
            if len(audio_buffer) * CHUNK / AUDIO_RATE >= 0.5:
                # 拼接音频数据并检测 VAD
                raw_audio = b''.join(audio_buffer)
                vad_result = self.__check_vad_activity(raw_audio)
                segments_to_save.append((raw_audio, time.time()))

                if vad_result:
                    # print("检测到语音活动")
                    last_active_time = time.time()
                    if have_audio == 0:
                        self.__msg_queue.put("speech_start")
                        have_audio = 1
                else:
                    # print("静音中...")
                    pass
                if have_audio == 0:
                    segments_to_save.clear()
                # if have_audio:
                    # segments_to_save.append((raw_audio, time.time()))
                audio_buffer = []  # 清空缓冲区

            if have_audio and time.time() - last_active_time > NO_SPEECH_THRESHOLD:
                if last_active_time - last_save_time < (SAVE_SPEECH_THRESHOLD - 0.5):
                    # print("对话语音时长过短")
                    self.__msg_queue.put("speech_skip")
                    pass
                else:
                    self.__save_audio(segments_to_save)
                have_audio = 0
                last_save_time = last_active_time = time.time()
                segments_to_save.clear()
        
        stream.stop_stream()
        stream.close()
        p.terminate()

    def __run(self) -> None:
        print("mic thread start...")
        self.__audio_recorder()

    def stop(self) -> None:
        self.__stop_event.set()  # 设置停止事件
        self.__thread.join()     # 等待线程结束


if __name__ == "__main__":
    msg = queue.Queue()
    my_object = AudioRecoder("/tmp/speech_client", msg)
    while True:
        m = msg.get()
        print(m)

