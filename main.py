from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError

from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    StickerMessage,
    ImageMessage
)

import os
import psycopg2

app = Flask(__name__)

# 環境変数を取得
CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
MASTER_USER = os.environ["MASTER_USER"]
DATABASE_URL = os.environ["DATABASE_URL"]

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


@app.route("/callback", methods=['POST'])
def callback():
    # ヘッダのX-Line-Signatureを取得
    signature = request.headers['X-Line-Signature']

    # JSONを取得
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 取得した情報を扱う　もしデータが改竄されてたらエラーになる
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


def get_connection():
    return psycopg2.connect(DATABASE_URL)


# テキストメッセージが来たとき
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = str(event.source.user_id)
    text = str(event.message.text)
    messageId = int(event.message.id)

    if MASTER_USER != user_id:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('このアプリは開発中です')
        )

    else:
        result = None
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM Word WHERE word='%s';" % text)
                result = cur.fetchall()

        if result: # データベースに登録されている単語かどうか
            # データベースに登録されている単語ならここに入る
            db_msgid = result[0][1]
            line_bot_api.reply_message(
                event.reply_token, (
                    TextSendMessage('それは言いました'),
                    TextSendMessage('%d' % db_msgid)
                )
            )
        else:
            # データベースに登録されていない単語は登録する
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO Word VALUES ('%s','%d');" % (text, messageId))
            line_bot_api.reply_message(
                event.reply_token, (
                    TextSendMessage('◯'),
                    TextSendMessage('%d' % messageId)
                )
            )



# スタンプが来たとき
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    user_id = str(event.source.user_id)
    if MASTER_USER != user_id:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('このアプリは開発中です')
        )
    else:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM Word;")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage('リセットしました')
        )


# CREATE TABLE Word (word varchar(50),id bigint);


if __name__ == "__main__":
    # app.run()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
