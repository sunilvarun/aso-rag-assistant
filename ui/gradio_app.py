import gradio as gr
from modules.chat_engine import ChatEngine
from modules.indexer import IndexBuilder

def launch_ui(chat: ChatEngine):
    with gr.Blocks() as app:
        gr.Markdown("# 📚 ASO Team AI Chatbot")
        gr.Markdown("Ask questions about your loaded documents. Answers are grounded in your corpus and include sources.")

        chatbot = gr.Chatbot(label="Document Q&A", type="messages", height=500)
        msg = gr.Textbox(placeholder="Type your question and hit enter...")

        with gr.Row():
            clear = gr.Button("Clear conversation")
            reindex = gr.Button("Re-index documents")

        status = gr.Markdown("")

        def on_submit(message, state):
            if not isinstance(state, list):
                state = []
            reply = chat.chat(message)
            state = state + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply}
            ]
            return state, ""

        def on_clear():
            chat.history.clear()
            return []

        def on_reindex():
            # show progress message first
            yield None, "", "⏳ Rebuilding index…"
            ib = IndexBuilder(chat.cfg)
            ib.build_index(force_rebuild=True)
            # swap the retriever db to the fresh one
            chat.retriever.db = ib.db
            yield None, "", "✅ Index rebuilt."

        msg.submit(on_submit, [msg, chatbot], [chatbot, msg])
        clear.click(on_clear, None, chatbot)
        reindex.click(on_reindex, None, [chatbot, msg, status], show_progress=True)

    app.launch()
