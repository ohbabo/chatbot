# apps/audio_utils.py

from transformers import pipeline
import torch, os
import logging, warnings




SUPERTONE_API_KEY = os.getenv('SUPERTONE_API_KEY')

warnings.filterwarnings("ignore", category=FutureWarning)

# Whisper 파이프라인 로드 (애플리케이션 시작 시 한 번만 로드)
try:
    whisper_pipeline = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-base",  # 원하는 Whisper 모델로 변경 가능
        device=0 if torch.cuda.is_available() else -1  # GPU 사용 가능 시 GPU 인덱스, 아니면 CPU
    )
    logging.info("Whisper pipeline loaded successfully.")
except Exception as e:
    logging.error(f"Failed to load Whisper pipeline: {e}")
    raise e


def transcribe_audio(audio_path):
    """
    주어진 오디오 파일을 Whisper 모델을 사용하여 텍스트로 변환합니다.

    Parameters:
        audio_path (str): 변환할 오디오 파일의 경로.

    Returns:
        str: 변환된 텍스트.
    """
    try:
        result = whisper_pipeline(audio_path)
        transcription = result['text']
        return transcription.lower()
    except Exception as e:
        logging.error(f"Audio transcription failed for {audio_path}: {e}")
        raise RuntimeError(f"Audio transcription failed: {e}")

