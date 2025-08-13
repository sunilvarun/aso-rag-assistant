import argparse
import logging
import yaml
from modules.indexer import IndexBuilder
from modules.retriever import Retriever
from modules.chat_engine import ChatEngine
from ui.gradio_app import launch_ui

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="Rebuild the FAISS index from scratch")
    args = parser.parse_args()

    cfg = load_config()

    logging.basicConfig(
        level=getattr(logging, cfg.get("logging", {}).get("level", "INFO")),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    log = logging.getLogger("main")

    # 1) (Re)build or load index
    indexer = IndexBuilder(cfg)
    if args.reindex:
        log.info("Forcing re-index ...")
        indexer.build_index(force_rebuild=True)
    else:
        indexer.build_index(force_rebuild=False)

    # 2) Create retriever + chat engine
    retriever = Retriever(cfg, indexer.db)
    chat = ChatEngine(cfg, retriever)

    # 3) Launch UI
    launch_ui(chat)

if __name__ == "__main__":
    main()
