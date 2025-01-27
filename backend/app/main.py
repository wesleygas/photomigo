from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.routes import router
from app.config import settings



app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # Some possible debuggin tools
# from starlette.concurrency import iterate_in_threadpool
# from fastapi import Request
# import time
# @app.middleware("http")
# async def middleware(request: Request, call_next):
#     # try:
#     #     req_body = await request.json()
#     # except Exception:
#     #     req_body = None

#     print(request.headers)
#     # start_time = time.perf_counter()
#     response = await call_next(request)
#     # process_time = time.perf_counter() - start_time

#     # res_body = [section async for section in response.body_iterator]
#     # response.body_iterator = iterate_in_threadpool(iter(res_body))

#     # Stringified response body object
#     # res_body = res_body[0].decode()
#     return response


# import logging
# logging.basicConfig()
# logger = logging.getLogger('sqlalchemy.engine')
# logger.setLevel(logging.DEBUG)

app.include_router(router, prefix=settings.API_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)