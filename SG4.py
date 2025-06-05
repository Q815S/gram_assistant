import serial, time, os, uuid, multiprocessing, speech_recognition as sr, google.generativeai as genai, screen_brightness_control as sbc
from gtts import gTTS
from playsound import playsound
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GModel = os.getenv('model')
system_instruction = os.getenv('system_instruction')

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(GModel, system_instruction = system_instruction)

SERIAL_PORT = 'COM3'
BAUD_RATE = 115200
MMIN = 0
MMAX = 1024
SMIN = 0
SMAX = 100

current_playback_process = None
temp_mp3_filename_global = None

def Speech_Recognition(recognizer, microphone, ser_conn=None):
    text = None
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("이제 말씀하세요!")
        try:
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            print("음성 입력 시간을 초과했어요.")
            return None

    if audio:
        print("음성을 분석하고 있어요.")
        try:
            text = recognizer.recognize_google(audio, language="ko-KR")
            print(f"인식된 텍스트: {text}")
        except sr.UnknownValueError:
            print("음성을 인식할 수 없어요.")
        except sr.RequestError as e:
            print(f"Google Speech Recognition 서비스에서 결과를 요청할 수 없습니다; {e}")

    return text

def Gemini(prompt_text, ser_conn=None):
    if not prompt_text:
        return "입력된 텍스트가 없어요."

    response = model.generate_content(prompt_text)
    if hasattr(response, 'text') and response.text:
        return response.text
    elif response.parts and hasattr(response.parts[0], 'text'):
        return response.parts[0].text
    else:
        print("문제가 발생했어요. 잠시 후 다시 시도해보세요.")
        return "Gemini 응답 형식 오류"

def Audio(filename):
    playsound(filename)

def GTTS(text_to_speak, lang='ko', ser_conn=None):
    global current_playback_process, temp_mp3_filename_global

    if not text_to_speak or text_to_speak.isspace():
        print("음성으로 변환할 텍스트가 없어요. 잠시후 다시 시도해보세요.")
        return

    if current_playback_process and current_playback_process.is_alive():
        print("TTS 재생을 중지합니다.")
        current_playback_process.terminate()
        current_playback_process.join(timeout=1)
        if temp_mp3_filename_global and os.path.exists(temp_mp3_filename_global):
            os.remove(temp_mp3_filename_global)
        current_playback_process = None
        temp_mp3_filename_global = None

    tts = gTTS(text=text_to_speak, lang=lang, slow=False)
    temp_mp3_filename_global = f"TTS_{uuid.uuid4()}.mp3"
    tts.save(temp_mp3_filename_global)
    current_playback_process = multiprocessing.Process(target=Audio, args=(temp_mp3_filename_global,))
    current_playback_process.start()

def Adaptive_Brightness(input_value_str):
    input_value = int(input_value_str)

    if MMAX == MMIN:
        ratio = 0.5
    else:
        ratio = (input_value - MMIN) / (MMAX - MMIN)

    ratio = max(0.0, min(1.0, ratio))
    target_brightness = int(SMIN + ratio * (SMAX - SMIN))
    target_brightness = max(0, min(100, target_brightness))

    sbc.set_brightness(target_brightness)
    return target_brightness

if __name__ == "__main__":
    multiprocessing.freeze_support()

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    ser = None
    AB_ON = True

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print("gram Assistant를 시작합니다.")
    print("버튼 A: Gemini 호출 / 버튼 B: TTS 재생 중지 / 버튼 A+B: 자동 밝기 토글 / 터미널 Ctrl+C: gram Assistant 종료")

    try:
        while True:
            if current_playback_process and not current_playback_process.is_alive():
                current_playback_process.join()
                if temp_mp3_filename_global and os.path.exists(temp_mp3_filename_global):
                    try:
                        os.remove(temp_mp3_filename_global)
                    except Exception as e:
                        print(f"TTS 완료 후 임시 파일 삭제 오류: {e}")
                current_playback_process = None
                temp_mp3_filename_global = None

            if ser and ser.in_waiting > 0:
                serial_input = ser.readline().decode('utf-8').rstrip()
                if not serial_input:
                    continue

                if serial_input == "A":
                    if current_playback_process and current_playback_process.is_alive():
                        print("TTS 재생 중단 (새 요청).")
                        current_playback_process.terminate()
                        current_playback_process.join(timeout=1)
                        if temp_mp3_filename_global and os.path.exists(temp_mp3_filename_global):
                            try: os.remove(temp_mp3_filename_global)
                            except Exception as e: print(f"기존 TTS 파일 삭제 오류: {e}")
                        current_playback_process = None
                        temp_mp3_filename_global = None

                    print("\n음성 인식 시작!")
                    recognized_text = Speech_Recognition(recognizer, microphone, ser)

                    if recognized_text:
                        print(f"\nGemini에게 프롬포트를 전달하고 있어요. (\"{recognized_text[:30]}...\")")
                        gemini_answer = Gemini(recognized_text, ser)
                        error_responses = ("Gemini 모델 오류", "입력된 텍스트가 없어요.", "Gemini 응답 형식 오류", "Gemini API 오류:")
                        if gemini_answer and not any(gemini_answer.startswith(err) for err in error_responses):
                            print(f"\nGemini: {gemini_answer}")
                            GTTS(gemini_answer, lang='ko', ser_conn=ser)
                        else:
                            error_msg = f"Gemini의 응답이 유효하지 않습니다: {gemini_answer if gemini_answer and len(gemini_answer) < 100 else '응답 내용이 너무 길거나 없습니다.'}"
                            print(error_msg)
                            GTTS(f"Gemini 응답에 문제가 있습니다. {gemini_answer if gemini_answer and len(gemini_answer) < 50 else ''}", ser_conn=ser)
                    else:
                        print("음성 인식에 실패했습니다. 다시 시도해보세요.")
                        GTTS("음성 인식에 실패했습니다. 다시 시도해보세요.", ser_conn=ser)

                elif serial_input == "B":
                    if current_playback_process and current_playback_process.is_alive():
                        print("TTS 재생을 중지할게요.")
                        current_playback_process.terminate()
                        current_playback_process.join(timeout=1)
                    else:
                        print("현재 재생 중인 TTS가 없습니다.")

                elif serial_input == "C":
                    AB_ON = not AB_ON
                    status_message = "자동 밝기 조절 기능이 " + ("활성화되었습니다." if AB_ON else "비활성화되었습니다.")
                    print(status_message)

                elif serial_input.isdigit():
                    if AB_ON:
                        print(f"Brightness Value: {serial_input}")
                        new_brightness = Adaptive_Brightness(serial_input)
                        if new_brightness is not None:
                            print(f"디스플레이 밝기가 조정되었어요. ({new_brightness}%)")
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\ngram Assistant를 종료합니다.")
    finally:
        if current_playback_process and current_playback_process.is_alive():
            print("종료 전 TTS 프로세스 정리...")
            current_playback_process.terminate()
            current_playback_process.join(timeout=2)
        if temp_mp3_filename_global and os.path.exists(temp_mp3_filename_global):
            try:
                os.remove(temp_mp3_filename_global)
            except Exception as e:
                print(f"종료 시 임시 파일 삭제 오류: {e}")
        if ser and ser.is_open:
            ser.close()
