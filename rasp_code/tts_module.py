import edge_tts
import pygame
import time
import asyncio

class TtsModule:
    def __init__(self) -> None:
        pass

    # 生成并保存音频文件
    async def __generate_audio(self, text, filename):
        communicate = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural")
        await communicate.save(filename)

    # --- 播放音频 -
    def __play_audio(self, file_path):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play()
            # while pygame.mixer.music.get_busy():
            #     time.sleep(1)  # 等待音频播放结束
            # print("播放完成！")
        except Exception as e:
            print(f"播放失败: {e}")
        finally:
            # pygame.mixer.quit()
            pass

    # edgetts
    async def __edgetts(self, text, filename):
        try:
            await self.__generate_audio(text, filename)
            self.__play_audio(filename)
        except Exception as e:
            pass


    def speak(self, text, filename) -> None:
        print(f"speak: {text}")
        asyncio.run(self.__edgetts(text, filename))
        pass

    def reduceSpeak(self) -> None:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            # pygame.mixer.music.stop()
            pygame.mixer.music.pause()
            # print("暂停播放")
        pass

    def normalSpeak(self) -> None:
        if pygame.mixer.get_init():
            # pygame.mixer.music.stop()
            pygame.mixer.music.unpause()
            # print("继续播放")
        pass

if __name__ == "__main__":
    print("start")
    tts = TtsModule()
    tts.speak("你好")
    tts.speak("你好")
