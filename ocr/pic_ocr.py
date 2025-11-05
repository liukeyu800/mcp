#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量抽取“不可直接读取/无文本层”的 PDF 内容（使用 PaddleOCR PPStructureV3）。
默认从 unreadable_pdfs.txt 读取 PDF 绝对路径清单；
输出到指定目录下，按原目录结构组织，每个 PDF 一个子目录，包含：
- 聚合后的 Markdown 文件（文件名为 <原PDF名>.md）
- 该 Markdown 引用的图片资源（按结构化结果中的相对路径保存）

用法：
  python3 pdf_extractor.py \
    --list-file /home/xxx/liukeyu/guangke/unreadable_pdfs.txt \
    --output-dir /home/xxx/liukeyu/guangke/output_ocr \
    --root-base /home/xxx/liukeyu/guangke/广科院资料

以上参数均有默认值，可直接运行：
  python3 /home/xxx/liukeyu/guangke/pdf_extractor.py
"""

from __future__ import annotations
from pathlib import Path
import argparse
from typing import List

from paddleocr import PPStructureV3
import paddle
import gc
# 新增：服务相关依赖
from typing import Optional, Dict, Any
import threading

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn
    _FASTAPI_AVAILABLE = True
except Exception:
    _FASTAPI_AVAILABLE = False


def build_out_dir(pdf_path: Path, output_base: Path, root_base: Path) -> Path:
    try:
        rel = pdf_path.resolve().relative_to(root_base.resolve())
        out_dir = output_base / rel.parent / pdf_path.stem
    except Exception:
        # 不在 root_base 下，退化为安全折叠绝对路径
        safe = pdf_path.resolve().as_posix().lstrip("/").replace("/", "__")
        out_dir = output_base / safe
    return out_dir


def process_pdf(pipeline: PPStructureV3, input_file: Path, output_base: Path, root_base: Path) -> Path:
    output = pipeline.predict(input=str(input_file))

    markdown_list = []
    markdown_images = []

    for res in output:
        md_info = res.markdown
        markdown_list.append(md_info)
        markdown_images.append(md_info.get("markdown_images", {}))

    markdown_texts = pipeline.concatenate_markdown_pages(markdown_list)

    out_dir = build_out_dir(input_file, output_base, root_base)
    out_dir.mkdir(parents=True, exist_ok=True)

    mkd_file_path = out_dir / f"{input_file.stem}.md"
    with open(mkd_file_path, "w", encoding="utf-8") as f:
        f.write(markdown_texts)

    for item in markdown_images:
        if item:
            for path, image in item.items():
                file_path = out_dir / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(file_path)

    return out_dir


def main():
    parser = argparse.ArgumentParser(description="Batch extract PDFs with PaddleOCR PPStructureV3")
    parser.add_argument("--list-file", default="/home/xxx/liukeyu/guangke/unreadable_pdfs.txt", help="包含待抽取 PDF 绝对路径的 txt 文件，一行一个路径")
    parser.add_argument("--output-dir", default="/home/xxx/liukeyu/guangke/output_ocr", help="输出目录")
    parser.add_argument("--root-base", default="/home/xxx/liukeyu/guangke/广科院资料", help="用于保持原有目录结构的根目录")
    parser.add_argument("--device", default="auto", choices=["auto", "gpu", "cpu"], help="选择设备：gpu/cpu/auto（默认auto，优先gpu可用则用gpu）")
    parser.add_argument("--gc-after-pdf", action="store_true", help="每个PDF完成后触发一次垃圾回收以降低内存峰值")
    # 新增：服务模式
    parser.add_argument("--serve", action="store_true", help="以HTTP接口模式启动服务，提供单文件抽取接口")
    parser.add_argument("--host", default="127.0.0.1", help="服务绑定地址（默认127.0.0.1）")
    parser.add_argument("--port", type=int, default=8000, help="服务端口（默认8000）")
    args = parser.parse_args()

    list_file = Path(args.list_file)
    output_dir = Path(args.output_dir)
    root_base = Path(args.root_base)

    if not list_file.exists():
        raise SystemExit(f"找不到列表文件: {list_file}")

    with open(list_file, "r", encoding="utf-8") as f:
        pdf_paths: List[Path] = [Path(line.strip()) for line in f if line.strip()]

    pdf_paths = [p for p in pdf_paths if p.exists() and p.is_file() and p.suffix.lower() == ".pdf"]

    if not pdf_paths:
        raise SystemExit("列表中没有有效的 PDF 路径")

    # 设备选择：优先使用GPU（如可用）
    chosen = "cpu"
    if args.device in ("auto", "gpu"):
        try:
            if hasattr(paddle, "is_compiled_with_cuda") and paddle.is_compiled_with_cuda():
                paddle.set_device("gpu")
                chosen = "gpu"
            else:
                if args.device == "gpu":
                    print("警告：指定了 --device gpu，但当前Paddle未启用CUDA或不可用，回退到CPU。")
                paddle.set_device("cpu")
        except Exception as e:
            print(f"警告：尝试设置GPU失败，回退到CPU：{e}")
            paddle.set_device("cpu")
    else:
        paddle.set_device("cpu")

    try:
        cur_dev = paddle.get_device()
    except Exception:
        cur_dev = chosen
    print(f"使用设备: {cur_dev}")

    # 服务模式：启动FastAPI，仅处理单文件抽取
    if args.serve:
        if not _FASTAPI_AVAILABLE:
            raise SystemExit("当前环境未安装 fastapi/uvicorn，请先安装后再使用 --serve 模式：pip install fastapi uvicorn")

        app = FastAPI(title="PDF Extractor API", version="1.0.0")
        state: Dict[str, Any] = {
            "pipeline": PPStructureV3(),
            "lock": threading.Lock(),
            "output_dir": output_dir,
            "root_base": root_base,
            "gc_after_pdf": args.gc_after_pdf,
        }

        class ExtractRequest(BaseModel):
            pdf_path: str
            output_dir: Optional[str] = None
            root_base: Optional[str] = None

        @app.post("/extract")
        def extract(req: ExtractRequest):
            pdf_path = Path(req.pdf_path)
            if not pdf_path.exists() or not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
                raise HTTPException(status_code=400, detail="无效的PDF路径")

            out_base = Path(req.output_dir) if req.output_dir else state["output_dir"]
            root_base_local = Path(req.root_base) if req.root_base else state["root_base"]

            with state["lock"]:
                try:
                    out_dir_path = process_pdf(state["pipeline"], pdf_path, out_base, root_base_local)
                    if state["gc_after_pdf"]:
                        gc.collect()
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"处理失败: {e}")

            md_file = out_dir_path / f"{pdf_path.stem}.md"
            return {
                "ok": True,
                "device": cur_dev,
                "pdf": str(pdf_path),
                "output_dir": str(out_dir_path),
                "markdown_file": str(md_file if md_file.exists() else ""),
            }

        uvicorn.run(app, host=args.host, port=args.port)
        return

    pipeline = PPStructureV3()

    failures: List[str] = []
    print(f"开始抽取，共 {len(pdf_paths)} 个 PDF，输出目录：{output_dir}")
    for idx, p in enumerate(pdf_paths, 1):
        try:
            print(f"[{idx}/{len(pdf_paths)}] 处理：{p}")
            out_dir_path = process_pdf(pipeline, p, output_dir, root_base)
            if args.gc_after_pdf:
                gc.collect()
        except Exception as e:
            print(f"  -> 失败：{p} | {e}")
            failures.append(str(p))

    if failures:
        fail_file = output_dir / "failed_pdfs.txt"
        fail_file.parent.mkdir(parents=True, exist_ok=True)
        with open(fail_file, "w", encoding="utf-8") as f:
            f.write("\n".join(failures))
        print(f"完成，但有 {len(failures)} 个失败，列表见：{fail_file}")
    else:
        print("全部完成，未发现失败。")


if __name__ == "__main__":
    main()