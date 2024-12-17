
# ZiBot AIChat
# 作者：ZiChen  时间：20241217

import re
import json
import websocket
import requests
from urllib.parse import quote
import array as arr

print("System: 欢迎使用ZiBot，服务正在启动中！")

# 基础服务参数
ws_url = "ws://172.18.0.4:11000" # WebSocket服务器的URL
http_url = "http://172.18.0.4:22000" # Http API服务器的URL
ai_url = "https://spark-api-open.xf-yun.com/v1/chat/completions"    # 大数据模型接口地址（这里使用的为讯飞星火）

# 大模型调用相关参数
model = "Lite"  # 指定请求的模型
APIPassword = "xxxxxxxxxx"   # APIPassword
training_msg = "回复的内容应当在50字以内，精简回答。问题内容：" # 调教文案(会添加在消息之前提供给机器人)


# 定义WebSocket回调类
class MyWebSocket:

    def on_open(self, ws):
        print("\nSystem: 连接已打开")

    def on_message(self, ws, message):
        #print("BOT：收到消息")
        print("\nSystem: 收到消息:", message)
        core(message)  # 调用核心函数处理消息

    def on_error(self, ws, error):
        print("\nSystem: 发生错误:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print("\nSystem: 连接已关闭")


# 主程序(WS进程)
def main():

    global ws_url

    # 创建WebSocket应用
    ws_app = websocket.WebSocketApp(
        ws_url,
        on_open=MyWebSocket().on_open,
        on_message=MyWebSocket().on_message,
        on_error=MyWebSocket().on_error,
        on_close=MyWebSocket().on_close
    )

    # 启动WebSocket客户端
    ws_app.run_forever()


# 核心调度程序
def core(data):

    global http_url

    # 解析接收到的消息
    message_type , user_id , raw_message = read_json(data)

    # 如果必须的信息都存在
    if message_type and user_id and raw_message:

        # 调用大模型进行回复
        ai_msg = chat_api(raw_message)

        # 如果成功获取相应
        if ai_msg:

            # 对返回的消息进行 URL 编码
            sent_msg = quote(ai_msg)

            # 如果消息来源是私聊
            if message_type == "private":
                # 发送消息
                response = requests.get( f'{http_url}/send_private_msg?user_id={user_id}&message={sent_msg}')
                print("BOT: 消息已发送:", response.text)
                return()

            # 如果消息来源是群聊
            if message_type == "group":
                # 发送消息
                response = requests.get( f'{http_url}/send_group_msg?group_id={user_id}&message={sent_msg}')
                print("BOT: 消息已发送:", response.text)
                return()

            print("BOT: 未知的消息来源")
            return()

        else:

            print("BOT: 大模型调用失败")
            return()

    else:

        #print("BOT: 消息解析失败")
        return()



# JSON解析器
def read_json(json_txt):
    try:
        # 解析 JSON 数据
        json_data = json.loads(json_txt)

        # 判断消息类型，如果是 lifecycle 或 meta_event 类型则跳过
        if json_data.get("post_type") == "meta_event":
            print("BOT: 收到生命周期事件 忽略处理")
            return None, None, None

        # 如果为私聊消息
        if json_data.get('message_type') == "private":

            print("BOT: 收到好友信息 正在处理")
            # 提取 bot_id user_id raw_message
            bot_id = str(json_data['self_id'])
            user_id = json_data['user_id']
            raw_message = json_data['raw_message']

            #清理CQ码
            raw_message = cq_clean(raw_message)
            if raw_message == "":
                print("BOT: 非文本消息 忽略处理")
                return None, None, None

            # 返回相关参数
            return "private" , user_id, raw_message

        # 如果为群聊消息
        if json_data.get('message_type') == "group":

            print("BOT: 收到群聊信息 正在处理")
            # 提取 bot_id group_id raw_message
            bot_id = str(json_data['self_id'])
            user_id = json_data['group_id']
            raw_message = json_data['raw_message']

            # 如果机器人被@
            if ("[CQ:at,qq=" + bot_id + "]") in raw_message:
                # 对文本进行处理
                raw_message = raw_message.replace("[CQ:at,qq=" + bot_id + "]", "")
                raw_message = raw_message.replace(" ", "")

                #清理CQ码
                raw_message = cq_clean(raw_message)
                if raw_message == "":
                    print("非文本消息，忽略处理")
                    return None, None, None

                # 返回相关参数
                return "group" , user_id, raw_message

            else:

                print("BOT: 没有@机器人，忽略处理")
                return None, None, None

        # 默认情况，直接返回空
        return None, None, None


    except json.JSONDecodeError:

        print("BOT: 解析消息失败 JSON 格式错误")
        return None, None, None


# cq码清理工具
def cq_clean(text):

    while True:
        # 查找 [CQ 的起始位置
        start_index = text.find("[CQ:")

        # 如果没有找到 [CQ，退出循环
        if start_index == -1:
            break

        # 查找第一个 ] 的位置
        end_index = text.find("]", start_index)

        # 如果没有找到 ]，退出循环
        if end_index == -1:
            break

        # 删除从 [CQ 开始到第一个 ] 的部分
        text = text[:start_index] + text[end_index + 1:]

    return text

# 调用大模型API
def chat_api(msg_txt):

    global ai_url
    global training_msg
    global APIPassword
    global model

    data = {
            "model": model ,
            "messages": [
                {
                    "role": "user",
                    "content": training_msg + msg_txt
                }
            ],
            "stream": True
        }

    header = {
        # 自定义了UserAgent，可自行修改
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Authorization": "Bearer " + APIPassword
    }

    # 发送POST请求
    response = requests.post(ai_url, headers=header, json=data)

    # 设置接口使用的编码
    response.encoding = "utf-8"

    # 将每一Token返回的Json进行整理
    response_data = response.text

    # 处理烂摊子()
    response_data = response_data.replace("\n\n", "\n")
    response_data = response_data.replace("data: ", "")
    response_data = response_data.replace("[DONE]", "")
    response_data = response_data.replace(" ", "")
    response_data = response_data.replace("\n\n", "")

    # 按行分割
    response_arr = response_data.split("\n")

    # 提取所有content并合并
    content_list = []

    for response_item in response_arr:
        try:
            # 将每行文本转换为JSON对象
            parsed_item = json.loads(response_item)

            # 提取choices中的content字段
            for choice in parsed_item['choices']:
                content_list.append(choice['delta']['content'])

        except json.JSONDecodeError:
            print(f"无法解析的JSON行: {response_item}")
            return("error")

        except KeyError as e:
            print(f"缺少预期的字段: {e}")
            return("error")


    # 合并成一句话
    merged_content = ''.join(content_list)

    # 文本优化，去除加粗标号
    merged_content = merged_content.replace("**", "")

    # 返回结果
    return(merged_content)


if __name__ == "__main__":
    main()

