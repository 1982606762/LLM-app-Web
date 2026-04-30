from django.urls import path

from .views import chat_stream_view, chat_view


urlpatterns = [
    path("chat/", chat_view, name="chat"),
    path("chat/stream/", chat_stream_view, name="chat-stream"),
]
