from flask import Flask, request, jsonify
from flask_cors import CORS
from pytube import YouTube, Playlist
from io import BytesIO
import requests
import base64

app = Flask(__name__)
CORS(app)

@app.route("/")
def hello():
    return "Hello!"

# 判斷是否為 YouTube 影片或播放清單
@app.route('/api/url_type', methods=['POST'])
def check_url_type():
    url = request.json.get('url')
    try:
        video = YouTube(url)
        thumbnail_url = video.thumbnail_url.replace('hq720.jpg', 'maxresdefault.jpg')
        title = video.title
        author = video.author
        return jsonify({'urlType': 'video', 'thumbnailUrl': thumbnail_url, 'title': title, 'author': author})
    except:
        try:
            playlist = Playlist(url)
            list_length = len(playlist)
            if list_length > 0:
                # 取得播放清單的第一個影片縮圖作為預覽
                first_video = playlist.video_urls[0]
                first_video_obj = YouTube(first_video)
                thumbnail_url = first_video_obj.thumbnail_url.replace('hq720.jpg', 'maxresdefault.jpg')
                title = playlist.title
                author = playlist.owner
                return jsonify({'urlType': 'playlist', 'thumbnailUrl': thumbnail_url, 'title': title, 'listLength': list_length})
            else:
                return jsonify({'urlType': 'private', 'thumbnailUrl': None, 'title': None, 'listLength': 0})
        except:
            return jsonify({'urlType': 'unknown', 'thumbnailUrl': None, 'title': None, 'author': None})

# 獲取音訊相關資訊
@app.route('/api/get_audio_info', methods=['POST'])
def get_audio_info():
    # 從 POST 請求中取得影片 URL
    video_url = request.json['url']

    try:
        yt = YouTube(video_url)
        audio_info = {
            'author': yt.author,
            'duration': yt.length,
            'audioBase64': None,
            'thumbnailBase64': None,
        }

        # 取得音訊串流
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            # 將音訊串流轉換為位元組緩衝區
            audio_buffer = BytesIO()
            audio_stream.stream_to_buffer(audio_buffer)

            # 將音訊緩衝區進行 base64 編碼
            encoded_audio = base64.b64encode(audio_buffer.getvalue()).decode('utf-8')
            audio_info['audioBase64'] = encoded_audio

        # 下載並編碼縮圖
        thumbnail_url = yt.thumbnail_url.replace('hq720.jpg', 'maxresdefault.jpg')
        thumbnail_response = requests.get(thumbnail_url)
        thumbnail_data = thumbnail_response.content
        thumbnail_base64 = base64.b64encode(thumbnail_data).decode('utf-8')
        audio_info['thumbnailBase64'] = thumbnail_base64

        # 回傳音訊相關資訊及縮圖
        return jsonify({'audioInfo': audio_info})

    except Exception as e:
        return jsonify({'audioInfo': None})

# 設定路由
@app.route('/api/get_mp3', methods=['POST'])
def get_mp3():
    # 從 POST 請求中取得影片 URL
    video_url = request.json['url']

    try:
        yt = YouTube(video_url)
        audio_base64 = None

        # 取得音訊串流
        audio_stream = yt.streams.filter(only_audio=True).first()
        if audio_stream:
            # 將音訊串流轉換為位元組緩衝區
            audio_buffer = BytesIO()
            audio_stream.stream_to_buffer(audio_buffer)

            # 將音訊緩衝區進行 base64 編碼
            encoded_audio = base64.b64encode(audio_buffer.getvalue()).decode('utf-8')
            audio_base64 = encoded_audio
        
            # 回傳影片資訊及音頻 URL
            return jsonify({'audioBase64': audio_base64})
        else:
            return jsonify({'audioBase64': None})
    except Exception as e:
        return jsonify({'audioBase64': None})

@app.route('/api/get_mp4', methods=['POST'])
def get_mp4():
    # 從 POST 請求中取得影片 URL
    video_url = request.json['url']

    try:
        yt = YouTube(video_url)

        # 取得影片串流
        video_stream = yt.streams.get_highest_resolution()

        if video_stream:
            # 取得音訊串流
            audio_stream = yt.streams.get_audio_only()

            # 將影片串流轉換為位元組緩衝區
            video_buffer = BytesIO()
            video_stream.stream_to_buffer(video_buffer)

            # 如果有音訊串流，將音訊串流轉換為位元組緩衝區
            if audio_stream:
                audio_buffer = BytesIO()
                audio_stream.stream_to_buffer(audio_buffer)
            else:
                audio_buffer = None

            # 將影片和音訊緩衝區進行合併
            if audio_buffer:
                merged_buffer = merge_video_audio(video_buffer, audio_buffer)
            else:
                merged_buffer = video_buffer.getvalue()

            # 將合併後的緩衝區進行 base64 編碼
            encoded_video = base64.b64encode(merged_buffer).decode('utf-8')

            # 回傳編碼後的影片資料
            return jsonify({'videoBase64': encoded_video})
        else:
            return jsonify({'videoBase64': None})

    except Exception as e:
        print(e)
        return jsonify({'videoBase64': None})

# 合併影片和音訊緩衝區
def merge_video_audio(video_buffer, audio_buffer):
    video_buffer.seek(0)
    audio_buffer.seek(0)

    # 合併緩衝區
    merged_buffer = video_buffer.getvalue() + audio_buffer.getvalue()

    return merged_buffer

@app.route('/api/get_audio_list_info', methods=['POST'])
def get_audio_list_info():
    # 從 POST 請求中取得 YouTube 播放清單網址
    playlist_url = request.json['playlistUrl']
    audio_list = []

    try:
        # 從 YouTube 播放清單網址中取得播放清單物件
        playlist = Playlist(playlist_url)

        # 逐一處理播放清單中的影片
        for video in playlist.videos:
            try:
                audio_info = {
                    'title': video.title,
                    'author': video.author,
                    'duration': video.length,
                    'audioBase64': None,
                    'thumbnailBase64': None,
                }

                # 取得音訊串流
                audio_stream = video.streams.filter(only_audio=True).first()
                if audio_stream:
                    # 將音訊串流轉換為位元組緩衝區
                    audio_buffer = BytesIO()
                    audio_stream.stream_to_buffer(audio_buffer)

                    # 將音訊緩衝區進行 base64 編碼
                    encoded_audio = base64.b64encode(audio_buffer.getvalue()).decode('utf-8')
                    audio_info['audioBase64'] = encoded_audio

                # 下載並編碼縮圖
                thumbnail_url = video.thumbnail_url.replace('hq720.jpg', 'maxresdefault.jpg')
                thumbnail_response = requests.get(thumbnail_url)
                thumbnail_data = thumbnail_response.content
                thumbnail_base64 = base64.b64encode(thumbnail_data).decode('utf-8')
                audio_info['thumbnailBase64'] = thumbnail_base64

                audio_list.append(audio_info)
                print(f"Processed video: {video.title}")
            except Exception as e:
                print(f"Failed to process video: {video.title}. Error: {str(e)}")

        # 回傳音訊相關資訊列表
        return jsonify({'audioList': audio_list})

    except Exception as e:
        return jsonify({'audioList': []})


# 主程式
if __name__ == '__main__':
    app.run(debug=True)
