import gradio as gr
from modules.chat_engine import ChatEngine

def launch_ui(chat: ChatEngine):
    with gr.Blocks() as app:
        gr.Markdown("# 📚 ASO Team AI Chatbot")
        gr.Markdown("Ask questions about your loaded documents. Answers are grounded in your corpus and include sources.")

        chatbot = gr.Chatbot(label="Document Q&A", type="messages", height=500)
        msg = gr.Textbox(placeholder="Type your question and hit enter...")
        clear = gr.Button("Clear conversation")

        def on_submit(message, state):
            if not isinstance(state, list):
                state = []
            reply = chat.chat(message)
            state = state + [{"role":"user","content": message}, {"role":"assistant","content": reply}]
            return state, ""

        def on_clear():
            chat.history.clear()
            return []

        msg.submit(on_submit, [msg, chatbot], [chatbot, msg])
        clear.click(on_clear, None, chatbot)

    app.launch()
