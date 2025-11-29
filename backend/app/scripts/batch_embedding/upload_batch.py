# upload_batch.py (修复版)

import os, sys
from dotenv import load_dotenv
from openai import OpenAI

CURRENT = os.path.abspath(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT, "../../../.."))
sys.path.append(BACKEND_DIR)

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def upload():
    input_file = "programs_batch_input.jsonl"
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"❌ 找不到文件: {input_file}，请先运行 prepare_input.py")
    
    print(">> Uploading batch file...")

    # 1. 上传文件
    try:
        with open(input_file, "rb") as f:
            upload = client.files.create(
                file=f,
                purpose="batch"
            )
        print("✔ Uploaded file ID:", upload.id)
    except Exception as e:
        print(f"❌ 上传文件失败: {e}")
        return

    # 2. 创建 batch
    try:
        batch = client.batches.create(
            input_file_id=upload.id,
            endpoint="/v1/embeddings",
            completion_window="24h"
        )
        
        print("✔ Batch created!")
        print("Batch ID:", batch.id)
        print("Status:", batch.status)
        
        # 保存 batch_id 供后续使用
        with open("last_batch_id.txt", "w") as f:
            f.write(batch.id)
        print("✔ Batch ID saved to last_batch_id.txt")
        
    except Exception as e:
        print(f"❌ 创建 batch 失败: {e}")
        return


if __name__ == "__main__":
    upload()