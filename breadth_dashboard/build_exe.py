"""
執行此腳本以自動打包為 exe：
    py build_exe.py
"""
import os
import sys
import shutil
import subprocess
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def find_package_path(pkg_name: str) -> str:
    spec = importlib.util.find_spec(pkg_name)
    if spec is None:
        raise RuntimeError(f"找不到套件：{pkg_name}")
    return os.path.dirname(spec.origin)


def main():
    # 先確認 pyinstaller 已安裝
    if importlib.util.find_spec("PyInstaller") is None:
        print("安裝 PyInstaller …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    streamlit_dir = find_package_path("streamlit")
    altair_dir    = find_package_path("altair")

    datas = [
        (streamlit_dir, "streamlit"),
        (altair_dir,    "altair"),
    ]

    hidden_imports = [
        "streamlit", "streamlit.web.cli", "streamlit.runtime",
        "streamlit.components.v1",
        "plotly", "plotly.graph_objects", "plotly.express",
        "pandas", "numpy", "yfinance", "requests",
        "diskcache", "lxml", "lxml.etree",
        "sklearn", "scipy",
        "altair", "pydeck",
        "PIL", "PIL.Image",
        "bs4", "html5lib",
        "pyarrow", "pyarrow.vendored.version",
        "tzdata",
    ]

    datas_args  = []
    for src, dst in datas:
        datas_args += ["--add-data", f"{src}{os.pathsep}{dst}"]

    hidden_args = []
    for hi in hidden_imports:
        hidden_args += ["--hidden-import", hi]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", "SP500_Breadth",
        "--icon", "NONE",
        *datas_args,
        *hidden_args,
        "--collect-all", "streamlit",
        "--collect-all", "altair",
        "--collect-all", "plotly",
        "launcher.py",
    ]

    print("開始打包（可能需要 3–10 分鐘）…\n")
    subprocess.check_call(cmd, cwd=HERE)

    # 把 app.py / config.py / modules/ 複製到 exe 旁邊
    # Streamlit 需要讀取實際的 .py 原始碼，無法從 PyInstaller 暫存目錄執行
    dist_dir = os.path.join(HERE, "dist", "SP500_Breadth")
    print("複製應用程式檔案…")
    for fname in ("app.py", "config.py"):
        shutil.copy2(os.path.join(HERE, fname), dist_dir)
    modules_dst = os.path.join(dist_dir, "modules")
    if os.path.exists(modules_dst):
        shutil.rmtree(modules_dst)
    shutil.copytree(os.path.join(HERE, "modules"), modules_dst)

    print("\n完成！執行檔位於：dist/SP500_Breadth/SP500_Breadth.exe")


if __name__ == "__main__":
    main()
