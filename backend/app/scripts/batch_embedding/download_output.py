# download_output.py

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# ================================================
# 路径设置
# ================================================
CURRENT_FILE = os.path.abspath(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_FILE, "../../../.."))
APP_DIR = os.path.join(BACKEND_DIR, "app")

sys.path.append(BACKEND_DIR)
sys.path.append(APP_DIR)

ENV_PATH = os.path.join(BACKEND_DIR, ".env")
load_dotenv(ENV_PATH)

from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def main():
    if not os.path.exists("last_batch_id.txt"):
        raise FileNotFoundError("❌ 没找到 last_batch_id.txt，请先运行 upload_batch.py")

    batch_id = open("last_batch_id.txt").read().strip()
    
    print(f">> 获取 Batch 信息: {batch_id}")
    batch = client.batches.retrieve(batch_id)
    
    print(f">> Status: {batch.status}")
    
    if batch.status != "completed":
        print(f"⚠️  Batch 状态不是 completed，当前是: {batch.status}")
        print(">> 请等待 batch 完成后再运行此脚本")
        return

    if not batch.output_file_id:
        raise RuntimeError("❌ 该 Batch 当前没有 output_file_id，可能未完成")

    print(">> Downloading output file:", batch.output_file_id)

    result = client.files.content(batch.output_file_id)

    # 保存为本地 JSONL 文件
    output_path = "batch_output.jsonl"
    with open(output_path, "wb") as f:
        f.write(result.read())

    # 统计行数
    line_count = sum(1 for _ in open(output_path, 'r', encoding='utf-8'))
    
    print(f"🎉 Output saved → {output_path}")
    print(f"   共 {line_count} 行结果")
    
    # 如果有错误文件，也下载
    if batch.error_file_id:
        print(f"\n⚠️  检测到错误文件: {batch.error_file_id}")
        error_result = client.files.content(batch.error_file_id)
        error_path = "batch_errors.jsonl"
        with open(error_path, "wb") as f:
            f.write(error_result.read())
        error_count = sum(1 for _ in open(error_path, 'r', encoding='utf-8'))
        print(f"   错误文件已保存 → {error_path} ({error_count} 条错误)")


if __name__ == "__main__":
    main()