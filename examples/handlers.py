from aioweb.async_web import get


@get('/')
async def index():
    return {
        '__template__': 'index.html'
    }
