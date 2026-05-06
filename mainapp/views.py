from django.shortcuts import render


def index(request):
    bot_username = 'STEOS'
    return render(request, 'mainapp/index.html', {
        'bot_username': bot_username,
        'bot_tg_link': f'https://t.me/{bot_username}',
        'bot_tg_scheme': f'tg://resolve?domain={bot_username}',
    })
