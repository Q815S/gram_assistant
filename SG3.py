import serial, time, os, uuid, multiprocessing, speech_recognition as sr, google.generativeai as genai, screen_brightness_control as sbc
from gtts import gTTS
from playsound import playsound
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
model = os.getenv('model')
system_instruction = os.getenv('system_instruction')

SERIAL_PORT = 'COM3'
BAUD_RATE = 115200

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(model, system_instruction = system_instruction)

MMIN = 0
MMAX = 1024
SMIN = 0
SMAX = 100

current_playback_process = None
temp_mp3_filename_global = None

def Speech_Recognition(recognizer, microphone, ser_conn=None):
    if not isinstance(recognizer, sr.Recognizer):
        raise TypeError("`recognizer` must be a `Recognizer` instance")
    if not isinstance(microphone, sr.Microphone):
        raise TypeError("`microphone` must be a `Microphone` instance")

    text = None
    with microphone as source:
        if ser_conn: ser_conn.write("LISTENING\n".encode('utf-8'))
        recognizer.adjust_for_ambient_noise(source, duration=0.5) 
        print("이제 말씀하세요!")
        try:
            audio = recognizer.listen(source, timeout=7, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            print("음성 입력 시간을 초과했어요.")
            if ser_conn: ser_conn.write("FAIL_STT_TIMEOUT\n".encode('utf-8'))
            return None

    if audio:
        print("음성을 분석하고 있어요.")
        if ser_conn: ser_conn.write("PROCESSING_STT\n".encode('utf-8')) 
        try: 
            text = recognizer.recognize_google(audio, language="ko-KR")
            print(f"인식된 텍스트: {text}")
        except sr.UnknownValueError or sr.UnknownValueError as e:
            print("음성을 인식할 수 없어요.")
    return text

def Gemini(prompt_text, ser_conn=None):
    if not prompt_text:
        return "입력된 텍스트가 없어요."

    try:
        response = model.generate_content(prompt_text)
        if hasattr(response, 'text') and response.text:
            return response.text
        elif response.parts and hasattr(response.parts[0], 'text'):
            return response.parts[0].text
        else:
            print("Gemini 응답에서 텍스트를 추출하는데 실패했어요.")
            return "Gemini 응답 형식 오류"
    except Exception as e:
        print(f"Gemini API 요청 중 오류 발생: {e}")
        return f"Gemini API 오류: {e}"

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
            try:
                os.remove(temp_mp3_filename_global)
            except Exception as e: 
                print(f"TTS 파일 삭제 중 오류가 발생했어요. {e}")
        current_playback_process = None
        temp_mp3_filename_global = None

    try:
        tts = gTTS(text=text_to_speak, lang=lang, slow=False)
        temp_mp3_filename_global = f"TTS_{uuid.uuid4()}.mp3"
        tts.save(temp_mp3_filename_global)
        current_playback_process = multiprocessing.Process(target=Audio, args=(temp_mp3_filename_global,))
        current_playback_process.start()
    except Exception as e:
        print(f"gTTS 또는 파일 저장 중 오류: {e}")
        if ser_conn: ser_conn.write("FAIL_TTS_GENERATION\n".encode('utf-8'))
        if temp_mp3_filename_global and os.path.exists(temp_mp3_filename_global):
            try:
                os.remove(temp_mp3_filename_global)
            except Exception as e_del:
                print(f"오류 발생 후 임시 파일 삭제 중 오류: {e_del}")
        temp_mp3_filename_global = None
        current_playback_process = None

def Display_Brightness(input_value_str, last_brightness):
    input_value = int(input_value_str)

    if MMAX == MMIN:
        ratio = 0.5
    else:
        ratio = (input_value - MMIN) / (MMAX - MMIN)
        
    ratio = max(0.0, min(1.0, ratio))
    target_brightness = int(SMIN + ratio * (SMAX - SMIN))
    target_brightness = max(0, min(100, target_brightness))

    if target_brightness != last_brightness:
        sbc.set_brightness(target_brightness)
        return target_brightness

if __name__ == "__main__":
    multiprocessing.freeze_support()

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    ser = None
    last_set_screen_brightness = -1
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    ser.write("READY\n".encode('utf-8'))
    print("gram Assistant를 시작합니다.")
    print("버튼 A: Gemini 호출 / 버튼 B: TTS 재생 중지 / 터미널 Ctrl+C: gram Assistant 종료")

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
                if ser: ser.write("DONE_PLAYING\n".encode('utf-8'))

            if ser and ser.in_waiting > 0:
                try:
                    serial_input = ser.readline().decode('utf-8').rstrip()
                    if not serial_input:
                        continue

                    if serial_input == "A":
                        if current_playback_process and current_playback_process.is_alive():
                            print("TTS 재생을 중지할게요.")
                            current_playback_process.terminate()
                            current_playback_process.join(timeout=1)
                            if temp_mp3_filename_global and os.path.exists(temp_mp3_filename_global):
                                try:
                                    os.remove(temp_mp3_filename_global)
                                except Exception as e:
                                    print(f"기존 TTS 파일 삭제 중 오류: {e}")
                            current_playback_process = None
                            temp_mp3_filename_global = None
                            if ser: ser.write("TTS_INTERRUPTED_NEW_REQUEST\n".encode('utf-8'))

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
                                print(f"Gemini의 응답이 유효하지 않습니다: {gemini_answer}")
                                GTTS(f"Gemini 응답에 문제가 있습니다. {gemini_answer if gemini_answer and len(gemini_answer) < 50 else ''}", ser_conn=ser)
                                if ser: ser.write("FAIL_GEMINI_RESPONSE\n".encode('utf-8'))
                        else:
                            print("음성 인식에 실패했습니다. 다시 시도해보세요.")
                            GTTS("음성 인식에 실패했습니다.", ser_conn=ser)

                    elif serial_input == "B":
                        if current_playback_process and current_playback_process.is_alive():
                            print("TTS 재생을 중지할게요.")
                            if ser: ser.write("TTS_STOPPING\n".encode('utf-8'))
                            current_playback_process.terminate()
                            if ser: ser.write("TTS_STOPPED\n".encode('utf-8'))
                        else:
                            if ser: ser.write("TTS_NOT_PLAYING\n".encode('utf-8'))
                    
                    elif serial_input.isdigit():
                        last_set_screen_brightness = Display_Brightness(serial_input, last_set_screen_brightness)

                except UnicodeDecodeError or ValueError as e:
                    print("문제가 발생했습니다. 잠시 후 다시 시도해보세요.")
                    print(f"오류 내용: {e}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\ngram Assistant를 종료합니다.")
    finally:
        if current_playback_process and current_playback_process.is_alive():
            print("종료 전 TTS 프로세스 정리...")
            current_playback_process.terminate()
            current_playback_process.join(timeout=1)
        if temp_mp3_filename_global and os.path.exists(temp_mp3_filename_global):
            try:
                os.remove(temp_mp3_filename_global)
            except Exception as e:
                print(f"종료 시 임시 파일 삭제 오류: {e}")
        if ser and ser.is_open:
            try:
                ser.write("EXITING\n".encode('utf-8'))
            except Exception as e:
                print(f"종료 메시지 전송 오류: {e}")
            finally:
                ser.close()