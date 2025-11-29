# check_batch.py

import os, sys, time
from dotenv import load_dotenv
from openai import OpenAI

CURRENT = os.path.abspath(__file__)
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT, "../../../.."))
sys.path.append(BACKEND_DIR)

load_dotenv(os.path.join(BACKEND_DIR, ".env"))
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def main():
    # 尝试从文件读取，否则手动输入
    if os.path.exists("last_batch_id.txt"):
        BATCH_ID = open("last_batch_id.txt").read().strip()
        print(f">> 使用保存的 Batch ID: {BATCH_ID}")
        print(">> (如需使用其他 ID，请修改 last_batch_id.txt)\n")
    else:
        BATCH_ID = input("请输入批处理 Batch ID: ").strip()
    
    print(">> 开始监控 (每 10 秒刷新一次)...\n")
    
    while True:
        try:
            batch = client.batches.retrieve(batch_id=BATCH_ID)
            
            print("\n" + "="*50)
            print("Batch ID:", BATCH_ID)
            print("Status:", batch.status)
            print("Created at:", batch.created_at)
            print("Request counts:")
            print(f"  - Total: {batch.request_counts.total}")
            print(f"  - Completed: {batch.request_counts.completed}")
            print(f"  - Failed: {batch.request_counts.failed}")
            
            if batch.output_file_id:
                print(f"✔ Output file: {batch.output_file_id}")
            if batch.error_file_id:
                print(f"⚠️  Error file: {batch.error_file_id}")
            
            print("="*50)
            
            if batch.status in ["completed", "failed", "expired", "cancelled"]:
                print(f"\n✅ Batch 已结束，状态: {batch.status}")
                if batch.status == "completed":
                    print(">> 可以运行 download_output.py 下载结果")
                break
            
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n\n>> 监控已停止")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            break


if __name__ == "__main__":
    main()