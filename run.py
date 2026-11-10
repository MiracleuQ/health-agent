"""统一运行入口：命令行 / FastAPI / Streamlit。"""
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：")
        print("  python run.py api       # 启动 FastAPI 后端")
        print("  python run.py web       # 启动 Streamlit 前端")
        print("  python run.py cli       # 启动命令行对话")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "api":
        os.system("uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    elif mode == "web":
        os.system("streamlit run frontend/streamlit_app.py")
    elif mode == "cli":
        from app.cli import main as cli_main
        cli_main()
    else:
        print(f"未知模式：{mode}")
        sys.exit(1)
